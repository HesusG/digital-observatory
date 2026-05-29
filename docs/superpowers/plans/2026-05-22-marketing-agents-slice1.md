# Marketing Agents — Slice 1 (Publishing Loop) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** End-to-end publishing loop where an RSS article → Tess scores → Carla drafts → Edu reviews → user taps ✅ in Telegram → Pablo publishes to Bluesky via Postiz.

**Architecture:** Refactor existing `ai_evaluator.py` and `drafter.py` to load their prompts from markdown persona files (Tess, Carla). Add two new agent modules (Edu the editor, Pablo the publisher). Introduce a `drafts` ChromaDB collection so each (item × platform × language) row has its own lifecycle (`draft → edu_verdict → approved/scheduled/published`). Update n8n workflows to call observatory's new draft-lifecycle endpoints rather than calling Postiz directly. Deploy Postiz last so the loop is end-to-end testable on local before any social account is wired.

**Tech Stack:** Python 3.12, FastAPI, pydantic, ChromaDB HttpClient, httpx, jinja2 (template rendering), pytest, n8n (workflow JSON), Postiz (self-hosted, Docker), Ollama gemma3:e4b on d3r-ser via WOL.

**Spec:** `docs/superpowers/specs/2026-05-22-marketing-agents-design.md` (commit 8cbf218).

---

## Pre-flight: Confirm branch + run tests

You should be on `feat/agent-department-spec`. Confirm:

```bash
cd /home/d3r/repos/digital-observatory
git status
git log --oneline -3
.venv/bin/python -m pytest -q
```

Expected: working tree clean (or with this plan file as an untracked addition), HEAD at `8cbf218 docs: marketing department of agents — design spec`, 42 passing tests.

---

## File-structure map

**New files**

| Path | Responsibility |
|---|---|
| `agents/tess.md` | Tess persona — Trend Spotter (extracted from `ai_evaluator.py::PROMPT_TEMPLATE`) |
| `agents/carla.md` | Carla persona — Copywriter (extracted from `drafter.py::PROMPT_TEMPLATE`) |
| `agents/edu.md` | Edu persona — Editor + brand-voice rules |
| `observatory/agents/__init__.py` | Empty marker |
| `observatory/agents/persona.py` | Loads/parses persona markdown files (frontmatter + sections) |
| `observatory/agents/edu.py` | Edu agent: voice + fact + platform + dup check → verdict |
| `observatory/agents/pablo.py` | Pablo agent: no LLM; relays approved drafts to Postiz |
| `observatory/storage/drafts_store.py` | ChromaDB helpers for the new `drafts` collection |
| `tests/test_persona.py` | Persona loader tests |
| `tests/test_drafts_store.py` | drafts_store tests (chromadb mocked) |
| `tests/test_edu.py` | Edu tests (Ollama mocked) |
| `tests/test_pablo.py` | Pablo tests (httpx_mock) |

**Modified files**

| Path | Change |
|---|---|
| `observatory/intelligence/ai_evaluator.py` | Load PROMPT_TEMPLATE from `agents/tess.md` rather than the inline constant |
| `observatory/intelligence/drafter.py` | Load PROMPT_TEMPLATE / PLATFORM_PROMPTS from `agents/carla.md`; on completion, write each draft to `drafts_store` and return draft IDs instead of bare text |
| `observatory/pipeline.py` | After Carla writes drafts, invoke Edu; only Edu-approved drafts trigger Telegram notification |
| `observatory/app.py` | Add `POST /api/drafts/{id}/approve`, `POST /api/drafts/{id}/skip`, `POST /api/drafts/{id}/edit`, `GET /api/drafts` |
| `config/settings.py` | Add `postiz_base_url`, `postiz_api_key`, `postiz_bluesky_integration_id` |
| `deploy/n8n/marketing-team-{es,en}.json` | After Carla draft step, fetch the `drafts` for that item and post one Telegram message per Edu-approved draft; callback buttons call observatory's approve/skip/edit endpoints |
| `deploy/n8n/marketing-team-callback.json` | Replace inline Postiz call with `POST /api/drafts/{id}/approve` (observatory handles the Postiz hop via Pablo) |

---

## Task 1: Persona file loader

**Files:**
- Create: `agents/tess.md`
- Create: `agents/carla.md`
- Create: `agents/edu.md`
- Create: `observatory/agents/__init__.py`
- Create: `observatory/agents/persona.py`
- Create: `tests/test_persona.py`

The loader is small but pivotal — every agent uses it. We write the loader first, then the persona content, so tests can drive the shape.

- [ ] **Step 1.1: Create empty package marker**

```bash
mkdir -p /home/d3r/repos/digital-observatory/observatory/agents
touch /home/d3r/repos/digital-observatory/observatory/agents/__init__.py
mkdir -p /home/d3r/repos/digital-observatory/agents
```

- [ ] **Step 1.2: Write the failing test**

Create `tests/test_persona.py`:

```python
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
```

- [ ] **Step 1.3: Run the test, see it fail**

```bash
cd /home/d3r/repos/digital-observatory
.venv/bin/python -m pytest tests/test_persona.py -v
```

Expected: `ModuleNotFoundError: No module named 'observatory.agents.persona'`

- [ ] **Step 1.4: Implement the persona loader**

Create `observatory/agents/persona.py`:

```python
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
```

- [ ] **Step 1.5: Run the test, see it pass**

```bash
.venv/bin/python -m pytest tests/test_persona.py -v
```

Expected: 3 PASS.

- [ ] **Step 1.6: Commit**

```bash
cd /home/d3r/repos/digital-observatory
git add observatory/agents/__init__.py observatory/agents/persona.py tests/test_persona.py
git commit -m "feat: add agent persona file loader

Reads markdown files with YAML frontmatter (name, role, vibe, brain,
schedule, tools) and returns a Persona dataclass. Body is preserved
verbatim for use in LLM prompts. Foundation for the marketing-agent
department (see spec 2026-05-22-marketing-agents-design.md).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Write Tess's persona file

**Files:**
- Create: `agents/tess.md`

This persona file becomes the source of truth for Tess's prompt. The next task will refactor `ai_evaluator.py` to load it.

- [ ] **Step 2.1: Write `agents/tess.md`**

```markdown
---
name: Tess
role: Trend Spotter
emoji: 🔭
brain: ollama:gemma3:e4b
schedule: "0 */4 * * *"
vibe: "Rigorous and skeptical; allergic to hype; trusts arxiv over press releases."
tools: [chromadb, rss, wordpress]
---

# 🔭 Tess — Trend Spotter

## Identity

You are Tess, the trend spotter on an "AI for Teachers" marketing team. You
read every AI / EdTech article that comes in and decide whether it's worth
turning into social-media content for high-school + university teachers,
plus AI-curious general public. The course owner profile is below; use it to
calibrate what "useful" looks like for this audience.

## Critical rules

- Score teacher_relevance honestly on a 1-10 scale. "AI is impressive" is
  not relevant; "here's a tool a teacher can use in class on Monday" is.
- Reject corporate news, funding announcements, infrastructure stories, and
  abstract research with no classroom angle by setting
  skip_reason="research-only-no-classroom-angle" (or one of the other
  documented values). Do NOT inflate the score to be polite — a low score
  with a clear skip_reason is more useful than a score-6 maybe.
- lang_targets is about which language audiences should hear this. Many
  arxiv items only matter in English; cross-language only when the
  underlying point translates without friction.
- The summary field must be in the article's original language (you will
  receive that as lang_hint).
- post_angles should be concrete, scenario-led ideas a teacher would
  recognize from their own classroom. Avoid generic "AI is transforming
  education" framings.

## Inputs you receive

- USER PROFILE: the course owner's bio and audience focus
- ARTICLE: full text (already truncated to ~6000 chars)
- lang_hint: ISO-639 code of the article's original language

## Output schema (return ONLY valid JSON, no markdown)

```
{
  "teacher_relevance": <int 1-10>,
  "audience_fit": [<"k12" | "highered" | "ai_curious_public">],
  "lang_targets": [<"es" | "en">],
  "topic_tags": [<2-6 short tags, e.g. "llm", "agents", "rag", "classroom-tool", "evals">],
  "one_line_hook": "<= 140 chars, opens a post a teacher would click",
  "post_angles": [{"angle": <str>, "for": <"k12-en"|"highered-es"|etc>}],
  "suggested_platforms": [<"x" | "linkedin" | "bluesky">],
  "summary": "2 sentences in the article's original language",
  "course_tie_in": <null or one sentence describing a natural course soft-pitch>,
  "skip_reason": <null or "research-only-no-classroom-angle" | "duplicate-of-recent" | "too-niche" | "low-signal">
}
```

## Examples

- GOOD → "OpenAI launches a free gradebook integration for K-12 teachers"
  → score 9, audience: k12, langs: [en, es], hook "Una herramienta que
  califica borradores: ¿la dejarías corregir tu próxima entrega?"

- BAD → "Google announces $500M infrastructure investment in Missouri"
  → score 1, skip_reason="research-only-no-classroom-angle"

- BORDERLINE → "New arxiv paper on chain-of-thought distillation"
  → score 4 only if it has a concrete teaching implication; otherwise
  skip_reason="too-niche"
```

- [ ] **Step 2.2: Commit**

```bash
cd /home/d3r/repos/digital-observatory
git add agents/tess.md
git commit -m "feat: add Tess persona file (Trend Spotter)

Extracted from ai_evaluator.py PROMPT_TEMPLATE plus voice guidance and
worked examples. The next task wires ai_evaluator.py to load this.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Wire Tess persona into `ai_evaluator.py`

**Files:**
- Modify: `observatory/intelligence/ai_evaluator.py`
- Modify: `tests/test_evaluator.py` (only if needed — first check if any AI-evaluator test exists)

- [ ] **Step 3.1: Check the existing AI-evaluator test coverage**

```bash
cd /home/d3r/repos/digital-observatory
grep -n "ai_evaluator\|evaluate_ai_signal\|AIEvaluationResult" tests/test_*.py
```

Expected: ai_evaluator may have no dedicated test file yet. If empty, that's fine — the existing pytest run still passes.

- [ ] **Step 3.2: Add a regression test for Tess persona-loading**

Create `tests/test_ai_evaluator.py`:

