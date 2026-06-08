# Profiles/Brands Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "profile" layer over the existing pipeline so each article is routed to one content profile (tech-reviewer / tech-educator / linkedin-influencer / promo) that decides voice, output formats, and target account.

**Architecture:** A new `observatory/profiles/` package loads YAML profile/account/book configs into validated Pydantic models. Routing is a deterministic pure function over `source_weights` (no LLM change). The pipeline applies the chosen profile by passing `tone=profile.voice` and the profile's mapped platforms into the existing `draft_for_platforms()`, and persists `profile_id`+`account` on each draft. Pablo resolves the account alias at publish time. `promo` is fed by a manual `books.yaml` branch, not by RSS routing.

**Tech Stack:** Python 3.13, Pydantic, PyYAML, pytest + pytest-asyncio (`asyncio_mode=auto`), ChromaDB (drafts store), LangChain/Ollama (unchanged).

**Design deviation from spec (intentional):** Spec said "Tess gains profile_id + structured output." Routing is implemented as a deterministic pure function instead — cheaper, testable without Ollama, and leaves Tess's prompt untouched. The structured-output rewrite of Tess is deferred as an orthogonal robustness upgrade (not required for this feature).

---

## File Structure

**Create:**
- `observatory/profiles/__init__.py` — package marker
- `observatory/profiles/loader.py` — Pydantic models (`Profile`, `ProfileOutput`, `Account`, `Book`) + loaders + `pick_profile()` + `FORMAT_TO_PLATFORM`
- `config/profiles/brands/tech-reviewer.yaml`
- `config/profiles/brands/tech-educator.yaml`
- `config/profiles/brands/linkedin-influencer.yaml`
- `config/profiles/brands/promo.yaml`
- `config/profiles/accounts.yaml`
- `config/profiles/books.yaml`
- `tests/test_profiles_loader.py`
- `tests/test_profiles_routing.py`
- `tests/test_promo_drafts.py`

**Modify:**
- `observatory/storage/drafts_store.py` — `upsert_draft()` gains `profile_id`, `account`
- `observatory/intelligence/drafter.py` — `draft_for_platforms()` gains `profile_id`, `accounts`
- `observatory/pipeline.py` — `_process_article` routes via profile; `carla_draft_for_item` takes a `profile`; new `draft_promo_posts()`
- `observatory/agents/pablo.py` — resolve `draft.account` → Postiz integration
- `observatory/agents/persona.py` — remove dead `tools` field
- `tests/test_drafts_store.py` — assert new fields round-trip
- `tests/test_pipeline.py` — assert profile voice/platforms/account flow

---

## Task 1: Profile/Account/Book models + loader + config YAMLs

**Files:**
- Create: `observatory/profiles/__init__.py`
- Create: `observatory/profiles/loader.py`
- Create: `config/profiles/brands/tech-reviewer.yaml`, `tech-educator.yaml`, `linkedin-influencer.yaml`, `promo.yaml`
- Create: `config/profiles/accounts.yaml`, `config/profiles/books.yaml`
- Test: `tests/test_profiles_loader.py`

- [ ] **Step 1: Write the config YAMLs**

`config/profiles/brands/tech-reviewer.yaml`:
```yaml
id: tech-reviewer
display_name: "Tech Reviewer"
emoji: "🗞️"
source_weights:
  ai_news: 1.5
  ai_research: 1.0
  llm_tools: 1.0
  edtech: 0.3
voice: >
  Punchy, con opinión y en primera persona. "Esto salió hoy, esto importa, esto
  pienso." Directo, sin hype vacío.
outputs:
  - { format: thread, account: x }
  - { format: bluesky, account: bluesky }
  - { format: youtube_short, account: youtube }
min_score: 6
active: true
```

`config/profiles/brands/tech-educator.yaml`:
```yaml
id: tech-educator
display_name: "Tech Educator"
emoji: "📐"
source_weights:
  edtech: 1.5
  ai_research: 1.0
  llm_tools: 1.0
  pedagogy_notes: 1.5
  obsidian: 1.0
  ai_news: 0.4
voice: >
  Cálida, precisa y pedagógica. Explica un concepto a docentes con un ejemplo
  concreto. Sin jerga innecesaria.
outputs:
  - { format: linkedin, account: linkedin }
  - { format: blog, account: youtube }
  - { format: youtube_long, account: youtube }
min_score: 6
active: true
```
> Note: `blog`'s `account: youtube` here is a placeholder alias that resolves to an
> Obsidian-draft destination (no auto-publish); see accounts.yaml. The real blog
> platform decision is subsystem C/D.

