import logging
from pathlib import Path

import yaml

from config.settings import settings
from observatory.collectors.base import BaseCollector
from observatory.storage.models import CollectedItem

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("config/sources/obsidian_folders.yaml")
MAX_NOTE_CHARS = 8000


def _load_folders_config() -> list[dict]:
    """Read selected folders from the yaml config; [] if missing/disabled."""
    try:
        data = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return []
    if not data.get("enabled", True):
        return []
    return data.get("folders", []) or []


def list_vault_folders(vault_path: Path | str | None = None, max_depth: int = 3) -> list[str]:
    """Return relative folder paths under the vault (dirs only, depth-limited),
    skipping hidden/.obsidian dirs. Used by the visual folder picker."""
    root = Path(vault_path) if vault_path else Path(settings.obsidian_vault_path)
    if not root.is_dir():
        return []
    out: list[str] = []
    for d in sorted(root.rglob("*")):
        if not d.is_dir():
            continue
        rel = d.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if len(rel.parts) > max_depth:
            continue
        out.append(rel.as_posix())
    return out


def save_folders_config(folders: list[str]) -> None:
    """Persist the selected folder paths to the yaml config (recursive=True)."""
    data = {
        "enabled": True,
        "folders": [{"path": p, "recursive": True} for p in folders],
    }
    DEFAULT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CONFIG.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _parse_note(text: str, stem: str) -> tuple[str, str]:
    """Return (title, body). Title from YAML frontmatter `title:` if present,
    else the filename stem. Body excludes the frontmatter block."""
    title = stem
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            front = text[3:end]
            body = text[end + 4 :].lstrip("\n")
            for line in front.splitlines():
                if line.strip().lower().startswith("title:"):
                    val = line.split(":", 1)[1].strip().strip("'\"")
                    if val:
                        title = val
                    break
    return title, body


class ObsidianNotesCollector(BaseCollector):
    """Reads markdown notes from selected vault folders as `article` items so the
    article pipeline (Tess/Carla/Edu) can draft posts about the user's notes."""

    name = "obsidian"
    source_type = "markdown"

    def __init__(self, vault_path: Path | str | None = None, folders: list[dict] | None = None):
        self.vault_path = Path(vault_path) if vault_path else Path(settings.obsidian_vault_path)
        self.folders = folders if folders is not None else _load_folders_config()

    async def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        for entry in self.folders:
            rel = entry.get("path", "")
            recursive = entry.get("recursive", True)
            folder = self.vault_path / rel
            if not folder.is_dir():
                logger.warning("Obsidian folder not found: %s", folder)
                continue
            md_files = folder.rglob("*.md") if recursive else folder.glob("*.md")
            for f in sorted(md_files):
                try:
                    text = f.read_text(encoding="utf-8")[:MAX_NOTE_CHARS]
                except Exception as exc:
                    logger.warning("Could not read %s: %s", f, exc)
                    continue
                title, body = _parse_note(text, f.stem)
                if not body.strip():
                    continue
                relpath = f.relative_to(self.vault_path).as_posix()
                items.append(
                    CollectedItem(
                        url=f"obsidian://{relpath}",
                        title=title,
                        source=rel or "obsidian",
                        source_type=self.source_type,
                        raw_text=body,
                        kind="article",
                        source_group="pedagogy_notes",
                    )
                )
        logger.info("ObsidianNotesCollector collected %d notes", len(items))
        return items