```python
from pathlib import Path

from observatory.intelligence import ai_evaluator
from observatory.intelligence.ai_evaluator import build_ai_prompt, parse_ai_response


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_build_ai_prompt_uses_tess_persona():
    """build_ai_prompt should incorporate the Tess persona body verbatim,
    so the model sees the persona's identity and critical rules."""
    prompt = build_ai_prompt(
        user_profile="Course owner: Hesus, AI educator.",
        article_text="Article body about a new gradebook tool.",
    )

    # Hallmarks of the persona body that should be present.
    assert "You are Tess" in prompt
    assert "teacher_relevance" in prompt          # output schema
    assert "skip_reason" in prompt                 # output schema
    assert "Course owner: Hesus" in prompt        # injected user profile
    assert "Article body" in prompt               # injected article


def test_parse_ai_response_well_formed():
    raw = (
        '{"teacher_relevance": 8, "audience_fit": ["k12"], '
        '"lang_targets": ["es","en"], "topic_tags": ["llm","tool"], '
        '"one_line_hook": "Hook here", '
        '"post_angles": [{"angle":"a","for":"k12-en"}], '
        '"suggested_platforms": ["x"], "summary": "Two sentences.", '
        '"course_tie_in": null, "skip_reason": null}'
    )

    r = parse_ai_response(raw)

    assert r.teacher_relevance == 8
    assert r.lang_targets == ["es", "en"]
    assert r.skip_reason is None


def test_parse_ai_response_malformed_returns_skip():
    r = parse_ai_response("not json at all")
    assert r.skip_reason == "parse-error"
```

- [ ] **Step 3.3: Run — see the persona test fail (the prompt still uses the inline PROMPT_TEMPLATE, no "You are Tess")**

```bash
.venv/bin/python -m pytest tests/test_ai_evaluator.py -v
```

Expected: `test_build_ai_prompt_uses_tess_persona` FAILS on `assert "You are Tess" in prompt`. The other two pass.

- [ ] **Step 3.4: Refactor `ai_evaluator.py` to load Tess's persona**

Open `observatory/intelligence/ai_evaluator.py` and replace the `PROMPT_TEMPLATE` constant + `build_ai_prompt` function with a persona-aware version. The complete patched section:

```python
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from config.settings import settings
from observatory.agents.persona import Persona, load_persona
from observatory.monitoring.health import check_ollama

# ... AIEvaluationResult and PostAngle unchanged ...

PERSONA_PATH = Path(__file__).resolve().parents[2] / "agents" / "tess.md"


@lru_cache(maxsize=1)
def _tess_persona() -> Persona:
    return load_persona(PERSONA_PATH)


def build_ai_prompt(user_profile: str, article_text: str) -> str:
    persona = _tess_persona()
    truncated = textwrap.shorten(article_text, width=6000, placeholder="... [truncated]")
    return (
        f"{persona.body}\n\n"
        f"--- USER / COURSE OWNER PROFILE ---\n{user_profile}\n\n"
        f"--- ARTICLE ---\n{truncated}\n\n"
        f"Return ONLY the JSON described in the output schema above. "
        f"No commentary, no markdown fences."
    )
```

Delete the now-unused `PROMPT_TEMPLATE` constant. Keep everything else (`AIEvaluationResult`, `PostAngle`, `parse_ai_response`, `_get_provider`, `evaluate_ai_signal`).

- [ ] **Step 3.5: Run tests, confirm all pass**

```bash
.venv/bin/python -m pytest tests/test_ai_evaluator.py -v
.venv/bin/python -m pytest -q
```

Expected: 3/3 in `test_ai_evaluator.py` PASS, 45/45 total tests PASS (3 new tests + 42 existing).

- [ ] **Step 3.6: Commit**

```bash
git add observatory/intelligence/ai_evaluator.py tests/test_ai_evaluator.py
git commit -m "refactor: load Tess prompt from agents/tess.md persona file

ai_evaluator.py no longer carries an inline PROMPT_TEMPLATE; it loads
the persona body from agents/tess.md and composes the final prompt
around it. Output schema and response parsing unchanged. Adds a
dedicated test module for the AI evaluator (none existed before).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Drafts ChromaDB collection — store helpers

**Files:**
- Create: `observatory/storage/drafts_store.py`
- Create: `tests/test_drafts_store.py`

We use a separate collection so a single article can spawn many drafts (one per platform × lang) with independent lifecycles. Pattern mirrors `chromadb_store.py`.

- [ ] **Step 4.1: Write the failing tests**

Create `tests/test_drafts_store.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from observatory.storage import drafts_store
from observatory.storage.drafts_store import (
    Draft,
    EduVerdict,
    DraftStatus,
    build_draft_id,
)


def test_build_draft_id_is_deterministic():
    a = build_draft_id(item_url="https://x.com/y", platform="x", lang="es")
    b = build_draft_id(item_url="https://x.com/y", platform="x", lang="es")
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_build_draft_id_distinguishes_platform_and_lang():
    base = "https://x.com/y"
    ids = {
        build_draft_id(base, "x", "es"),
        build_draft_id(base, "x", "en"),
        build_draft_id(base, "linkedin", "es"),
        build_draft_id(base, "bluesky", "es"),
    }
    assert len(ids) == 4  # all distinct


@patch.object(drafts_store, "_get_collection")
def test_upsert_draft_writes_expected_metadata(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll

    draft_id = drafts_store.upsert_draft(
        item_url="https://example.com/post",
        platform="x",
        lang="en",
        content="A post body.",
        item_title="Example",
        item_source="Test Source",
    )

    assert draft_id == build_draft_id("https://example.com/post", "x", "en")
    coll.upsert.assert_called_once()
    kwargs = coll.upsert.call_args.kwargs
    assert kwargs["ids"] == [draft_id]
    meta = kwargs["metadatas"][0]
    assert meta["item_url"] == "https://example.com/post"
    assert meta["platform"] == "x"
    assert meta["lang"] == "en"
    assert meta["status"] == "draft"
    assert meta["edu_verdict"] == ""
    assert meta["item_title"] == "Example"


@patch.object(drafts_store, "_get_collection")
def test_update_edu_verdict_writes_status_when_approved(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["draftid123"],
        "metadatas": [{"item_url": "u", "platform": "x", "lang": "en", "status": "draft"}],
    }

    drafts_store.update_edu_verdict(
        draft_id="draftid123",
        verdict=EduVerdict.APPROVED_FOR_REVIEW,
        reasoning="Looks good.",
    )

    coll.update.assert_called_once()
    new_meta = coll.update.call_args.kwargs["metadatas"][0]
    assert new_meta["edu_verdict"] == "approved-for-review"
    assert new_meta["edu_reasoning"] == "Looks good."
    assert new_meta["status"] == "awaiting-user"


@patch.object(drafts_store, "_get_collection")
def test_update_edu_verdict_rejects_set_status_rejected(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["d1"],
        "metadatas": [{"item_url": "u", "platform": "x", "lang": "en", "status": "draft"}],
    }

    drafts_store.update_edu_verdict("d1", EduVerdict.REJECT, "Bad tone.")

    new_meta = coll.update.call_args.kwargs["metadatas"][0]
    assert new_meta["status"] == "rejected"


@patch.object(drafts_store, "_get_collection")
def test_mark_published_records_postiz_id(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["d1"],
        "metadatas": [{"status": "awaiting-user"}],
    }

    drafts_store.mark_published(
        draft_id="d1",
        postiz_post_id="ptz_42",
        scheduled_at="2026-05-22T10:00:00Z",
    )

    meta = coll.update.call_args.kwargs["metadatas"][0]
    assert meta["status"] == "scheduled"
    assert meta["postiz_post_id"] == "ptz_42"
    assert meta["scheduled_at"] == "2026-05-22T10:00:00Z"


@patch.object(drafts_store, "_get_collection")
def test_mark_skipped_sets_status_and_reason(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {"ids": ["d1"], "metadatas": [{"status": "awaiting-user"}]}

    drafts_store.mark_skipped("d1", reason="not-relevant-this-week")

    meta = coll.update.call_args.kwargs["metadatas"][0]
    assert meta["status"] == "skipped"
    assert meta["skip_reason"] == "not-relevant-this-week"


@patch.object(drafts_store, "_get_collection")
def test_list_drafts_by_status_filters(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["d1", "d2", "d3"],
        "metadatas": [
            {"status": "awaiting-user", "platform": "x", "lang": "es"},
            {"status": "scheduled", "platform": "x", "lang": "es"},
            {"status": "awaiting-user", "platform": "linkedin", "lang": "en"},
        ],
        "documents": ["d1c", "d2c", "d3c"],
    }

    result = drafts_store.list_drafts_by_status("awaiting-user")

    assert {r["id"] for r in result} == {"d1", "d3"}
```

- [ ] **Step 4.2: Run — see them fail (module missing)**

```bash
.venv/bin/python -m pytest tests/test_drafts_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'observatory.storage.drafts_store'`.

- [ ] **Step 4.3: Implement `drafts_store.py`**

Create `observatory/storage/drafts_store.py`:

```python
"""ChromaDB helpers for the drafts collection.

One row per (item_url, platform, lang). Lifecycle:

    draft           ← Carla just wrote it
    awaiting-user   ← Edu approved-for-review; sitting in Telegram
    scheduled       ← Pablo handed it to Postiz; postiz_post_id stored
    published       ← Postiz reported success (Ana fills this in)
    skipped         ← user tapped Skip
    rejected        ← Edu vetoed
"""
import hashlib
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config.settings import settings
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_client: Optional[chromadb.HttpClient] = None
_embedding_fn: Optional[SentenceTransformerEmbeddingFunction] = None


class DraftStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_USER = "awaiting-user"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    SKIPPED = "skipped"
    REJECTED = "rejected"


class EduVerdict(str, Enum):
    APPROVED_FOR_REVIEW = "approved-for-review"
    REVISE = "revise"
    REJECT = "reject"


@dataclass
class Draft:
    id: str
    item_url: str
    platform: str
    lang: str
    content: str
    status: str
    edu_verdict: str
    edu_reasoning: str
    postiz_post_id: str
    metadata: dict


def _get_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return _client


def _get_embedding_fn() -> SentenceTransformerEmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model)
    return _embedding_fn


def _get_collection() -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name="drafts",
        embedding_function=_get_embedding_fn(),
        metadata={"hnsw:space": "cosine"},
    )


def build_draft_id(item_url: str, platform: str, lang: str) -> str:
    key = f"{item_url}|{platform}|{lang}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()


def upsert_draft(
    item_url: str,
    platform: str,
    lang: str,
    content: str,
    item_title: str = "",
    item_source: str = "",
) -> str:
    """Create or refresh a draft row. Status starts as 'draft'."""
    draft_id = build_draft_id(item_url, platform, lang)
    coll = _get_collection()
    now = datetime.utcnow().isoformat()
    metadata = {
        "item_url": item_url,
        "platform": platform,
        "lang": lang,
        "status": DraftStatus.DRAFT.value,
        "edu_verdict": "",
        "edu_reasoning": "",
        "postiz_post_id": "",
        "scheduled_at": "",
        "skip_reason": "",
        "item_title": item_title,
        "item_source": item_source,
        "created_at": now,
        "updated_at": now,
    }
    coll.upsert(ids=[draft_id], documents=[content], metadatas=[metadata])
    return draft_id