`config/profiles/brands/linkedin-influencer.yaml`:
```yaml
id: linkedin-influencer
display_name: "LinkedIn Influencer"
emoji: "💼"
source_weights:
  opportunities: 1.5
  edtech: 0.6
  ai_news: 0.6
voice: >
  Narrativa en primera persona, tono de liderazgo de pensamiento. Una reflexión
  de carrera o una oportunidad con una lección personal.
outputs:
  - { format: linkedin, account: linkedin }
min_score: 6
active: true
```

`config/profiles/brands/promo.yaml`:
```yaml
id: promo
display_name: "Promo (libros/blog)"
emoji: "📚"
source_weights: {}          # not RSS-routed; fed by books.yaml via manual trigger
voice: >
  Promocional honesto y cálido. Presenta el libro, para quién es y qué problema
  resuelve, con un llamado a la acción claro y sin exagerar.
outputs:
  - { format: thread, account: x }
  - { format: bluesky, account: bluesky }
  - { format: linkedin, account: linkedin }
min_score: 0
active: true
```

`config/profiles/accounts.yaml`:
```yaml
# alias -> how it resolves at publish time.
x:        { platform: x,        postiz_integration_id: "" }
linkedin: { platform: linkedin, postiz_integration_id: "" }
bluesky:  { platform: bluesky,  postiz_integration_id: "${POSTIZ_BLUESKY}" }
youtube:  { platform: youtube,  postiz_integration_id: "" }
```

`config/profiles/books.yaml`:
```yaml
- id: ser-tutor
  title: "Ser Tutor"
  audience: "educadores"
  status: "en preparación"
  themes: ["tutoría", "acompañamiento docente"]
  cta_url: ""
- id: ia-para-docentes
  title: "IA para Docentes (nivel medio y superior)"
  audience: "docentes de media superior y superior"
  status: "idea"
  themes: ["IA en el aula", "alfabetización en IA"]
  cta_url: ""
```

- [ ] **Step 2: Write the failing test**

`tests/test_profiles_loader.py`:
```python
from pathlib import Path

import pytest

from observatory.profiles.loader import (
    Account,
    Book,
    Profile,
    load_accounts,
    load_books,
    load_profiles,
    resolve_account,
)


def test_load_profiles_returns_all_four():
    profiles = load_profiles()
    assert set(profiles) == {
        "tech-reviewer",
        "tech-educator",
        "linkedin-influencer",
        "promo",
    }
    reviewer = profiles["tech-reviewer"]
    assert isinstance(reviewer, Profile)
    assert reviewer.source_weights["ai_news"] == 1.5
    assert reviewer.min_score == 6
    assert reviewer.outputs[0].format == "thread"
    assert reviewer.outputs[0].account == "x"
    assert "primera persona" in reviewer.voice


def test_load_accounts_and_resolve():
    accounts = load_accounts()
    assert isinstance(accounts["bluesky"], Account)
    assert accounts["bluesky"].platform == "bluesky"
    resolved = resolve_account("bluesky")
    assert resolved.platform == "bluesky"


def test_resolve_unknown_account_returns_none():
    assert resolve_account("does-not-exist") is None


def test_load_books_seeded():
    books = load_books()
    ids = {b.id for b in books}
    assert "ser-tutor" in ids
    assert "ia-para-docentes" in ids
    assert all(isinstance(b, Book) for b in books)


def test_profile_referencing_unknown_account_fails(tmp_path, monkeypatch):
    """Loader must fail-fast if a profile output names an account alias that
    does not exist in accounts.yaml."""
    brands = tmp_path / "brands"
    brands.mkdir()
    (brands / "bad.yaml").write_text(
        "id: bad\ndisplay_name: Bad\nsource_weights: {}\n"
        "voice: x\noutputs:\n  - {format: thread, account: nope}\n"
        "min_score: 1\nactive: true\n",
        encoding="utf-8",
    )
    (tmp_path / "accounts.yaml").write_text("x: {platform: x, postiz_integration_id: ''}\n", encoding="utf-8")
    (tmp_path / "books.yaml").write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr("observatory.profiles.loader.PROFILES_DIR", tmp_path)
    with pytest.raises(ValueError, match="unknown account"):
        load_profiles()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_profiles_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'observatory.profiles'`

- [ ] **Step 4: Write the loader**

`observatory/profiles/__init__.py`:
```python
```
(empty file)

