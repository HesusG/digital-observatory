"""Persona file loader.

Persona files are markdown with YAML frontmatter:

    ---
    name: Tess
    role: Trend Spotter
    emoji: 🔭
    brain: ollama:gemma3:e4b
    vibe: Rigorous and skeptical.
    ---

    # Tess

    ## Identity
    ...

The loader returns a Persona with the frontmatter parsed and the body kept
verbatim so it can be injected into LLM prompts.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Persona:
    name: str
    role: str
    body: str
    emoji: Optional[str] = None
    brain: Optional[str] = None
    vibe: Optional[str] = None
    schedule: Optional[str] = None
    tools: Optional[list[str]] = None


def load_persona(path: Path) -> Persona:
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"persona file missing frontmatter: {path}")

    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"persona file frontmatter not terminated: {path}")

    frontmatter_raw = text[4:end]
    body = text[end + len("\n---\n"):].lstrip("\n")
    fm = yaml.safe_load(frontmatter_raw) or {}

    return Persona(
        name=str(fm.get("name", "")),
        role=str(fm.get("role", "")),
        body=body,
        emoji=fm.get("emoji"),
        brain=fm.get("brain"),
        vibe=fm.get("vibe"),
        schedule=fm.get("schedule"),
        tools=fm.get("tools"),
    )