def _read(draft_id: str) -> Optional[dict]:
    coll = _get_collection()
    res = coll.get(ids=[draft_id], include=["metadatas", "documents"])
    if not res["ids"]:
        return None
    return {
        "id": res["ids"][0],
        "metadata": res["metadatas"][0] if res["metadatas"] else {},
        "document": res["documents"][0] if res["documents"] else "",
    }


def _merge_meta(draft_id: str, patch: dict) -> None:
    coll = _get_collection()
    existing = coll.get(ids=[draft_id])
    if not existing["ids"]:
        logger.warning("Unknown draft id: %s", draft_id[:12])
        return
    meta = existing["metadatas"][0] if existing["metadatas"] else {}
    meta.update(patch)
    meta["updated_at"] = datetime.utcnow().isoformat()
    coll.update(ids=[draft_id], metadatas=[meta])


def update_edu_verdict(
    draft_id: str,
    verdict: EduVerdict,
    reasoning: str = "",
) -> None:
    if verdict == EduVerdict.APPROVED_FOR_REVIEW:
        status = DraftStatus.AWAITING_USER.value
    elif verdict == EduVerdict.REJECT:
        status = DraftStatus.REJECTED.value
    else:  # REVISE
        status = DraftStatus.DRAFT.value
    _merge_meta(draft_id, {
        "edu_verdict": verdict.value,
        "edu_reasoning": reasoning,
        "status": status,
    })


def mark_published(draft_id: str, postiz_post_id: str, scheduled_at: str = "") -> None:
    _merge_meta(draft_id, {
        "status": DraftStatus.SCHEDULED.value,
        "postiz_post_id": postiz_post_id,
        "scheduled_at": scheduled_at,
    })


def mark_skipped(draft_id: str, reason: str = "user-skip") -> None:
    _merge_meta(draft_id, {
        "status": DraftStatus.SKIPPED.value,
        "skip_reason": reason,
    })


def get_draft(draft_id: str) -> Optional[dict]:
    return _read(draft_id)


def list_drafts_by_status(status: str, limit: int = 100) -> list[dict]:
    coll = _get_collection()
    try:
        res = coll.get(include=["metadatas", "documents"])
    except Exception as e:
        logger.error("ChromaDB get failed: %s", e)
        return []
    out: list[dict] = []
    if not res["ids"]:
        return out
    for i, doc_id in enumerate(res["ids"]):
        meta = res["metadatas"][i] if res["metadatas"] else {}
        if meta.get("status") != status:
            continue
        out.append({
            "id": doc_id,
            "metadata": meta,
            "document": res["documents"][i] if res["documents"] else "",
        })
        if len(out) >= limit:
            break
    return out
```

- [ ] **Step 4.4: Run tests, confirm all pass**

```bash
.venv/bin/python -m pytest tests/test_drafts_store.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 4.5: Commit**

```bash
git add observatory/storage/drafts_store.py tests/test_drafts_store.py
git commit -m "feat: drafts ChromaDB collection + lifecycle helpers

New 'drafts' collection stores one row per (item, platform, lang) with
status (draft → awaiting-user → scheduled → published | skipped |
rejected) and Edu's verdict + reasoning. Helpers: upsert_draft,
update_edu_verdict, mark_published, mark_skipped, get_draft,
list_drafts_by_status.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Write Carla's persona file

**Files:**
- Create: `agents/carla.md`

- [ ] **Step 5.1: Write `agents/carla.md`**

```markdown
---
name: Carla
role: Copywriter
emoji: ✍️
brain: ollama:gemma3:e4b
schedule: "triggered-after-tess"
vibe: "Warm, precise, teacher-empathic; opens with a classroom scenario; never hypey."
tools: [chromadb, drafts_store]
---

# ✍️ Carla — Copywriter

## Identity

You are Carla, the copywriter on an "AI for Teachers" marketing team. You
take a Tess-tagged article and turn it into one post per platform per
language. Your audience is a high-school or university teacher who is
curious about AI but skeptical of hype. They want concrete, classroom-ready
ideas.

## Critical rules

- Open with a sentence that a teacher would recognize from their own day —
  a scenario, a question, a confession. NOT "AI is transforming education."
- Use the article's hook, summary, and one of the post_angles as your
  spine. Don't invent claims the article didn't make.
- Voice: warm, precise, never hypey. The teacher should feel respected,
  not lectured. No "🚀" "💯" emoji walls. One emoji per post, max, and only
  if it's natural.
- Respect platform spec strictly:
  - **X**: ≤ 280 chars single, or JSON array of 2-4 thread tweets each ≤ 280.
  - **LinkedIn**: ≤ 1300 chars, 3-6 short paragraphs separated by blank lines.
    Open with a teacher scenario. End with a question. Never include bare
    links in the body — say "link in comments" if a URL is essential.
  - **Bluesky**: ≤ 300 chars single, or JSON array of 2-3 thread posts.
- If include_course_cta is true, soft-pitch the AI-for-Teachers course in
  the last paragraph. One sentence, no hard sell, leave a hook.
- If a thread is needed, return a JSON array of strings. Otherwise return
  a plain string. NO markdown fences, NO commentary.

## Inputs

- ARTICLE HOOK (already approved by Tess)
- ARTICLE SUMMARY
- POST ANGLES (3-5; pick the one most native to your assigned platform/lang)
- PLATFORM (x | linkedin | bluesky)
- LANG (es | en)
- INCLUDE_COURSE_CTA (true | false)
- TONE_OVERRIDE (optional one-line modifier)

## Output

Return ONLY the post text:
- single string  → just the post
- JSON array     → thread (only when the platform spec asks for one)

Examples (English, X, single):

GOOD: "I used to grade essays at 11pm with a glass of wine. Now Claude
suggests rubric matches in 4 seconds. Same wine, smaller pile."

BAD: "🚀 AI is REVOLUTIONIZING education! 🚀 Don't get left behind!"
```

- [ ] **Step 5.2: Commit**

```bash
git add agents/carla.md
git commit -m "feat: add Carla persona file (Copywriter)

Extracted from drafter.py PROMPT_TEMPLATE with refined voice guidance.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Wire Carla persona into `drafter.py` + write drafts to store

**Files:**
- Modify: `observatory/intelligence/drafter.py`
- Create: `tests/test_drafter.py`

- [ ] **Step 6.1: Write the failing tests**

Create `tests/test_drafter.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from observatory.intelligence import drafter
from observatory.intelligence.drafter import build_platform_prompt, _parse_platform_output


def test_build_platform_prompt_includes_carla_persona():
    prompt = build_platform_prompt(
        platform="x",
        lang="es",
        hook="Hook here",
        summary="Summary.",
        angles=[{"angle": "ang1", "for": "k12-es"}],
        include_course_cta=False,
        tone="",
    )
    assert "You are Carla" in prompt
    assert "x" in prompt.lower()           # platform name referenced
    assert "Hook here" in prompt
    assert "Summary." in prompt
    assert "ang1" in prompt


def test_parse_platform_output_thread_array():
    out = _parse_platform_output('["one tweet", "two tweet"]', 280)
    assert out == ["one tweet", "two tweet"]


def test_parse_platform_output_single_truncates_to_limit():
    long = "x" * 500
    out = _parse_platform_output(long, 280)
    assert isinstance(out, str)
    assert len(out) == 280


@pytest.mark.asyncio
async def test_draft_for_platforms_persists_each_draft(monkeypatch):
    """draft_for_platforms must write one drafts_store row per platform."""
    upsert_calls = []

    def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return "fake-draft-id-" + kwargs["platform"]

    monkeypatch.setattr(drafter, "upsert_draft", fake_upsert)

    # Mock the LLM provider to return deterministic per-platform text.
    fake_provider = AsyncMock()
    fake_provider.ainvoke = AsyncMock(side_effect=[
        MagicMock(content="x-post"),
        MagicMock(content="linkedin-post"),
        MagicMock(content="bluesky-post"),
    ])
    async def fake_get_provider():
        return fake_provider

    monkeypatch.setattr(drafter, "_get_provider", fake_get_provider)

    result = await drafter.draft_for_platforms(
        item_url="https://example.com/x",
        item_title="Title",
        item_source="Source",
        hook="Hook",
        summary="Summary",
        angles=[],
        platforms=["x", "linkedin", "bluesky"],
        lang="en",
    )

    assert len(upsert_calls) == 3
    platforms_persisted = {c["platform"] for c in upsert_calls}
    assert platforms_persisted == {"x", "linkedin", "bluesky"}
    assert result["x"] == "x-post"
    assert result["linkedin"] == "linkedin-post"
    assert "draft_ids" in result
    assert result["draft_ids"]["x"] == "fake-draft-id-x"
```

- [ ] **Step 6.2: Run — see failures**

```bash
.venv/bin/python -m pytest tests/test_drafter.py -v
```