`observatory/profiles/loader.py`:
```python
"""Loader for content profiles, account aliases, and the book catalog.

A Profile is a content "mode" (not a brand, not a user): it declares which
source_groups it cares about (source_weights), the voice Carla adopts for it,
and which output formats go to which account alias. Routing (pick_profile) is a
deterministic pure function over source_weights — no LLM involved.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# observatory/profiles/loader.py -> parents[2] == repo root
PROFILES_DIR = Path(__file__).resolve().parents[2] / "config" / "profiles"

# Profile output formats -> drafter PLATFORM_PROMPTS keys. Formats not present
# here are not yet supported by the drafter (subsystem C) and are skipped.
FORMAT_TO_PLATFORM = {
    "thread": "x",
    "bluesky": "bluesky",
    "linkedin": "linkedin",
    "blog": "blog",
}


class ProfileOutput(BaseModel):
    format: str
    account: str


class Profile(BaseModel):
    id: str
    display_name: str = ""
    emoji: str = ""
    source_weights: dict[str, float] = Field(default_factory=dict)
    voice: str = ""
    outputs: list[ProfileOutput] = Field(default_factory=list)
    min_score: int = 6
    active: bool = True


class Account(BaseModel):
    platform: str
    postiz_integration_id: str = ""
    destination: str = ""


class Book(BaseModel):
    id: str
    title: str
    audience: str = ""
    status: str = ""
    themes: list[str] = Field(default_factory=list)
    cta_url: str = ""


@lru_cache(maxsize=1)
def load_accounts() -> dict[str, Account]:
    path = PROFILES_DIR / "accounts.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {alias: Account(**cfg) for alias, cfg in raw.items()}


@lru_cache(maxsize=1)
def load_profiles() -> dict[str, Profile]:
    accounts = load_accounts()
    brands_dir = PROFILES_DIR / "brands"
    profiles: dict[str, Profile] = {}
    for path in sorted(brands_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        profile = Profile(**data)
        for out in profile.outputs:
            if out.account not in accounts:
                raise ValueError(
                    f"profile '{profile.id}' references unknown account "
                    f"'{out.account}' (not in accounts.yaml)"
                )
        profiles[profile.id] = profile
    return profiles


@lru_cache(maxsize=1)
def load_books() -> list[Book]:
    path = PROFILES_DIR / "books.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [Book(**b) for b in raw]


def resolve_account(alias: str) -> Optional[Account]:
    return load_accounts().get(alias)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_profiles_loader.py -v`
Expected: PASS (all 5 tests). The fail-fast test passes because `PROFILES_DIR` is monkeypatched; note `load_profiles`/`load_accounts` are `lru_cache`d — the test process starts fresh so the cache is cold, but if you add more tests that both patch and don't patch, call `load_profiles.cache_clear()` / `load_accounts.cache_clear()` in those tests.

- [ ] **Step 6: Commit**

```bash
git add observatory/profiles/ config/profiles/brands/ config/profiles/accounts.yaml config/profiles/books.yaml tests/test_profiles_loader.py
git commit -m "feat(profiles): Profile/Account/Book loader + 4 profile configs"
```

---

## Task 2: Deterministic routing — `pick_profile()`

**Files:**
- Modify: `observatory/profiles/loader.py` (add `pick_profile`)
- Test: `tests/test_profiles_routing.py`

- [ ] **Step 1: Write the failing test**

`tests/test_profiles_routing.py`:
```python
from observatory.profiles.loader import load_profiles, pick_profile


def test_ai_news_routes_to_tech_reviewer():
    profiles = load_profiles()
    chosen = pick_profile("ai_news", profiles)
    assert chosen is not None
    assert chosen.id == "tech-reviewer"


def test_edtech_routes_to_tech_educator():
    profiles = load_profiles()
    chosen = pick_profile("edtech", profiles)
    assert chosen is not None
    assert chosen.id == "tech-educator"


def test_opportunities_routes_to_influencer():
    profiles = load_profiles()
    chosen = pick_profile("opportunities", profiles)
    assert chosen is not None
    assert chosen.id == "linkedin-influencer"


def test_unknown_source_group_has_no_owner():
    profiles = load_profiles()
    assert pick_profile("totally_unknown_group", profiles) is None


def test_inactive_profile_never_selected():
    profiles = load_profiles()
    profiles["tech-reviewer"].active = False
    chosen = pick_profile("ai_news", profiles)
    # With reviewer inactive, ai_news falls to next-highest weight (educator 0.4).
    assert chosen is not None
    assert chosen.id != "tech-reviewer"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_profiles_routing.py -v`
Expected: FAIL with `ImportError: cannot import name 'pick_profile'`

- [ ] **Step 3: Implement `pick_profile`**

