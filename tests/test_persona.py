from pathlib import Path

import pytest

from observatory.agents.persona import Persona, load_persona


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_load_persona_parses_frontmatter(tmp_path):
    persona_file = tmp_path / "tess.md"
    persona_file.write_text(
        "---\n"
        "name: Tess\n"
        "role: Trend Spotter\n"
        "emoji: 🔭\n"
        "brain: ollama:gemma3:e4b\n"
        "vibe: Rigorous and skeptical.\n"
        "---\n"
        "\n"
        "# Tess\n"
        "\n"
        "## Identity\n"
        "You are Tess.\n"
        "\n"
        "## Critical rules\n"
        "- Score honestly.\n",
        encoding="utf-8",
    )

    p = load_persona(persona_file)

    assert isinstance(p, Persona)
    assert p.name == "Tess"
    assert p.role == "Trend Spotter"
    assert p.emoji == "🔭"
    assert p.brain == "ollama:gemma3:e4b"
    assert p.vibe == "Rigorous and skeptical."
    assert "You are Tess" in p.body
    assert "Critical rules" in p.body


def test_load_persona_round_trips_full_text(tmp_path):
    """Persona's body should preserve the whole markdown after frontmatter
    so prompts can use it verbatim."""
    persona_file = tmp_path / "carla.md"
    persona_file.write_text(
        "---\nname: Carla\nrole: Copywriter\n---\n"
        "# Carla\n\n## Section A\nA-text.\n\n## Section B\nB-text.\n",
        encoding="utf-8",
    )

    p = load_persona(persona_file)

    assert "Section A" in p.body
    assert "Section B" in p.body
    assert "A-text." in p.body


def test_load_persona_missing_frontmatter_raises(tmp_path):
    persona_file = tmp_path / "broken.md"
    persona_file.write_text("# No frontmatter\n", encoding="utf-8")

    with pytest.raises(ValueError, match="frontmatter"):
        load_persona(persona_file)