Expected:
- `test_build_platform_prompt_includes_carla_persona` FAILS (no "You are Carla" in current prompt)
- `test_parse_platform_output_*` PASS (already work)
- `test_draft_for_platforms_persists_each_draft` FAILS (no `upsert_draft` attribute on drafter, and signature doesn't match)

- [ ] **Step 6.3: Refactor `drafter.py`**

Open `observatory/intelligence/drafter.py`. Replace the `PLATFORM_PROMPTS`, `LANG_LABELS`, `PROMPT_TEMPLATE`, `build_platform_prompt`, and `draft_for_platforms` portions with:

```python
import asyncio
import json
import logging
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Optional

from config.settings import settings
from observatory.agents.persona import Persona, load_persona
from observatory.monitoring.health import check_ollama
from observatory.storage.drafts_store import upsert_draft

logger = logging.getLogger(__name__)


PLATFORM_PROMPTS = {
    "x":        {"limit_chars": 280},
    "linkedin": {"limit_chars": 1300},
    "bluesky":  {"limit_chars": 300},
}

LANG_LABELS = {"es": "Spanish (es-MX register)", "en": "English"}


PERSONA_PATH = Path(__file__).resolve().parents[2] / "agents" / "carla.md"


@lru_cache(maxsize=1)
def _carla_persona() -> Persona:
    return load_persona(PERSONA_PATH)


def _format_angles(angles: list[dict], lang: str) -> str:
    if not angles:
        return "(no angles provided)"
    lines = []
    for a in angles:
        if not isinstance(a, dict):
            lines.append(f"- {a}")
            continue
        for_tag = str(a.get("for", ""))
        lines.append(f"- ({for_tag}) {a.get('angle','')}" if for_tag else f"- {a.get('angle','')}")
    return "\n".join(lines)


def build_platform_prompt(
    platform: str,
    lang: str,
    hook: str,
    summary: str,
    angles: list[dict],
    include_course_cta: bool,
    tone: str = "",
) -> str:
    persona = _carla_persona()
    limit = PLATFORM_PROMPTS[platform]["limit_chars"]
    lang_label = LANG_LABELS.get(lang, lang)
    cta_block = (
        "include_course_cta=true: soft-pitch the course in the last paragraph."
        if include_course_cta
        else "include_course_cta=false: do not mention the course."
    )
    tone_block = f"tone_override: {tone}" if tone else "tone_override: (none)"

    return (
        f"{persona.body}\n\n"
        f"--- ASSIGNMENT ---\n"
        f"platform: {platform} (char limit {limit})\n"
        f"lang: {lang_label}\n"
        f"hook: {hook}\n"
        f"summary: {textwrap.shorten(summary or '(no summary)', width=600, placeholder='...')}\n"
        f"angles:\n{_format_angles(angles, lang)}\n"
        f"{cta_block}\n"
        f"{tone_block}\n\n"
        f"Return ONLY the post text. If platform requires a thread, return a JSON "
        f"array of strings. Otherwise a plain string. No markdown fences."
    )


def _parse_platform_output(raw: str, char_limit: int) -> str | list[str]:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    if cleaned.startswith("["):
        try:
            arr = json.loads(cleaned)
            if isinstance(arr, list):
                return [str(p)[:char_limit] for p in arr]
        except json.JSONDecodeError:
            pass
    return cleaned[: char_limit if char_limit > 0 else len(cleaned)]


async def _get_provider():
    if not await check_ollama():
        logger.error(
            "Ollama unreachable at %s — d3r-ser asleep; drafter cannot produce content.",
            settings.ollama_base_url,
        )
        return None
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.7,
        )
    except Exception as e:
        logger.error("Ollama provider failed to initialize: %s", e)
        return None


async def draft_for_platforms(
    hook: str,
    summary: str,
    angles: list[dict],
    platforms: list[str],
    lang: str,
    item_url: str = "",
    item_title: str = "",
    item_source: str = "",
    include_course_cta: bool = False,
    tone: str = "",
) -> dict:
    """Generate per-platform drafts AND persist each one to the drafts collection.

    Returns:
        {
          "x": "<post text or thread list>",
          "linkedin": ...,
          "bluesky": ...,
          "draft_ids": {"x": "<draft id>", "linkedin": ..., "bluesky": ...},
        }
    """
    provider = await _get_provider()
    if provider is None:
        return {p: "" for p in platforms} | {"draft_ids": {}}

    from langchain_core.messages import HumanMessage

    async def one(platform: str) -> tuple[str, str | list[str]]:
        if platform not in PLATFORM_PROMPTS:
            return platform, ""
        prompt = build_platform_prompt(
            platform=platform, lang=lang,
            hook=hook, summary=summary, angles=angles,
            include_course_cta=include_course_cta, tone=tone,
        )
        try:
            response = await provider.ainvoke([HumanMessage(content=prompt)])
            return platform, _parse_platform_output(
                response.content, PLATFORM_PROMPTS[platform]["limit_chars"]
            )
        except Exception as e:
            logger.error("Draft failed for %s/%s: %s", platform, lang, e)
            return platform, ""

    results = await asyncio.gather(*(one(p) for p in platforms))

    drafts_dict: dict[str, str | list[str]] = {}
    draft_ids: dict[str, str] = {}
    for platform, content in results:
        drafts_dict[platform] = content
        if not content or not item_url:
            continue
        body = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        draft_id = upsert_draft(
            item_url=item_url,
            platform=platform,
            lang=lang,
            content=body,
            item_title=item_title,
            item_source=item_source,
        )
        draft_ids[platform] = draft_id

    drafts_dict["draft_ids"] = draft_ids
    return drafts_dict
```

- [ ] **Step 6.4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_drafter.py -v
.venv/bin/python -m pytest -q
```

Expected: all 4 in `test_drafter.py` PASS, full suite still green (49 total).

- [ ] **Step 6.5: Update `app.py::content_draft` to pass item context**

The existing endpoint already pulls the item from ChromaDB and calls `draft_for_platforms`. Add `item_url`/`item_title`/`item_source` to the call. Open `observatory/app.py`, find the `content_draft` handler, and modify the call:

```python
drafts = await draft_for_platforms(
    hook=meta.get("one_line_hook", "") or meta.get("title", ""),
    summary=meta.get("summary", ""),
    angles=angles,
    platforms=list(platforms),
    lang=lang,
    item_url=url,
    item_title=meta.get("title", ""),
    item_source=meta.get("source", ""),
    include_course_cta=include_course_cta,
    tone=tone,
)
```

- [ ] **Step 6.6: Re-run full test suite**

```bash
.venv/bin/python -m pytest -q
```

Expected: 49/49 PASS.

- [ ] **Step 6.7: Commit**

```bash
git add observatory/intelligence/drafter.py observatory/app.py tests/test_drafter.py
git commit -m "refactor: Carla drafter loads persona + persists drafts

drafter.py now loads its prompt from agents/carla.md, and each generated
draft is written to the new chromadb.drafts collection (status=draft).
Returns draft_ids alongside the inline text so downstream callers can
follow the lifecycle. app.py /api/content/draft passes item context so
each draft links back to its source article.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Edu persona file

**Files:**
- Create: `agents/edu.md`

- [ ] **Step 7.1: Write `agents/edu.md`**

```markdown
---
name: Edu
role: Editor
emoji: 📐
brain: ollama:gemma3:e4b
schedule: "triggered-after-carla"
vibe: "Skeptical reader; protects the audience's time; would rather kill a draft than ship a 6/10."
tools: [chromadb, drafts_store]
---

# 📐 Edu — Editor

## Identity

You are Edu, the editor and quality gate on an "AI for Teachers" marketing
team. Every post Carla writes passes through you before it reaches the
user's Telegram approval queue. Your job is to protect the audience from
weak drafts and protect the user from approving mediocrity by reflex.

## Critical rules

You must check FOUR things on every draft:

1. **Voice / tone**
   - Is the opening a recognizable teacher scenario, question, or
     confession? (NOT "AI is transforming education.")
   - Does it sound warm, precise, and respectful of the reader's
     intelligence? Hype, "🚀💯" walls, or motivational-poster cadence are
     immediate fails.
   - Is there a defensible point of view? Vague neutrality earns
     verdict=revise.

2. **Fact / claim sanity**
   - Are AI-tool capabilities described accurately? (e.g., "Claude grades
     essays" is OK; "Claude grades essays with 100% accuracy" is not.)
   - Are pedagogical claims plausible? (e.g., "students learn better with
     X" needs a concrete mechanism, not a feel.)
   - If you see numbers (percentages, dates, model sizes), flag any that
     look suspicious in your reasoning, even if you can't verify.

3. **Platform rule compliance**
   - **X**: ≤ 280 chars per tweet (single or thread).
   - **LinkedIn**: ≤ 1300 chars, no bare URLs in the body, paragraph
     breaks present.
   - **Bluesky**: ≤ 300 chars per post (single or thread).
   - Fail with verdict=revise if any limit is broken.

4. **Soft duplicate check**
   - You will receive a list of the last-30-days post titles + hooks. If
     this draft repeats an angle that already ran in the last 14 days
     verbatim or near-verbatim, verdict=reject with reasoning citing the
     prior post.

## Verdicts

- **approved-for-review** — ships to the user's Telegram for HITL approval.
- **revise** — write a one-paragraph hand-back to Carla explaining what to
  fix. Carla's next cycle re-drafts.
- **reject** — kill the draft entirely. Use sparingly: only for hard
  duplicates, factually broken claims you cannot fix by rewording, or
  drafts that would damage the brand.

## Inputs you receive

- DRAFT TEXT (the post Carla wrote)
- PLATFORM (x | linkedin | bluesky)
- LANG (es | en)
- ARTICLE HOOK + SUMMARY (for context)
- RECENT POSTS (last-30-days, title + hook, for the duplicate check)

## Output schema (return ONLY valid JSON, no markdown fences)

```
{
  "verdict": "approved-for-review" | "revise" | "reject",
  "reasoning": "<1-3 sentences explaining the verdict>",
  "fail_categories": [<subset of "voice", "facts", "platform", "duplicate">],
  "hand_back": "<only when verdict=revise: one-paragraph note to Carla>"
}
```

## Example outputs

GOOD draft (English, X, single):
"I used to grade essays at 11pm with wine. Now Claude suggests rubric
matches in 4s. Same wine, smaller pile."

→ {"verdict": "approved-for-review", "reasoning": "Strong opening scenario,
honest tone, fits the 280-char limit, no false claims.", "fail_categories":
[], "hand_back": ""}

BAD draft:
"🚀 AI is REVOLUTIONIZING education! Don't get left behind! 💯"

→ {"verdict": "reject", "reasoning": "Pure hype, no concrete claim,
emoji-spam violates voice guidelines.", "fail_categories": ["voice"],
"hand_back": ""}

PLATFORM-FAIL draft (LinkedIn, 1450 chars):
→ {"verdict": "revise", "reasoning": "Over 1300-char LinkedIn limit by
150.", "fail_categories": ["platform"], "hand_back": "Trim to ~1200
chars; cut the third paragraph which restates the second."}
```

- [ ] **Step 7.2: Commit**

```bash
git add agents/edu.md
git commit -m "feat: add Edu persona file (Editor)

Defines the 4-check quality gate (voice, facts, platform, duplicate) and
the verdict schema (approved-for-review | revise | reject).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Edu agent module

**Files:**
- Create: `observatory/agents/edu.py`
- Create: `tests/test_edu.py`

- [ ] **Step 8.1: Write the failing tests**

Create `tests/test_edu.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from observatory.agents import edu


def test_parse_edu_response_well_formed():
    raw = (
        '{"verdict": "approved-for-review", "reasoning": "Good.", '
        '"fail_categories": [], "hand_back": ""}'
    )
    r = edu.parse_edu_response(raw)
    assert r.verdict == "approved-for-review"
    assert r.reasoning == "Good."
    assert r.fail_categories == []


def test_parse_edu_response_revise_with_handback():
    raw = (
        '{"verdict": "revise", "reasoning": "Over X limit.", '
        '"fail_categories": ["platform"], "hand_back": "Trim by 50 chars."}'
    )
    r = edu.parse_edu_response(raw)
    assert r.verdict == "revise"
    assert "platform" in r.fail_categories
    assert "Trim by 50 chars." in r.hand_back


def test_parse_edu_response_malformed_returns_revise():
    """When the model returns garbage, we default to revise (safer than
    rejecting a draft that might be fine)."""
    r = edu.parse_edu_response("not json")
    assert r.verdict == "revise"
    assert "parse-error" in r.reasoning.lower()


def test_build_edu_prompt_includes_persona_and_inputs():
    prompt = edu.build_edu_prompt(
        draft_text="A draft.",
        platform="x",
        lang="en",
        hook="Hook.",
        summary="Summary.",
        recent_posts=[{"title": "Old post", "hook": "Old hook"}],
    )
    assert "You are Edu" in prompt
    assert "A draft." in prompt
    assert "Old post" in prompt
    assert "x" in prompt.lower()


@pytest.mark.asyncio
async def test_review_draft_returns_verdict(monkeypatch):
    """End-to-end happy path: mocked Ollama returns approved-for-review."""
    fake_provider = AsyncMock()
    fake_provider.ainvoke = AsyncMock(return_value=MagicMock(
        content='{"verdict":"approved-for-review","reasoning":"OK.","fail_categories":[],"hand_back":""}'
    ))

    async def fake_get_provider():
        return fake_provider

    monkeypatch.setattr(edu, "_get_provider", fake_get_provider)

    verdict = await edu.review_draft(
        draft_text="A draft.",
        platform="x",
        lang="en",
        hook="Hook.",
        summary="Summary.",
        recent_posts=[],
    )

    assert verdict.verdict == "approved-for-review"


@pytest.mark.asyncio
async def test_review_draft_ollama_unreachable_returns_revise(monkeypatch):
    """If Ollama is down, we revise (not reject) — fail-safe."""
    async def fake_get_provider():
        return None

    monkeypatch.setattr(edu, "_get_provider", fake_get_provider)

    verdict = await edu.review_draft(
        draft_text="A draft.",
        platform="x",
        lang="en",
        hook="Hook.",
        summary="Summary.",
        recent_posts=[],
    )

    assert verdict.verdict == "revise"
    assert "unavailable" in verdict.reasoning.lower()
```

- [ ] **Step 8.2: Run — failures expected**

```bash
.venv/bin/python -m pytest tests/test_edu.py -v
```

Expected: `ModuleNotFoundError: No module named 'observatory.agents.edu'`.

- [ ] **Step 8.3: Implement `observatory/agents/edu.py`**

```python
"""Edu — Editor agent. Reviews Carla's drafts and emits a verdict."""
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from config.settings import settings
from observatory.agents.persona import Persona, load_persona
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)