Append to `observatory/profiles/loader.py`:
```python
def pick_profile(
    source_group: str, profiles: dict[str, Profile]
) -> Optional[Profile]:
    """Return the active profile with the highest source_weight for this
    source_group, or None if no active profile weights it above zero.

    Deterministic: ties are broken by profile id (sorted) so the same input
    always yields the same owner.
    """
    candidates = [
        (p.source_weights.get(source_group, 0.0), p.id, p)
        for p in profiles.values()
        if p.active
    ]
    candidates = [c for c in candidates if c[0] > 0.0]
    if not candidates:
        return None
    # Highest weight wins; tie-break by id ascending.
    candidates.sort(key=lambda c: (-c[0], c[1]))
    return candidates[0][2]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_profiles_routing.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add observatory/profiles/loader.py tests/test_profiles_routing.py
git commit -m "feat(profiles): deterministic source_group -> profile routing"
```

---

## Task 3: Persist `profile_id` + `account` on drafts

**Files:**
- Modify: `observatory/storage/drafts_store.py:86-114` (`upsert_draft`)
- Test: `tests/test_drafts_store.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_drafts_store.py` (import `upsert_draft`, `get_draft` if not already imported at top):
```python
def test_upsert_draft_persists_profile_and_account(monkeypatch):
    captured = {}

    class FakeColl:
        def upsert(self, ids, documents, metadatas):
            captured["id"] = ids[0]
            captured["meta"] = metadatas[0]

    monkeypatch.setattr(
        "observatory.storage.drafts_store._get_collection", lambda: FakeColl()
    )
    from observatory.storage.drafts_store import upsert_draft

    upsert_draft(
        item_url="https://example.com/a",
        platform="x",
        lang="es",
        content="hola",
        item_title="T",
        item_source="S",
        profile_id="tech-reviewer",
        account="x",
    )
    assert captured["meta"]["profile_id"] == "tech-reviewer"
    assert captured["meta"]["account"] == "x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_drafts_store.py::test_upsert_draft_persists_profile_and_account -v`
Expected: FAIL with `TypeError: upsert_draft() got an unexpected keyword argument 'profile_id'`

- [ ] **Step 3: Modify `upsert_draft`**

In `observatory/storage/drafts_store.py`, change the signature and metadata dict:
```python
def upsert_draft(
    item_url: str,
    platform: str,
    lang: str,
    content: str,
    item_title: str = "",
    item_source: str = "",
    profile_id: str = "",
    account: str = "",
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
        "profile_id": profile_id,
        "account": account,
        "created_at": now,
        "updated_at": now,
    }
    coll.upsert(ids=[draft_id], documents=[content], metadatas=[metadata])
    return draft_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_drafts_store.py::test_upsert_draft_persists_profile_and_account -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/storage/drafts_store.py tests/test_drafts_store.py
git commit -m "feat(drafts): persist profile_id and account on drafts"
```

---

## Task 4: Thread `profile_id`/`accounts` through the drafter

**Files:**
- Modify: `observatory/intelligence/drafter.py:136-201` (`draft_for_platforms`)
- Test: `tests/test_drafter.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_drafter.py`:
```python
import asyncio

from observatory.intelligence import drafter


def test_draft_for_platforms_passes_profile_and_account(monkeypatch):
    captured = []

    def fake_upsert(**kwargs):
        captured.append(kwargs)
        return "draft-" + kwargs["platform"]

    class FakeResp:
        content = "texto generado"

    class FakeProvider:
        async def ainvoke(self, messages):
            return FakeResp()

    monkeypatch.setattr(drafter, "upsert_draft", fake_upsert)
    monkeypatch.setattr(drafter, "_get_provider", lambda: _coro(FakeProvider()))

    result = asyncio.get_event_loop().run_until_complete(
        drafter.draft_for_platforms(
            hook="h", summary="s", angles=[], platforms=["x"], lang="es",
            item_url="https://ex.com/a", item_title="T", item_source="S",
            tone="voz reviewer",
            profile_id="tech-reviewer",
            accounts={"x": "x"},
        )
    )

    assert result["x"] == "texto generado"
    assert captured[0]["profile_id"] == "tech-reviewer"
    assert captured[0]["account"] == "x"


async def _coro(value):
    return value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_drafter.py::test_draft_for_platforms_passes_profile_and_account -v`
Expected: FAIL with `TypeError: draft_for_platforms() got an unexpected keyword argument 'profile_id'`

- [ ] **Step 3: Modify `draft_for_platforms`**

In `observatory/intelligence/drafter.py`, update the signature (add two params at the end) and the `upsert_draft` call:

Signature — add after `tone: str = "",`:
```python
    profile_id: str = "",
    accounts: Optional[dict] = None,
) -> dict:
```

