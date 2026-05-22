"""Obsidian vault writer for AI-article drafts.

One markdown per language stream under ``{vault}/Inbox/{lang}/``. The user
reviews these as two separate inboxes and approves via Telegram (Phase 5).
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from config.settings import settings

if TYPE_CHECKING:
    from observatory.intelligence.ai_evaluator import AIEvaluationResult
    from observatory.storage.models import CollectedItem

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, max_len: int = 60) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:max_len] or "untitled"


def _frontmatter_value(v):
    if isinstance(v, list):
        return "[" + ", ".join(f"\"{x}\"" for x in v) + "]"
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f"\"{str(v).replace(chr(34), chr(39))}\""


def _render_markdown(item: "CollectedItem", evaluation: "AIEvaluationResult", lang: str) -> str:
    angles_for_lang = [
        a for a in evaluation.post_angles
        if isinstance(a, dict) and lang in str(a.get("for", ""))
    ] or evaluation.post_angles

    frontmatter = {
        "source": item.source,
        "url": item.url,
        "kind": item.kind,
        "source_group": item.source_group,
        "lang": lang,
        "teacher_relevance": evaluation.teacher_relevance,
        "audience_fit": evaluation.audience_fit,
        "topic_tags": evaluation.topic_tags,
        "suggested_platforms": evaluation.suggested_platforms,
        "course_tie_in": evaluation.course_tie_in,
        "created": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "status": "draft",
    }

    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {_frontmatter_value(v)}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {item.title}")
    lines.append("")
    if evaluation.one_line_hook:
        lines.append(f"> {evaluation.one_line_hook}")
        lines.append("")
    lines.append("## Summary")
    lines.append(evaluation.summary or "_(no summary)_")
    lines.append("")
    lines.append("## Post angles")
    if angles_for_lang:
        for a in angles_for_lang:
            angle = a.get("angle", "") if isinstance(a, dict) else str(a)
            for_tag = a.get("for", "") if isinstance(a, dict) else ""
            tag_suffix = f"  _( {for_tag} )_" if for_tag else ""
            lines.append(f"- {angle}{tag_suffix}")
    else:
        lines.append("_(none returned by evaluator)_")
    lines.append("")
    if evaluation.course_tie_in:
        lines.append("## Course tie-in")
        lines.append(evaluation.course_tie_in)
        lines.append("")
    lines.append("## Source")
    lines.append(f"[{item.source}]({item.url})")
    lines.append("")
    return "\n".join(lines)


async def write_article_drafts(item: "CollectedItem", evaluation: "AIEvaluationResult") -> list[Path]:
    """Write one draft per language in evaluation.lang_targets. Returns the
    list of paths actually written (may be empty if no langs targeted or vault
    unreachable)."""
    if not evaluation.lang_targets:
        return []

    vault_root = Path(settings.obsidian_vault_path)
    written: list[Path] = []
    date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
    slug = _slugify(item.title)

    for lang in evaluation.lang_targets:
        if lang not in settings.ai_supported_langs:
            continue
        inbox = vault_root / "Inbox" / lang
        try:
            inbox.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Vault inbox not writable at {inbox}: {e}")
            continue

        path = inbox / f"{date_prefix}-{slug}.md"
        body = _render_markdown(item, evaluation, lang)
        try:
            path.write_text(body, encoding="utf-8")
            written.append(path)
            logger.info(f"Wrote vault draft: {path}")
        except OSError as e:
            logger.error(f"Failed to write vault draft {path}: {e}")

    return written