PERSONA_PATH = Path(__file__).resolve().parents[2] / "agents" / "edu.md"


@dataclass
class EduResult:
    verdict: str  # "approved-for-review" | "revise" | "reject"
    reasoning: str
    fail_categories: list[str]
    hand_back: str


@lru_cache(maxsize=1)
def _edu_persona() -> Persona:
    return load_persona(PERSONA_PATH)


def build_edu_prompt(
    draft_text: str,
    platform: str,
    lang: str,
    hook: str,
    summary: str,
    recent_posts: list[dict],
) -> str:
    persona = _edu_persona()
    recent_lines = "\n".join(
        f"- {r.get('title','?')}: {r.get('hook','')[:80]}" for r in recent_posts
    ) or "(no recent posts yet)"
    return (
        f"{persona.body}\n\n"
        f"--- ASSIGNMENT ---\n"
        f"platform: {platform}\n"
        f"lang: {lang}\n"
        f"article_hook: {hook}\n"
        f"article_summary: {summary}\n\n"
        f"--- RECENT POSTS (last 30 days) ---\n{recent_lines}\n\n"
        f"--- DRAFT TO REVIEW ---\n{draft_text}\n\n"
        f"Return ONLY the verdict JSON described above. No markdown fences."
    )


def parse_edu_response(raw: str) -> EduResult:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        return EduResult(
            verdict=str(data.get("verdict", "revise")),
            reasoning=str(data.get("reasoning", "")),
            fail_categories=list(data.get("fail_categories") or []),
            hand_back=str(data.get("hand_back", "")),
        )
    except (json.JSONDecodeError, ValueError):
        return EduResult(
            verdict="revise",
            reasoning="parse-error: editor response was not valid JSON",
            fail_categories=[],
            hand_back="",
        )


async def _get_provider():
    if not await check_ollama():
        logger.error(
            "Ollama unreachable at %s — Edu cannot review drafts.",
            settings.ollama_base_url,
        )
        return None
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.1,  # low — Edu should be consistent
        )
    except Exception as e:
        logger.error("Edu provider failed to initialize: %s", e)
        return None


async def review_draft(
    draft_text: str,
    platform: str,
    lang: str,
    hook: str,
    summary: str,
    recent_posts: list[dict],
) -> EduResult:
    provider = await _get_provider()
    if provider is None:
        return EduResult(
            verdict="revise",
            reasoning="Editor unavailable (Ollama unreachable); not approving by default.",
            fail_categories=[],
            hand_back="",
        )

    prompt = build_edu_prompt(draft_text, platform, lang, hook, summary, recent_posts)

    try:
        from langchain_core.messages import HumanMessage
        response = await provider.ainvoke([HumanMessage(content=prompt)])
        return parse_edu_response(response.content)
    except Exception as e:
        logger.error("Edu review failed: %s", e)
        return EduResult(
            verdict="revise",
            reasoning=f"editor-error: {e}",
            fail_categories=[],
            hand_back="",
        )
```

- [ ] **Step 8.4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_edu.py -v
```

Expected: all 6 PASS.

- [ ] **Step 8.5: Commit**

```bash
git add observatory/agents/edu.py tests/test_edu.py
git commit -m "feat: Edu editor agent (voice/facts/platform/duplicate gate)

review_draft returns an EduResult with verdict
(approved-for-review|revise|reject), reasoning, fail_categories, and an
optional hand_back paragraph for Carla. Fails safe to verdict=revise on
malformed responses or Ollama outages.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Wire Edu into the pipeline

**Files:**
- Modify: `observatory/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 9.1: Inspect the current pipeline article branch**

```bash
grep -n "_process_article\|evaluate_ai_signal\|write_article_drafts" observatory/pipeline.py
```

Expected: there is an `_process_article` helper that calls `evaluate_ai_signal` and `write_article_drafts`. We will add a call to Edu after Carla finishes (via `write_article_drafts`).

Note: Carla today is wrapped by `write_article_drafts` (vault writer). That helper writes vault markdown but doesn't currently call `drafts_store`. We integrate drafts_store + Edu inside `_process_article` after the AI evaluation.

- [ ] **Step 9.2: Write the failing pipeline test**

Add to `tests/test_pipeline.py` (or create a new fixture-friendly section):

```python
from unittest.mock import AsyncMock, patch

import pytest

from observatory import pipeline
from observatory.storage.models import CollectedItem


@pytest.mark.asyncio
async def test_pipeline_article_path_invokes_edu_per_draft(monkeypatch):
    """When an article passes Tess, every Carla draft must go through Edu."""
    edu_calls = []

    fake_ai_eval = AsyncMock()
    fake_ai_eval.return_value = type("E", (), dict(
        teacher_relevance=8,
        lang_targets=["en"],
        audience_fit=["k12"],
        topic_tags=["llm"],
        post_angles=[{"angle": "a1", "for": "k12-en"}],
        suggested_platforms=["x", "linkedin"],
        one_line_hook="Hook",
        summary="Two sentences.",
        course_tie_in=None,
        skip_reason=None,
    ))()
    monkeypatch.setattr(pipeline, "evaluate_ai_signal", AsyncMock(return_value=fake_ai_eval))

    async def fake_write_drafts(item, evaluation):
        # Simulate Carla writing two drafts (x, linkedin) returning their IDs.
        return [{"id": "draft-x", "platform": "x", "content": "x text"},
                {"id": "draft-li", "platform": "linkedin", "content": "li text"}]

    monkeypatch.setattr(pipeline, "carla_draft_for_item", fake_write_drafts)

    async def fake_review(**kwargs):
        edu_calls.append(kwargs)
        return type("V", (), {"verdict": "approved-for-review", "reasoning": "ok",
                              "fail_categories": [], "hand_back": ""})()
    monkeypatch.setattr(pipeline, "edu_review_draft", fake_review)

    monkeypatch.setattr(pipeline, "drafts_update_verdict", lambda *a, **kw: None)

    item = CollectedItem(
        url="https://example.com/a",
        title="T",
        source="S",
        source_type="rss",
        raw_text="body",
        kind="article",
        source_group="ai_news",
        lang_hint="en",
    )
    result = pipeline.PipelineResult()
    await pipeline._process_article(item, result)

    assert len(edu_calls) == 2
    assert {c["platform"] for c in edu_calls} == {"x", "linkedin"}
```

- [ ] **Step 9.3: Run — see failure**

```bash
.venv/bin/python -m pytest tests/test_pipeline.py::test_pipeline_article_path_invokes_edu_per_draft -v
```

Expected: AttributeError or similar — the new functions are not wired yet.

- [ ] **Step 9.4: Modify `pipeline.py`**

Open `observatory/pipeline.py`. At the top, add:

```python
from observatory.agents.edu import review_draft as edu_review_draft
from observatory.storage import drafts_store
from observatory.storage.drafts_store import EduVerdict


# Thin indirection so tests can monkey-patch this entry point.
async def carla_draft_for_item(item, evaluation) -> list[dict]:
    """Generate per-platform drafts for `item`, persist them to drafts_store,
    return [{id, platform, content}, ...].

    Today drafter.draft_for_platforms persists drafts itself; we call it
    once per lang in evaluation.lang_targets and aggregate."""
    from observatory.intelligence.drafter import draft_for_platforms
    out: list[dict] = []
    for lang in evaluation.lang_targets:
        platforms = evaluation.suggested_platforms or settings.ai_default_platforms
        result = await draft_for_platforms(
            hook=evaluation.one_line_hook,
            summary=evaluation.summary,
            angles=evaluation.post_angles,
            platforms=platforms,
            lang=lang,
            item_url=item.url,
            item_title=item.title,
            item_source=item.source,
            include_course_cta=False,
        )
        for platform in platforms:
            content = result.get(platform)
            draft_id = result.get("draft_ids", {}).get(platform)
            if content and draft_id:
                out.append({"id": draft_id, "platform": platform, "lang": lang, "content": content})
    return out


def drafts_update_verdict(draft_id, verdict, reasoning):
    drafts_store.update_edu_verdict(
        draft_id=draft_id,
        verdict=verdict,
        reasoning=reasoning,
    )
```