Inside the persistence loop, replace the `upsert_draft(...)` call with:
```python
        draft_id = upsert_draft(
            item_url=item_url,
            platform=platform,
            lang=lang,
            content=body,
            item_title=item_title,
            item_source=item_source,
            profile_id=profile_id,
            account=(accounts or {}).get(platform, ""),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_drafter.py::test_draft_for_platforms_passes_profile_and_account -v`
Expected: PASS

- [ ] **Step 5: Run the full drafter suite to confirm no regression**

Run: `python -m pytest tests/test_drafter.py tests/test_blog_format.py -v`
Expected: PASS (existing tests still green — new params default to `""`/`None`)

- [ ] **Step 6: Commit**

```bash
git add observatory/intelligence/drafter.py tests/test_drafter.py
git commit -m "feat(drafter): thread profile_id and per-platform account through"
```

---

## Task 5: Apply the profile in the pipeline

**Files:**
- Modify: `observatory/pipeline.py:173-316` (`_process_article`, `carla_draft_for_item`)
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pipeline.py`:
```python
import asyncio
import types

from observatory import pipeline
from observatory.profiles.loader import Profile, ProfileOutput
from observatory.storage.models import CollectedItem


def test_carla_uses_profile_voice_and_mapped_platforms(monkeypatch):
    calls = {}

    async def fake_draft_for_platforms(**kwargs):
        calls.update(kwargs)
        return {
            "x": "texto",
            "bluesky": "texto",
            "draft_ids": {"x": "id-x", "bluesky": "id-b"},
        }

    monkeypatch.setattr(
        "observatory.intelligence.drafter.draft_for_platforms",
        fake_draft_for_platforms,
    )
    monkeypatch.setattr(pipeline.event_log, "append_event", lambda *a, **k: None)

    profile = Profile(
        id="tech-reviewer",
        voice="voz punchy",
        outputs=[
            ProfileOutput(format="thread", account="x"),
            ProfileOutput(format="bluesky", account="bluesky"),
            ProfileOutput(format="youtube_short", account="youtube"),
        ],
        min_score=6,
    )
    item = CollectedItem(
        url="https://ex.com/a", title="T", source="S", source_type="rss",
        raw_text="body", kind="article", source_group="ai_news",
    )
    evaluation = types.SimpleNamespace(
        lang_targets=["es"], one_line_hook="hook", summary="sum",
        post_angles=[],
    )

    drafts = asyncio.get_event_loop().run_until_complete(
        pipeline.carla_draft_for_item(item, evaluation, profile)
    )

    assert calls["tone"] == "voz punchy"
    # youtube_short is unsupported -> dropped; only x + bluesky remain.
    assert set(calls["platforms"]) == {"x", "bluesky"}
    assert calls["profile_id"] == "tech-reviewer"
    assert calls["accounts"]["x"] == "x"
    assert calls["accounts"]["bluesky"] == "bluesky"
    assert len(drafts) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py::test_carla_uses_profile_voice_and_mapped_platforms -v`
Expected: FAIL with `TypeError: carla_draft_for_item() takes ... arguments` (profile arg not accepted yet)

- [ ] **Step 3: Modify `carla_draft_for_item`**

Replace `carla_draft_for_item` in `observatory/pipeline.py` with:
```python
async def carla_draft_for_item(
    item: CollectedItem, evaluation, profile, run_id: str | None = None
) -> list[dict]:
    """Generate per-platform drafts for `item` using the chosen profile's voice,
    mapped output formats, and per-platform account aliases. Persists to
    drafts_store and returns [{id, platform, lang, content}, ...]."""
    from observatory.intelligence.drafter import draft_for_platforms
    from observatory.profiles.loader import FORMAT_TO_PLATFORM

    # Map profile outputs (format -> platform) and remember each platform's account.
    platforms: list[str] = []
    accounts: dict[str, str] = {}
    for out in profile.outputs:
        platform = FORMAT_TO_PLATFORM.get(out.format)
        if platform is None:
            logger.warning(
                "Profile %s output format '%s' not yet supported by drafter; skipping.",
                profile.id, out.format,
            )
            continue
        if platform not in platforms:
            platforms.append(platform)
            accounts[platform] = out.account

    out_list: list[dict] = []
    if not platforms:
        return out_list

    for lang in evaluation.lang_targets:
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
            tone=profile.voice,
            profile_id=profile.id,
            accounts=accounts,
        )
        for platform in platforms:
            content = result.get(platform)
            draft_id = result.get("draft_ids", {}).get(platform)
            if content and draft_id:
                out_list.append(
                    {"id": draft_id, "platform": platform, "lang": lang, "content": content}
                )
                event_log.append_event(
                    "carla", "carla.drafted",
                    item_url=item.url, draft_id=draft_id,
                    platform=platform, lang=lang, run_id=run_id,
                    payload={"title": item.title, "profile_id": profile.id},
                )
    return out_list
```

- [ ] **Step 4: Update `_process_article` to route + gate by profile**

In `observatory/pipeline.py`, in `_process_article`, replace the relevance gate block (currently `if evaluation.teacher_relevance >= settings.ai_article_min_relevance:` ... through the `carla_draft_for_item(item, evaluation, run_id=run_id)` call) so it routes first:

```python
    from observatory.profiles.loader import load_profiles, pick_profile

    profile = pick_profile(item.source_group, load_profiles())
    if profile is None:
        event_log.append_event(
            "tess", "tess.skipped",
            item_url=item.url, run_id=run_id,
            payload={"title": item.title, "skip_reason": "no-profile-owner"},
        )
        return

    if evaluation.teacher_relevance >= profile.min_score:
        # Vault drafts for the human-readable inbox (existing behavior).
        written = await write_article_drafts(item, evaluation)
        result.articles_drafted += len(written)

        # Carla → Edu per draft, using the routed profile.
        drafts = await carla_draft_for_item(item, evaluation, profile, run_id=run_id)
        for draft in drafts:
```
(the per-draft Edu loop below stays exactly as-is)

And update the `else` branch's skip payload to use the profile threshold:
```python
    else:
        event_log.append_event(
            "tess", "tess.skipped",
            item_url=item.url, run_id=run_id,
            payload={
                "title": item.title,
                "skip_reason": "below-min-relevance",
                "teacher_relevance": evaluation.teacher_relevance,
                "profile_id": profile.id,
                "min_score": profile.min_score,
            },
        )
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py::test_carla_uses_profile_voice_and_mapped_platforms -v`
Expected: PASS

- [ ] **Step 6: Run the full pipeline suite to confirm no regression**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: PASS. If a pre-existing test calls `carla_draft_for_item(item, evaluation, run_id=...)` without a `profile`, update that call to pass a `Profile(...)` (it changed signature by design) — show the diff in your commit.

- [ ] **Step 7: Commit**

```bash
git add observatory/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): route articles to a profile; apply voice/formats/account"
```

---

## Task 6: `promo` branch — drafts from `books.yaml`

**Files:**
- Modify: `observatory/pipeline.py` (add `draft_promo_posts`)
- Test: `tests/test_promo_drafts.py`

- [ ] **Step 1: Write the failing test**

`tests/test_promo_drafts.py`:
```python
import asyncio

from observatory import pipeline


def test_draft_promo_posts_uses_promo_voice_and_books(monkeypatch):
    calls = []

    async def fake_draft_for_platforms(**kwargs):
        calls.append(kwargs)
        return {"x": "promo!", "draft_ids": {"x": "id-x"}}

    monkeypatch.setattr(
        "observatory.intelligence.drafter.draft_for_platforms",
        fake_draft_for_platforms,
    )
    monkeypatch.setattr(pipeline.event_log, "append_event", lambda *a, **k: None)

    drafts = asyncio.get_event_loop().run_until_complete(
        pipeline.draft_promo_posts(book_id="ser-tutor", lang="es")
    )

    assert calls, "expected at least one draft_for_platforms call"
    assert calls[0]["profile_id"] == "promo"
    assert "Ser Tutor" in calls[0]["hook"]
    assert calls[0]["tone"]  # promo voice non-empty
    assert len(drafts) >= 1