Then find `_process_article` and modify it so after the AI eval and existing vault write, it calls Carla → Edu per draft:

```python
async def _process_article(item: CollectedItem, result: PipelineResult) -> None:
    evaluation = await evaluate_ai_signal(item.raw_text)
    if evaluation is None:
        result.eval_failures += 1
        metrics.llm_errors.labels(provider="unknown").inc()
        return

    result.evaluated += 1
    metrics.items_evaluated.labels(source=item.source).inc()

    chromadb_store.update_item_ai_evaluation(
        url=item.url,
        teacher_relevance=evaluation.teacher_relevance,
        audience_fit=evaluation.audience_fit,
        lang_targets=evaluation.lang_targets,
        topic_tags=evaluation.topic_tags,
        post_angles=evaluation.post_angles,
        suggested_platforms=evaluation.suggested_platforms,
        one_line_hook=evaluation.one_line_hook,
        summary=evaluation.summary,
        course_tie_in=evaluation.course_tie_in or "",
        skip_reason=evaluation.skip_reason or "",
    )

    if evaluation.skip_reason:
        return

    if evaluation.teacher_relevance < settings.ai_article_min_relevance:
        return

    # Vault drafts for human-readable inbox (existing behavior).
    written = await write_article_drafts(item, evaluation)
    result.articles_drafted += len(written)

    # Carla → Edu per draft.
    drafts = await carla_draft_for_item(item, evaluation)
    for draft in drafts:
        verdict = await edu_review_draft(
            draft_text=draft["content"] if isinstance(draft["content"], str) else "\n".join(draft["content"]),
            platform=draft["platform"],
            lang=draft["lang"],
            hook=evaluation.one_line_hook,
            summary=evaluation.summary,
            recent_posts=[],  # Slice 1: empty; Slice 2 will populate from ChromaDB
        )
        drafts_update_verdict(
            draft_id=draft["id"],
            verdict=EduVerdict(verdict.verdict) if verdict.verdict in {v.value for v in EduVerdict} else EduVerdict.REVISE,
            reasoning=verdict.reasoning,
        )
        logger.info("Edu %s draft %s (%s/%s): %s",
                    verdict.verdict, draft["id"][:12], draft["platform"], draft["lang"], verdict.reasoning[:80])
```

- [ ] **Step 9.5: Run tests**

```bash
.venv/bin/python -m pytest tests/test_pipeline.py -v
.venv/bin/python -m pytest -q
```

Expected: the new pipeline test PASSES; all existing tests still PASS.

- [ ] **Step 9.6: Commit**

```bash
git add observatory/pipeline.py tests/test_pipeline.py
git commit -m "feat: wire Edu review into the article path of the pipeline

After Carla writes per-platform drafts, each one is reviewed by Edu and
the verdict is stored on the draft row. Drafts marked
approved-for-review move to status=awaiting-user; revise/reject change
status accordingly. recent_posts is empty in Slice 1; populated in
Slice 2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Pablo — Postiz client + agent module

**Files:**
- Modify: `config/settings.py`
- Create: `observatory/agents/pablo.py`
- Create: `tests/test_pablo.py`

- [ ] **Step 10.1: Add Postiz settings**

In `config/settings.py`, add (next to the existing WOL block):

```python
    # Postiz publisher (see deploy/postiz/)
    postiz_base_url: str = "http://100.84.156.15:5000"
    postiz_api_key: str = ""
    postiz_bluesky_integration_id: str = ""
```

- [ ] **Step 10.2: Write the failing tests**

Create `tests/test_pablo.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from observatory.agents import pablo


@pytest.mark.asyncio
async def test_publish_draft_happy_path(monkeypatch):
    """Pablo posts to Postiz, captures postiz_post_id, marks the draft scheduled."""
    monkeypatch.setattr(pablo.settings, "postiz_base_url", "http://test:5000")
    monkeypatch.setattr(pablo.settings, "postiz_api_key", "key123")
    monkeypatch.setattr(pablo.settings, "postiz_bluesky_integration_id", "int-bsky")

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"posts": [{"id": "ptz-42"}]}
    fake_resp.raise_for_status = MagicMock()

    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = False
    fake_client.post.return_value = fake_resp

    monkeypatch.setattr(pablo.httpx, "AsyncClient", lambda **kw: fake_client)

    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: {
        "id": did,
        "metadata": {
            "platform": "bluesky",
            "lang": "en",
            "status": "awaiting-user",
        },
        "document": "Hello world.",
    })

    marks = []
    monkeypatch.setattr(pablo.drafts_store, "mark_published", lambda **kw: marks.append(kw))

    result = await pablo.publish_draft("draft-abc")

    assert result.ok is True
    assert result.postiz_post_id == "ptz-42"
    assert marks and marks[0]["postiz_post_id"] == "ptz-42"


@pytest.mark.asyncio
async def test_publish_draft_unknown_draft_returns_error(monkeypatch):
    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: None)
    result = await pablo.publish_draft("missing")
    assert result.ok is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_publish_draft_unsupported_platform_returns_error(monkeypatch):
    """Slice 1: only Bluesky is wired."""
    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: {
        "id": did,
        "metadata": {"platform": "linkedin", "status": "awaiting-user"},
        "document": "Hi.",
    })
    result = await pablo.publish_draft("d1")
    assert result.ok is False
    assert "platform" in result.error.lower()


@pytest.mark.asyncio
async def test_publish_draft_postiz_500_returns_error(monkeypatch):
    monkeypatch.setattr(pablo.settings, "postiz_api_key", "k")
    monkeypatch.setattr(pablo.settings, "postiz_bluesky_integration_id", "int-bsky")
    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: {
        "id": did,
        "metadata": {"platform": "bluesky", "lang": "en", "status": "awaiting-user"},
        "document": "Hi.",
    })

    err_resp = MagicMock()
    err_resp.status_code = 500
    err_resp.text = "boom"
    err_resp.raise_for_status.side_effect = pablo.httpx.HTTPStatusError(
        "500", request=MagicMock(), response=err_resp
    )
    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = False
    fake_client.post.return_value = err_resp
    monkeypatch.setattr(pablo.httpx, "AsyncClient", lambda **kw: fake_client)

    result = await pablo.publish_draft("d1")
    assert result.ok is False
    assert "postiz" in result.error.lower()