def test_draft_promo_posts_unknown_book_returns_empty(monkeypatch):
    monkeypatch.setattr(pipeline.event_log, "append_event", lambda *a, **k: None)
    drafts = asyncio.get_event_loop().run_until_complete(
        pipeline.draft_promo_posts(book_id="does-not-exist", lang="es")
    )
    assert drafts == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_promo_drafts.py -v`
Expected: FAIL with `AttributeError: module 'observatory.pipeline' has no attribute 'draft_promo_posts'`

- [ ] **Step 3: Implement `draft_promo_posts`**

Add to `observatory/pipeline.py`:
```python
async def draft_promo_posts(
    book_id: str, lang: str = "es", run_id: str | None = None
) -> list[dict]:
    """Manual-trigger branch: generate promotional drafts for one book using the
    'promo' profile's voice and outputs. Not fed by RSS routing."""
    from observatory.intelligence.drafter import draft_for_platforms
    from observatory.profiles.loader import (
        FORMAT_TO_PLATFORM,
        load_books,
        load_profiles,
    )

    book = next((b for b in load_books() if b.id == book_id), None)
    if book is None:
        logger.warning("draft_promo_posts: unknown book_id '%s'", book_id)
        return []

    profile = load_profiles().get("promo")
    if profile is None or not profile.active:
        logger.warning("draft_promo_posts: 'promo' profile missing or inactive")
        return []

    platforms: list[str] = []
    accounts: dict[str, str] = {}
    for out in profile.outputs:
        platform = FORMAT_TO_PLATFORM.get(out.format)
        if platform and platform not in platforms:
            platforms.append(platform)
            accounts[platform] = out.account

    hook = f"{book.title} — para {book.audience}"
    summary = f"Libro: {book.title}. Audiencia: {book.audience}. Temas: {', '.join(book.themes)}."
    angles = [{"angle": t, "for": book.audience} for t in book.themes]
    pseudo_url = f"promo://book/{book.id}"

    result = await draft_for_platforms(
        hook=hook,
        summary=summary,
        angles=angles,
        platforms=platforms,
        lang=lang,
        item_url=pseudo_url,
        item_title=book.title,
        item_source="promo:books",
        include_course_cta=False,
        tone=profile.voice,
        profile_id=profile.id,
        accounts=accounts,
    )

    out_list: list[dict] = []
    for platform in platforms:
        content = result.get(platform)
        draft_id = result.get("draft_ids", {}).get(platform)
        if content and draft_id:
            out_list.append(
                {"id": draft_id, "platform": platform, "lang": lang, "content": content}
            )
            event_log.append_event(
                "carla", "carla.drafted",
                item_url=pseudo_url, draft_id=draft_id,
                platform=platform, lang=lang, run_id=run_id,
                payload={"title": book.title, "profile_id": profile.id},
            )
    return out_list
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_promo_drafts.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add observatory/pipeline.py tests/test_promo_drafts.py
git commit -m "feat(promo): generate promotional drafts from books.yaml"
```

---

## Task 7: Pablo resolves the account alias

**Files:**
- Modify: `observatory/agents/pablo.py` (add `resolve_integration_id`; use it in `publish_draft`, lines ~49-59)
- Test: `tests/test_pablo.py`

Pablo today (verified): `publish_draft` reads `meta["platform"]`, looks up
`PLATFORM_INTEGRATION_ENV[platform]` → a `settings` attribute
(`postiz_bluesky_integration_id`). We add alias resolution as the primary path and
keep the existing settings lookup as a fallback so the deployed Bluesky flow on the
Pi keeps working unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pablo.py`:
```python
from observatory.agents import pablo as pablo_mod
from observatory.profiles.loader import load_accounts


def test_resolve_integration_id_env_interpolation(monkeypatch):
    load_accounts.cache_clear()
    monkeypatch.setenv("POSTIZ_BLUESKY", "bsky-integration-123")
    # accounts.yaml: bluesky -> "${POSTIZ_BLUESKY}"
    assert pablo_mod.resolve_integration_id("bluesky") == "bsky-integration-123"


def test_resolve_integration_id_uncabled_and_unknown():
    # x is declared but uncabled (empty id); 'missing' is not an alias at all.
    assert pablo_mod.resolve_integration_id("x") == ""
    assert pablo_mod.resolve_integration_id("missing") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pablo.py::test_resolve_integration_id_env_interpolation -v`
Expected: FAIL with `AttributeError: module 'observatory.agents.pablo' has no attribute 'resolve_integration_id'`

- [ ] **Step 3: Add `resolve_integration_id`**

Add near the top of `observatory/agents/pablo.py` (after the imports):
```python
def resolve_integration_id(account_alias: str) -> str:
    """Map a draft's account alias to a Postiz integration id. Returns "" when
    the alias is unknown or not yet cabled. Supports ${ENV} interpolation."""
    import os

    from observatory.profiles.loader import resolve_account

    account = resolve_account(account_alias)
    if account is None:
        return ""
    integration = (account.postiz_integration_id or "").strip()
    if integration.startswith("${") and integration.endswith("}"):
        return os.environ.get(integration[2:-1], "")
    return integration
```

- [ ] **Step 4: Use it in `publish_draft` (preserve Bluesky fallback)**

In `observatory/agents/pablo.py`, replace the integration-id selection block
(currently lines ~50-59, from `platform = meta.get("platform", "")` through the
`if not integration_id or not settings.postiz_api_key:` guard) with:
```python
    platform = meta.get("platform", "")
    account = meta.get("account", "")
    content = draft["document"]

    # Primary: resolve via the draft's account alias. Fallback: legacy per-platform
    # settings lookup so the already-deployed Bluesky flow keeps working.
    integration_id = resolve_integration_id(account) if account else ""
    if not integration_id:
        integration_attr = PLATFORM_INTEGRATION_ENV.get(platform)
        if integration_attr is None and not account:
            return _fail(draft_id, platform, f"unsupported platform: {platform!r}")
        integration_id = getattr(settings, integration_attr, "") if integration_attr else ""

    if not integration_id or not settings.postiz_api_key:
        return _fail(
            draft_id, platform,
            f"account {account or platform!r} not cabled (integration id / api key missing)",
        )
```
> Note: the existing `content = draft["document"]` line a few lines above is now
> moved into this block — delete the old standalone `content = draft["document"]`
> assignment so it isn't duplicated.

- [ ] **Step 5: Run the test + full Pablo suite**

Run: `python -m pytest tests/test_pablo.py -v`
Expected: PASS. Existing Bluesky tests still pass because a draft without an
`account` falls back to `PLATFORM_INTEGRATION_ENV["bluesky"]` →
`settings.postiz_bluesky_integration_id`, exactly as before.

- [ ] **Step 6: Commit**

```bash
git add observatory/agents/pablo.py tests/test_pablo.py
git commit -m "feat(pablo): resolve account alias -> Postiz integration; keep bluesky fallback"
```

---

## Task 8: Remove the dead `tools` field from personas

**Files:**
- Modify: `observatory/agents/persona.py:37,61`
- Test: `tests/test_persona.py`

- [ ] **Step 1: Confirm nothing reads `Persona.tools`**

Run: `grep -rn "\.tools" observatory/ | grep -iv "import"`
Expected: no hits referencing `persona.tools` / `Persona.tools` usage (only the definition/assignment). If a hit exists, stop and handle that consumer first.

- [ ] **Step 2: Remove the field**

In `observatory/agents/persona.py`, delete line `tools: Optional[list[str]] = None` from the dataclass and `tools=fm.get("tools"),` from the constructor call.

- [ ] **Step 3: Run the persona suite**

Run: `python -m pytest tests/test_persona.py -v`
Expected: PASS (existing tests don't reference `tools`)

- [ ] **Step 4: Commit**

```bash
git add observatory/agents/persona.py
git commit -m "chore(persona): drop unused tools field (dead config)"
```

---

## Task 9: Full-suite green + final commit

- [ ] **Step 1: Run the entire test suite**

Run: `python -m pytest -q`
Expected: all tests pass. Fix any cross-test `lru_cache` bleed by adding `load_profiles.cache_clear(); load_accounts.cache_clear(); load_books.cache_clear()` at the start of tests that monkeypatch `PROFILES_DIR`.

- [ ] **Step 2: Sanity-check routing end to end (manual)**

Run:
```bash
python -c "from observatory.profiles.loader import load_profiles, pick_profile; ps=load_profiles(); print({g: pick_profile(g, ps).id if pick_profile(g, ps) else None for g in ['ai_news','edtech','opportunities','llm_tools','pedagogy_notes']})"
```
Expected: `{'ai_news': 'tech-reviewer', 'edtech': 'tech-educator', 'opportunities': 'linkedin-influencer', 'llm_tools': 'tech-reviewer', 'pedagogy_notes': 'tech-educator'}`
(`llm_tools` ties reviewer vs educator at 1.0 → tie-break by id: `tech-educator` < `tech-reviewer`, so expect `tech-educator`. Adjust the expected string to match, or bump a weight if you want reviewer to own `llm_tools`.)

- [ ] **Step 3: Final verification note**

Confirm the working tree is clean (`git status`) and all 8 feature commits are present (`git log --oneline -10`).

---

## Spec Coverage Check

- Profile model (lens/voice/formats/account) → Task 1 ✓
- accounts.yaml single source of truth → Task 1 ✓
- books.yaml seeded (ser-tutor, ia-para-docentes) → Task 1 ✓
- Loader with fail-fast on bad alias → Task 1 ✓
- Router 1-profile-per-item (deterministic) → Task 2 ✓
- Draft persists profile_id + account → Task 3 ✓
- Carla gets per-profile voice (tone) + mapped platforms → Tasks 4–5 ✓
- min_score gate per profile → Task 5 ✓
- Unsupported formats skipped with warning → Task 5 ✓
- promo branch from books.yaml, manual → Task 6 ✓
- Pablo resolves account, holds uncabled → Task 7 ✓
- Dead `tools` field removed → Task 8 ✓
- Out of scope (B/C/D/E, fan-out, real account cabling) → not in this plan ✓
```