```

- [ ] **Step 10.3: Run — failures expected**

```bash
.venv/bin/python -m pytest tests/test_pablo.py -v
```

Expected: `ModuleNotFoundError: No module named 'observatory.agents.pablo'`.

- [ ] **Step 10.4: Implement `pablo.py`**

```python
"""Pablo — Publisher agent. No LLM. Relays approved drafts to Postiz.

Slice 1: only Bluesky is wired (we connect that account first). X and
LinkedIn integration IDs land in Slice 6 / Phase 7 after their respective
developer accounts clear.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from config.settings import settings
from observatory.storage import drafts_store

logger = logging.getLogger(__name__)


PLATFORM_INTEGRATION_ENV = {
    "bluesky": "postiz_bluesky_integration_id",
    # "x":        "postiz_x_integration_id",        # Slice 6
    # "linkedin": "postiz_linkedin_integration_id", # Phase 7
}


@dataclass
class PabloResult:
    ok: bool
    postiz_post_id: Optional[str] = None
    error: Optional[str] = None


async def publish_draft(draft_id: str) -> PabloResult:
    draft = drafts_store.get_draft(draft_id)
    if not draft:
        return PabloResult(ok=False, error=f"draft not found: {draft_id}")

    meta = draft["metadata"]
    platform = meta.get("platform", "")
    content = draft["document"]

    integration_attr = PLATFORM_INTEGRATION_ENV.get(platform)
    if integration_attr is None:
        return PabloResult(ok=False, error=f"unsupported platform in Slice 1: {platform!r}")

    integration_id = getattr(settings, integration_attr, "")
    if not integration_id or not settings.postiz_api_key:
        return PabloResult(ok=False, error="Postiz not configured (api key / integration id missing)")

    payload = {
        "type": "now",
        "shortLink": False,
        "posts": [
            {
                "integration": {"id": integration_id},
                "value": [{"content": content}],
            }
        ],
    }

    url = settings.postiz_base_url.rstrip("/") + "/api/public/v1/posts"
    headers = {
        "Authorization": f"Bearer {settings.postiz_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error("Pablo: Postiz call failed: %s", e)
        return PabloResult(ok=False, error=f"postiz request failed: {e}")
    except Exception as e:
        logger.error("Pablo: unexpected: %s", e)
        return PabloResult(ok=False, error=f"unexpected: {e}")

    posts = data.get("posts") or []
    postiz_post_id = posts[0].get("id") if posts else None
    if not postiz_post_id:
        return PabloResult(ok=False, error=f"postiz returned no post id: {data}")

    drafts_store.mark_published(
        draft_id=draft_id,
        postiz_post_id=postiz_post_id,
        scheduled_at="",  # Postiz returns its own scheduled_at; we don't echo it back in Slice 1
    )
    return PabloResult(ok=True, postiz_post_id=postiz_post_id)
```

- [ ] **Step 10.5: Run tests**

```bash
.venv/bin/python -m pytest tests/test_pablo.py -v
```

Expected: all 4 PASS.

- [ ] **Step 10.6: Commit**

```bash
git add config/settings.py observatory/agents/pablo.py tests/test_pablo.py
git commit -m "feat: Pablo publisher agent (Postiz relay, Bluesky-only in Slice 1)

publish_draft pulls the draft, posts to Postiz with the configured
integration ID, captures the postiz_post_id, and marks the draft
scheduled. X and LinkedIn integration IDs are stubs for Slice 6 / Phase
7. Fails clearly when Postiz isn't configured or returns a bad response.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Observatory API endpoints for draft lifecycle

**Files:**
- Modify: `observatory/app.py`
- Create: `tests/test_app_drafts.py`

- [ ] **Step 11.1: Write the failing tests**

Create `tests/test_app_drafts.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from observatory.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_drafts_list_filters_by_status(client, monkeypatch):
    from observatory.storage import drafts_store

    monkeypatch.setattr(
        drafts_store,
        "list_drafts_by_status",
        lambda status, limit=100: [
            {"id": "d1", "metadata": {"status": status, "platform": "x", "lang": "en"}, "document": "hi"},
        ],
    )

    r = client.get("/api/drafts?status=awaiting-user")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["id"] == "d1"


def test_post_drafts_approve_calls_pablo(client, monkeypatch):
    from observatory.app import publish_draft  # re-imported to ensure path is right
    from observatory.agents import pablo

    monkeypatch.setattr(
        pablo,
        "publish_draft",
        AsyncMock(return_value=pablo.PabloResult(ok=True, postiz_post_id="ptz-42")),
    )

    r = client.post("/api/drafts/draft-abc/approve")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["postiz_post_id"] == "ptz-42"


def test_post_drafts_approve_pablo_fails(client, monkeypatch):
    from observatory.agents import pablo

    monkeypatch.setattr(
        pablo,
        "publish_draft",
        AsyncMock(return_value=pablo.PabloResult(ok=False, error="boom")),
    )

    r = client.post("/api/drafts/draft-abc/approve")
    assert r.status_code == 502
    assert "boom" in r.json()["error"]


def test_post_drafts_skip_updates_status(client, monkeypatch):
    from observatory.storage import drafts_store

    calls = []
    monkeypatch.setattr(
        drafts_store,
        "mark_skipped",
        lambda draft_id, reason="user-skip": calls.append((draft_id, reason)),
    )

    r = client.post("/api/drafts/draft-abc/skip", params={"reason": "off-topic"})
    assert r.status_code == 200
    assert calls == [("draft-abc", "off-topic")]


def test_post_drafts_edit_replaces_content_then_approves(client, monkeypatch):
    """Edit replaces content, then triggers Pablo publish on the new content."""
    from observatory.storage import drafts_store
    from observatory.agents import pablo

    updates = []
    monkeypatch.setattr(
        drafts_store,
        "get_draft",
        lambda did: {"id": did, "metadata": {"platform": "bluesky", "lang": "en", "status": "awaiting-user"}, "document": "old"},
    )
    monkeypatch.setattr(
        drafts_store,
        "upsert_draft",
        lambda **kw: updates.append(kw) or "draft-abc",
    )
    monkeypatch.setattr(
        pablo,
        "publish_draft",
        AsyncMock(return_value=pablo.PabloResult(ok=True, postiz_post_id="ptz-2")),
    )

    r = client.post("/api/drafts/draft-abc/edit", json={"content": "new text"})
    assert r.status_code == 200
    assert r.json()["postiz_post_id"] == "ptz-2"
```

- [ ] **Step 11.2: Run — see failures**

```bash
.venv/bin/python -m pytest tests/test_app_drafts.py -v
```

Expected: 404s on the missing routes.

- [ ] **Step 11.3: Add endpoints to `app.py`**

Open `observatory/app.py`. Near the existing `/api/items/skip` endpoint, add:

```python
from observatory.agents import pablo as pablo_agent
from observatory.storage import drafts_store


@app.get("/api/drafts")
async def list_drafts(
    status: str = Query(default="awaiting-user", pattern="^(draft|awaiting-user|scheduled|published|skipped|rejected)$"),
    limit: int = Query(default=50),
):
    items = drafts_store.list_drafts_by_status(status, limit=limit)
    return {"count": len(items), "items": items}


@app.post("/api/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str):
    """Hand off to Pablo to publish via Postiz."""
    result = await pablo_agent.publish_draft(draft_id)
    if not result.ok:
        return JSONResponse(status_code=502, content={"error": result.error or "unknown"})
    return {"status": "ok", "draft_id": draft_id, "postiz_post_id": result.postiz_post_id}


@app.post("/api/drafts/{draft_id}/skip")
async def skip_draft(draft_id: str, reason: str = Query(default="user-skip")):
    drafts_store.mark_skipped(draft_id=draft_id, reason=reason)
    return {"status": "ok", "draft_id": draft_id}


@app.post("/api/drafts/{draft_id}/edit")
async def edit_draft(draft_id: str, payload: dict = Body(...)):
    """Replace the draft content, then publish."""
    new_content = payload.get("content", "")
    if not new_content:
        return JSONResponse(status_code=400, content={"error": "content required"})

    existing = drafts_store.get_draft(draft_id)
    if not existing:
        return JSONResponse(status_code=404, content={"error": "draft not found"})

    meta = existing["metadata"]
    drafts_store.upsert_draft(
        item_url=meta.get("item_url", ""),
        platform=meta.get("platform", ""),
        lang=meta.get("lang", ""),
        content=new_content,
        item_title=meta.get("item_title", ""),
        item_source=meta.get("item_source", ""),
    )
    result = await pablo_agent.publish_draft(draft_id)
    if not result.ok:
        return JSONResponse(status_code=502, content={"error": result.error or "unknown"})
    return {"status": "ok", "draft_id": draft_id, "postiz_post_id": result.postiz_post_id}
```

- [ ] **Step 11.4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_app_drafts.py -v
.venv/bin/python -m pytest -q
```

Expected: all 5 new tests PASS; full suite green.

- [ ] **Step 11.5: Commit**

```bash
git add observatory/app.py tests/test_app_drafts.py
git commit -m "feat: draft-lifecycle API endpoints

Adds GET /api/drafts (filter by status), POST /api/drafts/{id}/approve
(Pablo publish), POST /api/drafts/{id}/skip, POST /api/drafts/{id}/edit
(replace content + publish). n8n's Telegram callback workflow will call
these instead of touching Postiz directly.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Update n8n marketing-team workflows

**Files:**
- Modify: `deploy/n8n/marketing-team-es.json`
- Modify: `deploy/n8n/marketing-team-en.json`
- Modify: `deploy/n8n/marketing-team-callback.json`

The workflows shift from "fetch articles → draft inline → Telegram" to "fetch drafts that Edu approved → Telegram one message per draft".

- [ ] **Step 12.1: Modify `marketing-team-es.json`**

Replace the existing nodes with the simpler "fetch drafts" pattern. Open `deploy/n8n/marketing-team-es.json` and replace its `nodes` and `connections` so the flow is:

  Cron → Wake d3r-ser → GET /api/drafts?status=awaiting-user → filter for lang=es → Split → Telegram message per draft.

The "fetch + draft inline" step is gone because the digital-observatory pipeline now produces drafts on its 6-hour cron, and Edu has already gated them. The n8n workflow just surfaces what's ready.

Replace the file contents with:

```json
{
  "name": "Marketing Team — ES Stream",
  "nodes": [
    {
      "parameters": {
        "rule": {"interval": [{"field": "cronExpression", "expression": "0 9,21 * * *"}]}
      },
      "id": "mt-es-trigger-001",
      "name": "Twice daily (09:00 / 21:00 CST)",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [240, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://100.84.156.15:8400/api/wake-ollama",
        "options": {"timeout": 60000}
      },
      "id": "mt-es-wake-010",
      "name": "Wake d3r-ser (Ollama)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [360, 300]
    },
    {
      "parameters": {
        "method": "GET",
        "url": "http://100.84.156.15:8400/api/drafts",
        "sendQuery": true,
        "queryParameters": {
          "parameters": [
            {"name": "status", "value": "awaiting-user"},
            {"name": "limit", "value": "50"}
          ]
        },
        "options": {"timeout": 30000}
      },
      "id": "mt-es-fetch-002",
      "name": "Fetch awaiting-user drafts",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [480, 300]
    },
    {
      "parameters": {"fieldToSplitOut": "items", "options": {}},
      "id": "mt-es-split-003",
      "name": "Split drafts",
      "type": "n8n-nodes-base.splitOut",
      "typeVersion": 1,
      "position": [700, 300]
    },
    {
      "parameters": {
        "conditions": {
          "options": {"caseSensitive": true, "typeValidation": "loose"},
          "conditions": [
            {"leftValue": "={{ $json.metadata.lang }}", "rightValue": "es", "operator": {"type": "string", "operation": "equals"}}
          ],
          "combinator": "and"
        },
        "options": {}
      },
      "id": "mt-es-filter-004",
      "name": "Only lang=es",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [900, 300]
    },
    {
      "parameters": {
        "chatId": "={{ $env.TELEGRAM_CHAT_ID_ES }}",
        "text": "=📝 *Borrador ES — {{ $json.metadata.platform.toUpperCase() }}*\n\n*Fuente:* {{ $json.metadata.item_source }}\n*Veredicto:* {{ $json.metadata.edu_verdict }}\n*Notas Edu:* _{{ $json.metadata.edu_reasoning }}_\n\n```\n{{ $json.document }}\n```",
        "additionalFields": {
          "parse_mode": "Markdown",
          "reply_markup": "={\n  \"inline_keyboard\": [[\n    { \"text\": \"✅ Approve\", \"callback_data\": \"approve_{{ $json.id }}\" },\n    { \"text\": \"✏️ Edit\", \"callback_data\": \"edit_{{ $json.id }}\" },\n    { \"text\": \"⏭️ Skip\", \"callback_data\": \"skip_{{ $json.id }}\" }\n  ]]\n}"
        }
      },
      "id": "mt-es-tg-005",
      "name": "Send to ES Telegram inbox",
      "type": "n8n-nodes-base.telegram",
      "typeVersion": 1.2,
      "position": [1140, 300],
      "credentials": {
        "telegramApi": {"id": "PLACEHOLDER_TELEGRAM_CRED_ID", "name": "Telegram Marketing Bot"}
      }
    }
  ],
  "connections": {
    "Twice daily (09:00 / 21:00 CST)": {"main": [[{"node": "Wake d3r-ser (Ollama)", "type": "main", "index": 0}]]},
    "Wake d3r-ser (Ollama)": {"main": [[{"node": "Fetch awaiting-user drafts", "type": "main", "index": 0}]]},
    "Fetch awaiting-user drafts": {"main": [[{"node": "Split drafts", "type": "main", "index": 0}]]},
    "Split drafts": {"main": [[{"node": "Only lang=es", "type": "main", "index": 0}]]},
    "Only lang=es": {"main": [[{"node": "Send to ES Telegram inbox", "type": "main", "index": 0}]]}
  },
  "active": false,
  "settings": {"executionOrder": "v1", "saveDataErrorExecution": "all", "saveDataSuccessExecution": "all", "saveManualExecutions": true},
  "versionId": "2",
  "meta": {"description": "ES stream — surfaces drafts that Edu approved-for-review to a dedicated Telegram chat. Buttons call observatory's draft-lifecycle endpoints."}
}
```

- [ ] **Step 12.2: Modify `marketing-team-en.json` analogously**

Same shape with `lang=en` filter, cron `0 10,22 * * *`, env `TELEGRAM_CHAT_ID_EN`, IDs prefixed `mt-en-`.

Use the same JSON template; only change:
- workflow name to "Marketing Team — EN Stream"
- cron expression to `0 10,22 * * *`
- node IDs from `mt-es-*` to `mt-en-*`
- filter from `lang=es` to `lang=en`
- chat env var to `TELEGRAM_CHAT_ID_EN`
- "Borrador ES" → "Draft EN", "Fuente" → "Source", "Veredicto" → "Verdict", "Notas Edu" → "Edu notes"

- [ ] **Step 12.3: Modify `marketing-team-callback.json` to call observatory endpoints**

Open `deploy/n8n/marketing-team-callback.json`. Replace the "Schedule in Postiz" node with an observatory approve call, and "Mark item skipped" so it calls `/api/drafts/{id}/skip`:

Replace these two nodes' parameters:

For approve:
```json
{
  "method": "POST",
  "url": "=http://100.84.156.15:8400/api/drafts/{{ $('Parse callback').item.json.item_id }}/approve",
  "options": {"timeout": 30000}
}
```

For skip (id `mt-cb-skip-005`):
```json
{
  "method": "POST",
  "url": "=http://100.84.156.15:8400/api/drafts/{{ $('Parse callback').item.json.item_id }}/skip",
  "sendQuery": true,
  "queryParameters": {
    "parameters": [{"name": "reason", "value": "user-skip"}]
  },
  "options": {"timeout": 15000}
}
```

Rename `mt-cb-postiz-004` to `mt-cb-approve-004` and rename its display name to "Approve via observatory". Update the `"connections"` block's `"Schedule in Postiz"` key to `"Approve via observatory"` accordingly.

- [ ] **Step 12.4: Validate JSON**

```bash
cd /home/d3r/repos/digital-observatory
for f in deploy/n8n/*.json; do .venv/bin/python -c "import json; json.load(open('$f'))" && echo "OK: $f" || echo "BROKEN: $f"; done
```

Expected: all four files OK.

- [ ] **Step 12.5: Commit**

```bash
git add deploy/n8n/marketing-team-es.json deploy/n8n/marketing-team-en.json deploy/n8n/marketing-team-callback.json
git commit -m "feat: n8n marketing workflows route through draft-lifecycle endpoints

ES/EN workflows now fetch GET /api/drafts?status=awaiting-user and
surface one Telegram message per draft (Edu has already gated them).
Inline buttons call POST /api/drafts/{id}/approve|skip|edit so the
observatory owns the lifecycle and Pablo handles the Postiz hop.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Final test sweep + push

- [ ] **Step 13.1: Run all tests**

```bash
cd /home/d3r/repos/digital-observatory
.venv/bin/python -m pytest -q
```

Expected: every test PASS (estimated total ~65).

- [ ] **Step 13.2: Confirm git log shape**

```bash
git log --oneline feat/agent-department-spec ^main
```

Expected: 11-13 commits (one per task), each scoped and conventionally-prefixed.

- [ ] **Step 13.3: Push the branch**

```bash
git push -u origin feat/agent-department-spec
```

- [ ] **Step 13.4: Open the PR**

```bash
gh pr create --base main --head feat/agent-department-spec \
  --title "Slice 1: marketing agent department — publishing loop" \
  --body "$(cat <<'EOF'
## Summary
Implements Slice 1 of the marketing-agents spec (see docs/superpowers/specs/2026-05-22-marketing-agents-design.md): a working end-to-end publishing loop where Tess scores, Carla drafts, Edu reviews, the user approves in Telegram, and Pablo publishes to Bluesky via Postiz.

## What's new
- `observatory/agents/persona.py` + four persona markdown files (`agents/tess.md`, `agents/carla.md`, `agents/edu.md`)
- `observatory/storage/drafts_store.py` — new `drafts` ChromaDB collection with lifecycle helpers
- `observatory/agents/edu.py` — voice/facts/platform/dup gate
- `observatory/agents/pablo.py` — Postiz relay (Bluesky-only in Slice 1)
- Draft-lifecycle API: `GET /api/drafts`, `POST /api/drafts/{id}/{approve,skip,edit}`
- n8n workflows reshaped to surface Edu-approved drafts and call the new endpoints

## Out of scope (later slices)
- Ana (Analyst), Mara (CMO Reporter), ReAct/external API, real-time firehose, X + LinkedIn publishing, learning loop.

## Test plan
- [x] Unit tests for persona loader, drafts_store, drafter, edu, pablo, app draft endpoints
- [ ] Manual: deploy Postiz on nano-spud + connect Bluesky (Task 14)
- [ ] Manual end-to-end: trigger pipeline → an Edu-approved Bluesky draft appears in Telegram → tap ✅ → post lands on Bluesky within ~30s

EOF
)"
```

---

## Task 14: Deploy Postiz + connect Bluesky (the last open Phase 6 work)

This task is manual / out-of-band and SHOULD be done **after** the code PR merges (so the production observatory has the new endpoints ready).

- [ ] **Step 14.1: Generate Postiz secrets**

```bash
ssh nano-spud
cd /home/d3r/repos/digital-observatory/deploy/postiz
cp .env.example .env
JWT=$(openssl rand -base64 48)
DBP=$(openssl rand -hex 24)
sed -i "s|^POSTIZ_JWT_SECRET=.*|POSTIZ_JWT_SECRET=${JWT}|" .env
sed -i "s|^POSTIZ_DB_PASSWORD=.*|POSTIZ_DB_PASSWORD=${DBP}|" .env
grep -c '^POSTIZ_' .env
```

Expected: 2.

- [ ] **Step 14.2: Bring up Postiz**

```bash
docker compose up -d
docker compose logs --tail 50 postiz
```

Expected: "ready" line within ~60s.

- [ ] **Step 14.3: Verify health**

```bash
curl -fsS http://localhost:5000/api/health || curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:5000/
```

Expected: 200.

- [ ] **Step 14.4: Open Postiz UI via SSH tunnel**

From your Fedora terminal:

```bash
ssh -L 5000:127.0.0.1:5000 nano-spud
# Then browse to http://localhost:5000
```

Create the admin account in the browser.

- [ ] **Step 14.5: Connect Bluesky**

- In Bluesky web app → Settings → App Passwords → create a new app password named "Postiz".
- In Postiz UI → Integrations → Bluesky → paste your Bluesky handle + the app password.
- After it shows "connected", copy the integration's ID (visible in the URL of the integration's details page, or via `GET /api/public/v1/integrations`).

- [ ] **Step 14.6: Generate Postiz API key**

In Postiz UI → Settings → API Keys → New. Copy the key.

- [ ] **Step 14.7: Set observatory env vars**

```bash
ssh nano-spud
cd /home/d3r/repos/digital-observatory
grep -q "^POSTIZ_BASE_URL=" .env || echo "POSTIZ_BASE_URL=http://100.84.156.15:5000" >> .env
echo "POSTIZ_API_KEY=<paste here>" >> .env
echo "POSTIZ_BLUESKY_INTEGRATION_ID=<paste here>" >> .env
docker compose up -d --force-recreate observatory
docker compose exec observatory env | grep POSTIZ
```

Expected: all three POSTIZ_* lines present in the env dump.

- [ ] **Step 14.8: End-to-end smoke test**

Use any existing `awaiting-user` Bluesky draft (or trigger the pipeline to make one), then approve via the observatory API directly:

```bash
# from nano-spud (or Fedora):
curl -fsS "http://100.84.156.15:8400/api/drafts?status=awaiting-user&limit=5" | python3 -m json.tool

# Pick a draft id where metadata.platform == "bluesky" and approve it:
DRAFT_ID=<paste>
curl -fsS -X POST "http://100.84.156.15:8400/api/drafts/${DRAFT_ID}/approve" | python3 -m json.tool
```

Expected: `{"status":"ok","draft_id":"...","postiz_post_id":"..."}` and the post appears on your Bluesky timeline within ~30s.

- [ ] **Step 14.9: Tail observatory logs to confirm**

```bash
ssh nano-spud 'docker compose -f /home/d3r/repos/digital-observatory/docker-compose.yml logs --tail 30 observatory'
```

Expected: a `pablo` log line showing the Postiz call succeeded.

---

## Self-review

**Spec coverage:**

| Spec requirement | Where implemented |
|---|---|
| Persona files (agency-agents pattern) | Tasks 1, 2, 5, 7 |
| Tess persona-ified, uses agents/tess.md | Tasks 2, 3 |
| Carla persona-ified, uses agents/carla.md | Tasks 5, 6 |
| Edu new agent + voice/facts/platform/duplicate verdicts | Tasks 7, 8 |
| Pablo (no LLM, Postiz relay) | Task 10 |
| New `drafts` ChromaDB collection + helpers | Task 4 |
| Pipeline routes drafts through Edu before Telegram | Task 9 |
| Telegram callback workflow calls observatory's approve/skip/edit | Task 12 |
| Postiz deployment + Bluesky connection | Task 14 |
| Stage Postiz deployment last so the pipeline can be tested locally first | Task 14 deliberately final |
| Local Ollama for worker agents via WOL | Tasks 3, 6, 8 retain existing `_get_provider` + `check_ollama` pattern; `/api/wake-ollama` is already in place |
| No new sidecars | All work fits the existing observatory + chromadb + n8n + wol-service + postiz containers |

**Placeholder scan:** none in the plan. `PLACEHOLDER_TELEGRAM_CRED_ID` in the workflow JSON is a literal that n8n requires for credential mapping; it's set in the n8n UI, not in code, so it's not a plan placeholder.

**Type consistency:**
- `EduVerdict` enum values (`approved-for-review`, `revise`, `reject`) match the strings the `Edu` JSON output schema (in `agents/edu.md`) emits and what `drafts_store.update_edu_verdict` consumes.
- `DraftStatus` enum string values (`draft`, `awaiting-user`, etc.) match what `app.py::list_drafts` accepts as a regex and what `drafts_store.update_edu_verdict` writes.
- `PabloResult` (`ok`, `postiz_post_id`, `error`) is consistent across `pablo.publish_draft`, `app.py::approve_draft`, and the tests.

**Scope:** Slice 1 only. Ana / Mara / ReAct / real-time firehose / X+LinkedIn integrations / learning loop are deliberately deferred to Slice 2+ and explicitly listed in the PR body as out-of-scope.

**Ambiguity:**
- "Edu uses recent posts for duplicate check" — Slice 1 passes an empty list; Slice 2 will populate from ChromaDB. This is called out explicitly in Task 9's Step 9.4 implementation comment.
- "Pablo only supports Bluesky in Slice 1" — `PLATFORM_INTEGRATION_ENV` in `pablo.py` carries commented-out entries for X and LinkedIn so the path forward is clear.
