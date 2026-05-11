# Scrapper → Observatory Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate all working pipeline code from educational-ops-scrapper into digital-observatory's modular architecture, filling the empty `intelligence/` and `outputs/` modules.

**Architecture:** Config-driven collectors (RSS, WordPress REST API, Playwright) feed into a dual-dedup pipeline (URL hash + semantic similarity), evaluated by an LLM provider chain (Ollama → OpenAI → Gemini), stored in ChromaDB with full metadata, and dispatched to notification outputs (Telegram, email, Google Sheets). Pipeline is triggerable via CLI or FastAPI endpoint.

**Tech Stack:** Python 3.11+, FastAPI, ChromaDB, LangChain (langchain-ollama, langchain-openai, langchain-google-genai), httpx, Pydantic, Jinja2, gspread, Playwright (optional)

**Spec:** `docs/superpowers/specs/2026-05-11-scrapper-migration-design.md`

---

## Task 1: Dependencies and Configuration Foundation

**Files:**
- Modify: `pyproject.toml`
- Modify: `config/settings.py`
- Modify: `.env.example`
- Create: `config/sources/wordpress_sites.yaml`
- Create: `config/profiles/user_profile.txt`

- [ ] **Step 1: Update pyproject.toml with new dependencies**

```toml
[project]
name = "digital-observatory"
version = "0.2.0"
description = "Intelligent topic monitoring and knowledge management system"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "chromadb>=0.5.0",
    "sentence-transformers>=2.6.0",
    "feedparser>=6.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "pyyaml>=6.0",
    "jinja2>=3.1.0",
    "python-dotenv>=1.0.0",
    "prometheus-client>=0.20.0",
    "langchain-core>=0.3.0",
    "langchain-openai>=0.1.1",
    "langchain-google-genai>=1.0.2",
    "langchain-ollama>=0.3.0",
    "openai>=1.14.2",
    "google-generativeai>=0.4.1",
]

[project.optional-dependencies]
scraping = [
    "playwright>=1.42.0",
    "beautifulsoup4>=4.12.0",
]
notifications = [
    "requests>=2.31.0",
    "gspread>=6.0.2",
    "oauth2client>=4.1.3",
]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.3.0",
]

[project.scripts]
observatory = "observatory.cli:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Update config/settings.py with new fields**

Replace the entire file:

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # LLM providers (Ollama first, then cloud fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # Obsidian
    obsidian_vault_path: Path = Path("/mnt/d/DM01")

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""
    email_receiver: str = ""

    # Google Sheets
    google_sheet_id: str = ""
    google_credentials_path: Path = Path("credentials.json")

    # Paths
    user_profile_path: Path = Path("config/profiles/user_profile.txt")
    wordpress_config_path: Path = Path("config/sources/wordpress_sites.yaml")
    state_db_path: Path = Path("data/state.db")

    # App
    log_level: str = "INFO"
    app_port: int = 8400

    # Processing
    dedup_distance_threshold: float = 0.15
    embedding_model: str = "all-MiniLM-L6-v2"
    high_affinity_threshold: int = 8
    weekly_email_interval_days: int = 7

    # WordPress scraping
    wp_default_keywords: list[str] = [
        "artificial intelligence",
        "data science",
        "education technology",
        "scholarship PhD",
        "fellowship AI",
        "remote AI jobs",
    ]
    wp_max_results_per_site: int = 10
    wp_request_delay_min: float = 1.0
    wp_request_delay_max: float = 2.5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 3: Create config/sources/wordpress_sites.yaml**

```yaml
sites:
  - name: GlobalSouthOpportunities
    base_url: https://www.globalsouthopportunities.com
    enabled: true

  - name: OpportunityDesk
    base_url: https://opportunitydesk.org
    enabled: true

  - name: OpportunitiesForAfricans
    base_url: https://www.opportunitiesforafricans.com
    enabled: true

  - name: Scholars4Dev
    base_url: https://www.scholars4dev.com
    enabled: true

  - name: AfterSchoolAfrica
    base_url: https://www.afterschoolafrica.com
    enabled: true

  - name: fundsforNGOs
    base_url: https://www2.fundsforngos.org
    enabled: true
```

- [ ] **Step 4: Copy user_profile.txt to config/profiles/**

```bash
cp /mnt/c/Users/HG_Co/OneDrive/Documents/Github/educational-ops-scrapper/user_profile.txt \
   config/profiles/user_profile.txt
```

- [ ] **Step 5: Update .env.example with all new variables**

```bash
# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# LLM Providers — Ollama is tried first, then cloud APIs as fallback
OLLAMA_BASE_URL=http://100.x.x.x:11434
OLLAMA_MODEL=llama3.1:8b

# Cloud LLM fallback (optional — used when Ollama is unreachable)
OPENAI_API_KEY=
GEMINI_API_KEY=

# Obsidian vault path
OBSIDIAN_VAULT_PATH=/mnt/d/DM01

# Telegram notifications (real-time alerts for high-affinity matches)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Email digest (weekly summary)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=
EMAIL_PASSWORD=
EMAIL_RECEIVER=

# Google Sheets (master opportunity log)
GOOGLE_SHEET_ID=
GOOGLE_CREDENTIALS_PATH=credentials.json

# App
LOG_LEVEL=INFO
APP_PORT=8400

# Processing
DEDUP_DISTANCE_THRESHOLD=0.15
HIGH_AFFINITY_THRESHOLD=8
WEEKLY_EMAIL_INTERVAL_DAYS=7
```

- [ ] **Step 6: Create data directory for state.db**

```bash
mkdir -p data
echo "*.db" > data/.gitignore
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml config/settings.py config/sources/wordpress_sites.yaml \
       config/profiles/user_profile.txt .env.example data/.gitignore
git commit -m "feat: add configuration foundation for scrapper migration

Add LLM provider settings (Ollama-first), WordPress site configs,
Google Sheets settings, user profile, and pipeline state path."
```

---

## Task 2: Storage Models and State Management

**Files:**
- Modify: `observatory/storage/models.py`
- Create: `observatory/storage/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Update observatory/storage/models.py**

Replace the entire file:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CollectedItem(BaseModel):
    url: str
    title: str
    source: str
    source_type: str  # rss | wordpress | playwright
    raw_text: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    affinity_score: int = 0
    is_free_or_funded: bool = False
    category: str = "general"
    summary: str = ""
    reasoning: str = ""


class EvaluatedItem(BaseModel):
    url: str
    title: str
    source: str
    source_type: str
    raw_text: str
    collected_at: datetime
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    evaluation: Optional[EvaluationResult] = None

    topics: list[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    affinity_score: int = 0
    is_free_or_funded: bool = False
    category: str = "general"
    summary: str = ""
    reasoning: str = ""

    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    obsidian_path: Optional[str] = None
```

- [ ] **Step 2: Write failing tests for state.py**

Create `tests/test_state.py`:

```python
import os
import pytest
from observatory.storage.state import PipelineState


@pytest.fixture
def state(tmp_path):
    db_path = tmp_path / "test_state.db"
    return PipelineState(db_path)


def test_init_creates_tables(state):
    assert state.get("nonexistent") is None


def test_set_and_get(state):
    state.set("last_run", "2026-05-11T10:00:00")
    assert state.get("last_run") == "2026-05-11T10:00:00"


def test_set_overwrites(state):
    state.set("key", "value1")
    state.set("key", "value2")
    assert state.get("key") == "value2"


def test_should_send_weekly_email_true_when_never_sent(state):
    assert state.should_send_weekly_email(interval_days=7) is True


def test_should_send_weekly_email_false_when_recent(state):
    state.mark_weekly_email_sent()
    assert state.should_send_weekly_email(interval_days=7) is False


def test_should_send_weekly_email_true_after_interval(state):
    from datetime import datetime, timedelta
    old_date = (datetime.now() - timedelta(days=8)).isoformat()
    state.set("last_weekly_email", old_date)
    assert state.should_send_weekly_email(interval_days=7) is True
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'observatory.storage.state'`

- [ ] **Step 4: Implement observatory/storage/state.py**

```python
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PipelineState:
    def __init__(self, db_path: Path | str = "data/state.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS state "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )

    def get(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM state WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (key, value),
            )

    def should_send_weekly_email(self, interval_days: int = 7) -> bool:
        last_sent = self.get("last_weekly_email")
        if not last_sent:
            return True
        last_dt = datetime.fromisoformat(last_sent)
        return (datetime.now() - last_dt).days >= interval_days

    def mark_weekly_email_sent(self):
        self.set("last_weekly_email", datetime.now().isoformat())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_state.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add observatory/storage/models.py observatory/storage/state.py tests/test_state.py
git commit -m "feat: add EvaluationResult model and pipeline state management

State uses lightweight SQLite for run metadata (weekly email tracking).
Items stay in ChromaDB."
```

---

## Task 3: ChromaDB Store Updates

**Files:**
- Modify: `observatory/storage/chromadb_store.py`
- Create: `tests/test_chromadb_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_chromadb_store.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from observatory.storage.chromadb_store import url_to_id, url_exists, update_item_evaluation


def test_url_to_id_deterministic():
    url = "https://example.com/opp/123"
    assert url_to_id(url) == url_to_id(url)


def test_url_to_id_different_urls():
    assert url_to_id("https://a.com") != url_to_id("https://b.com")


@patch("observatory.storage.chromadb_store.get_items_collection")
def test_url_exists_true(mock_collection):
    collection = MagicMock()
    collection.get.return_value = {"ids": ["abc123"]}
    mock_collection.return_value = collection
    assert url_exists("https://example.com") is True


@patch("observatory.storage.chromadb_store.get_items_collection")
def test_url_exists_false(mock_collection):
    collection = MagicMock()
    collection.get.return_value = {"ids": []}
    mock_collection.return_value = collection
    assert url_exists("https://nonexistent.com") is False


@patch("observatory.storage.chromadb_store.get_items_collection")
def test_update_item_evaluation(mock_collection):
    collection = MagicMock()
    collection.get.return_value = {
        "ids": ["abc"],
        "metadatas": [{"url": "https://example.com", "title": "Test"}],
    }
    mock_collection.return_value = collection

    update_item_evaluation(
        url="https://example.com",
        affinity_score=9,
        category="scholarship",
        summary="Great match",
        reasoning="Strong AI focus",
        is_free_or_funded=True,
    )

    collection.update.assert_called_once()
    call_kwargs = collection.update.call_args
    metadata = call_kwargs[1]["metadatas"][0] if call_kwargs[1] else call_kwargs[0][2][0]
    assert metadata["affinity_score"] == 9
    assert metadata["category"] == "scholarship"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_chromadb_store.py -v`
Expected: FAIL — `url_exists` and `update_item_evaluation` not found

- [ ] **Step 3: Add url_exists and update_item_evaluation to chromadb_store.py**

Append these functions to the end of `observatory/storage/chromadb_store.py` (after `get_item_count`):

```python
def url_exists(url: str) -> bool:
    collection = get_items_collection()
    doc_id = url_to_id(url)
    results = collection.get(ids=[doc_id])
    return bool(results["ids"])


def update_item_evaluation(
    url: str,
    affinity_score: int,
    category: str = "general",
    summary: str = "",
    reasoning: str = "",
    is_free_or_funded: bool = False,
):
    collection = get_items_collection()
    doc_id = url_to_id(url)

    existing = collection.get(ids=[doc_id])
    if not existing["ids"]:
        logger.warning(f"Cannot update evaluation for unknown URL: {url[:60]}")
        return

    metadata = existing["metadatas"][0] if existing["metadatas"] else {}
    metadata.update({
        "affinity_score": affinity_score,
        "category": category,
        "summary": summary,
        "reasoning": reasoning,
        "is_free_or_funded": is_free_or_funded,
        "processed_at": datetime.utcnow().isoformat(),
    })

    collection.update(ids=[doc_id], metadatas=[metadata])
    logger.info(f"Updated evaluation for {doc_id[:12]}... (score={affinity_score}, cat={category})")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_chromadb_store.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/storage/chromadb_store.py tests/test_chromadb_store.py
git commit -m "feat: add url_exists and update_item_evaluation to ChromaDB store

Supports pipeline flow: upsert item first, then update with evaluation
results after LLM scoring."
```

---

## Task 4: Enhanced Deduplicator

**Files:**
- Modify: `observatory/processing/deduplicator.py`
- Create: `tests/test_deduplicator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_deduplicator.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from observatory.processing.deduplicator import is_duplicate


@patch("observatory.processing.deduplicator.chromadb_store")
def test_exact_url_duplicate(mock_store):
    mock_store.url_exists.return_value = True
    dup, dup_of = is_duplicate("Some text about AI", "https://example.com/opp1")
    assert dup is True
    assert dup_of == "https://example.com/opp1"
    mock_store.find_nearest.assert_not_called()


@patch("observatory.processing.deduplicator.chromadb_store")
def test_semantic_duplicate(mock_store):
    mock_store.url_exists.return_value = False
    mock_store.find_nearest.return_value = (
        0.05,
        {"url": "https://other.com/same-opp"},
    )
    dup, dup_of = is_duplicate("AI scholarship in Finland", "https://new.com/opp")
    assert dup is True
    assert dup_of == "https://other.com/same-opp"


@patch("observatory.processing.deduplicator.chromadb_store")
def test_not_duplicate(mock_store):
    mock_store.url_exists.return_value = False
    mock_store.find_nearest.return_value = (0.85, {"url": "https://unrelated.com"})
    dup, dup_of = is_duplicate("Completely new opportunity", "https://brand-new.com")
    assert dup is False
    assert dup_of is None


@patch("observatory.processing.deduplicator.chromadb_store")
def test_empty_store(mock_store):
    mock_store.url_exists.return_value = False
    mock_store.find_nearest.return_value = (None, None)
    dup, dup_of = is_duplicate("First item ever", "https://first.com")
    assert dup is False
    assert dup_of is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_deduplicator.py -v`
Expected: FAIL — `url_exists` not called / different function signature

- [ ] **Step 3: Rewrite observatory/processing/deduplicator.py**

Replace the entire file:

```python
import logging

from config.settings import settings
from observatory.storage import chromadb_store
from observatory.processing.embedder import clean_for_embedding

logger = logging.getLogger(__name__)


def is_duplicate(raw_text: str, url: str) -> tuple[bool, str | None]:
    """
    Two-phase deduplication:
    1. URL hash check (fast O(1) — catches exact re-scrapes)
    2. Semantic similarity (expensive — catches same opp on different sites)
    """
    if chromadb_store.url_exists(url):
        return True, url

    cleaned = clean_for_embedding(raw_text)
    distance, metadata = chromadb_store.find_nearest(cleaned)

    if distance is None:
        return False, None

    existing_url = metadata.get("url", "") if metadata else ""

    if distance < settings.dedup_distance_threshold:
        logger.info(
            f"Semantic duplicate (distance={distance:.3f}): "
            f"'{url[:60]}' ≈ '{existing_url[:60]}'"
        )
        return True, existing_url

    return False, None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_deduplicator.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/processing/deduplicator.py tests/test_deduplicator.py
git commit -m "feat: dual deduplication — URL hash first, then semantic similarity

URL hash check is O(1) and catches the 90% case (re-scrapes).
Semantic similarity catches the same opportunity posted on different sites."
```

---

## Task 5: LLM Evaluator with Provider Chain

**Files:**
- Create: `observatory/intelligence/evaluator.py`
- Create: `tests/test_evaluator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_evaluator.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from observatory.intelligence.evaluator import (
    parse_llm_response,
    build_evaluation_prompt,
    evaluate_opportunity,
)
from observatory.storage.models import EvaluationResult


def test_parse_valid_json():
    raw = json.dumps({
        "affinity_score": 9,
        "is_free_or_funded": True,
        "category": "scholarship",
        "summary": "Great AI PhD program",
        "reasoning": "Perfect match",
    })
    result = parse_llm_response(raw)
    assert isinstance(result, EvaluationResult)
    assert result.affinity_score == 9
    assert result.category == "scholarship"
    assert result.is_free_or_funded is True


def test_parse_json_with_markdown_fences():
    raw = '```json\n{"affinity_score": 7, "is_free_or_funded": false, "category": "job", "summary": "AI role", "reasoning": "OK"}\n```'
    result = parse_llm_response(raw)
    assert result.affinity_score == 7
    assert result.category == "job"


def test_parse_invalid_json_returns_default():
    result = parse_llm_response("not json at all")
    assert result.affinity_score == 1
    assert result.category == "general"


def test_parse_clamps_score():
    raw = json.dumps({
        "affinity_score": 15,
        "is_free_or_funded": False,
        "category": "grant",
        "summary": "Test",
        "reasoning": "Test",
    })
    result = parse_llm_response(raw)
    assert result.affinity_score == 10


def test_build_prompt_includes_profile_and_text():
    prompt = build_evaluation_prompt("User: AI researcher", "PhD in AI at MIT")
    assert "AI researcher" in prompt
    assert "PhD in AI at MIT" in prompt


def test_build_prompt_truncates_long_text():
    long_text = "x" * 10000
    prompt = build_evaluation_prompt("Short profile", long_text)
    assert len(prompt) < 10000


@pytest.mark.asyncio
@patch("observatory.intelligence.evaluator._get_provider")
async def test_evaluate_opportunity_success(mock_get_provider):
    mock_provider = AsyncMock()
    mock_provider.invoke.return_value = json.dumps({
        "affinity_score": 8,
        "is_free_or_funded": True,
        "category": "fellowship",
        "summary": "AI fellowship",
        "reasoning": "Good match",
    })
    mock_get_provider.return_value = mock_provider

    with patch("observatory.intelligence.evaluator._load_user_profile", return_value="Test profile"):
        result = await evaluate_opportunity("Fellowship in AI education")

    assert result is not None
    assert result.affinity_score == 8
    assert result.category == "fellowship"


@pytest.mark.asyncio
@patch("observatory.intelligence.evaluator._get_provider")
async def test_evaluate_opportunity_all_providers_fail(mock_get_provider):
    mock_get_provider.return_value = None

    with patch("observatory.intelligence.evaluator._load_user_profile", return_value="Test profile"):
        result = await evaluate_opportunity("Some opportunity")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_evaluator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement observatory/intelligence/evaluator.py**

```python
import json
import logging
import textwrap
from pathlib import Path
from typing import Optional

from config.settings import settings
from observatory.storage.models import EvaluationResult
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are an expert analyzer of professional opportunities spanning education,
AI research, technology careers, and funding/grants.

Your task: read a recently scraped opportunity and evaluate how well it matches
the user's profile.

--- USER PROFILE ---
{user_profile}

--- OPPORTUNITY FOUND ---
{opportunity_text}

--- INSTRUCTIONS ---
1. Analyze the opportunity against the user's profile, skills, and interests.
2. Determine if it is free, funded, or paid (scholarships, grants, salary).
3. Classify the opportunity type into one of these categories:
   scholarship, fellowship, internship, job, grant, conference, award, general.
4. Assign an affinity score from 1 to 10 (10 = perfect match). Consider:
   - Educational programs (PhD, summer schools, exchange programs)
   - AI/ML research positions (postdoc, research engineer, lab positions)
   - Tech jobs (especially AI/data science, remote-friendly)
   - Grants and funding (NGO grants, research funding, project grants)
   - Conferences and workshops (CFPs, speaking opportunities, AI + education)
5. Summarize what the opportunity is about in 2 sentences max.

Return ONLY valid JSON with this structure, no extra text or markdown blocks:
{{"affinity_score": (int 1-10), "is_free_or_funded": (bool), "category": (str), "summary": (str), "reasoning": (str)}}"""


def _load_user_profile() -> str:
    profile_path = Path(settings.user_profile_path)
    if not profile_path.exists():
        logger.warning(f"User profile not found at {profile_path}")
        return "No user profile available."
    return profile_path.read_text(encoding="utf-8")


def build_evaluation_prompt(user_profile: str, opportunity_text: str) -> str:
    truncated = textwrap.shorten(opportunity_text, width=6000, placeholder="... [truncated]")
    return PROMPT_TEMPLATE.format(user_profile=user_profile, opportunity_text=truncated)


def parse_llm_response(raw: str) -> EvaluationResult:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        score = max(1, min(10, int(data.get("affinity_score", 1))))
        return EvaluationResult(
            affinity_score=score,
            is_free_or_funded=bool(data.get("is_free_or_funded", False)),
            category=str(data.get("category", "general")),
            summary=str(data.get("summary", "")),
            reasoning=str(data.get("reasoning", "")),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return EvaluationResult(
            affinity_score=1,
            summary="LLM response could not be parsed",
            reasoning=str(e),
        )


async def _get_provider():
    """Returns an LLM provider in priority order: Ollama → OpenAI → Gemini."""
    if await check_ollama():
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=0,
            )
        except Exception as e:
            logger.warning(f"Ollama provider failed to initialize: {e}")

    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", temperature=0)
        except Exception as e:
            logger.warning(f"OpenAI provider failed to initialize: {e}")

    if settings.gemini_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
        except Exception as e:
            logger.warning(f"Gemini provider failed to initialize: {e}")

    logger.error("No LLM provider available")
    return None


async def evaluate_opportunity(opportunity_text: str) -> Optional[EvaluationResult]:
    provider = await _get_provider()
    if provider is None:
        return None

    user_profile = _load_user_profile()
    prompt_text = build_evaluation_prompt(user_profile, opportunity_text)

    try:
        from langchain_core.messages import HumanMessage
        response = await provider.ainvoke([HumanMessage(content=prompt_text)])
        return parse_llm_response(response.content)
    except Exception as e:
        logger.error(f"LLM evaluation failed: {e}")
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_evaluator.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/intelligence/evaluator.py tests/test_evaluator.py
git commit -m "feat: LLM evaluator with Ollama-first provider chain

Tries Ollama → OpenAI → Gemini in order. Parses JSON response into
EvaluationResult model. Clamps scores, handles markdown fences."
```

---

## Task 6: WordPress Collector

**Files:**
- Create: `observatory/collectors/wordpress.py`
- Create: `tests/test_wordpress.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_wordpress.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from observatory.collectors.wordpress import WordPressCollector


@pytest.fixture
def wp_config(tmp_path):
    config = tmp_path / "wp.yaml"
    config.write_text("""sites:
  - name: TestSite
    base_url: https://test.example.com
    enabled: true
  - name: DisabledSite
    base_url: https://disabled.example.com
    enabled: false
""")
    return config


def test_loads_enabled_sites_only(wp_config):
    collector = WordPressCollector(config_path=wp_config)
    assert len(collector.sites) == 1
    assert collector.sites[0]["name"] == "TestSite"


def test_missing_config_file():
    collector = WordPressCollector(config_path=Path("/nonexistent.yaml"))
    assert collector.sites == []


SAMPLE_WP_RESPONSE = [
    {
        "link": "https://test.example.com/opp/1",
        "title": {"rendered": "AI Fellowship 2026"},
        "content": {"rendered": "<p>Apply now for this AI fellowship.</p>"},
        "excerpt": {"rendered": "<p>Short desc</p>"},
        "meta": {},
    }
]


@pytest.mark.asyncio
@patch("observatory.collectors.wordpress.httpx.AsyncClient")
async def test_collect_returns_items(mock_client_cls, wp_config):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_WP_RESPONSE

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    collector = WordPressCollector(config_path=wp_config, keywords=["AI"], delay_range=(0, 0))
    items = await collector.collect()

    assert len(items) == 1
    assert items[0].title == "AI Fellowship 2026"
    assert items[0].source == "TestSite"
    assert items[0].source_type == "wordpress"
    assert "Apply now" in items[0].raw_text


@pytest.mark.asyncio
@patch("observatory.collectors.wordpress.httpx.AsyncClient")
async def test_collect_handles_rate_limit(mock_client_cls, wp_config):
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = SAMPLE_WP_RESPONSE

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[rate_limit_response, ok_response])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    collector = WordPressCollector(config_path=wp_config, keywords=["AI"], delay_range=(0, 0))
    items = await collector.collect()

    assert len(items) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_wordpress.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement observatory/collectors/wordpress.py**

```python
import asyncio
import logging
import random
from datetime import datetime
from html import unescape
from pathlib import Path

import httpx
import yaml

from observatory.collectors.base import BaseCollector
from observatory.storage.models import CollectedItem
from config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "DigitalObservatory/1.0 (educational research; contact: hesusgc@gmail.com)"
}


class WordPressCollector(BaseCollector):
    name = "wordpress"
    source_type = "wordpress"

    def __init__(
        self,
        config_path: Path | None = None,
        keywords: list[str] | None = None,
        delay_range: tuple[float, float] | None = None,
    ):
        self.config_path = config_path or settings.wordpress_config_path
        self.keywords = keywords or settings.wp_default_keywords
        self.delay_range = delay_range if delay_range is not None else (
            settings.wp_request_delay_min,
            settings.wp_request_delay_max,
        )
        self.sites: list[dict] = []
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            logger.warning(f"WordPress config not found: {self.config_path}")
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.sites = [s for s in data.get("sites", []) if s.get("enabled", True)]

    async def collect(self) -> list[CollectedItem]:
        items = []
        for site in self.sites:
            try:
                site_items = await self._scrape_site(site)
                items.extend(site_items)
            except Exception as e:
                logger.error(f"Error scraping {site['name']}: {e}")
        logger.info(f"WordPress collector gathered {len(items)} items from {len(self.sites)} sites")
        return items

    async def _scrape_site(self, site: dict) -> list[CollectedItem]:
        base_url = site["base_url"].rstrip("/")
        source_name = site["name"]
        endpoint = f"{base_url}/wp-json/wp/v2/posts"
        seen_urls: set[str] = set()
        results: list[CollectedItem] = []

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0) as client:
            for term in self.keywords:
                params = {"per_page": settings.wp_max_results_per_site, "search": term}

                try:
                    resp = await client.get(endpoint, params=params)

                    if resp.status_code == 429:
                        logger.warning(f"[{source_name}] Rate limited. Retrying after 5s...")
                        await asyncio.sleep(5)
                        resp = await client.get(endpoint, params=params)

                    if resp.status_code != 200:
                        logger.warning(
                            f"[{source_name}] HTTP {resp.status_code} for term='{term}'"
                        )
                        continue

                    posts = resp.json()
                    if not posts:
                        continue

                    for post in posts:
                        item = self._parse_post(post, source_name, seen_urls)
                        if item:
                            results.append(item)

                except httpx.HTTPError as e:
                    logger.error(f"[{source_name}] Request error for term='{term}': {e}")
                    continue

                if self.delay_range[1] > 0:
                    await asyncio.sleep(random.uniform(*self.delay_range))

        logger.info(f"[{source_name}] Collected {len(results)} opportunities")
        return results

    def _parse_post(
        self, post: dict, source_name: str, seen_urls: set[str]
    ) -> CollectedItem | None:
        url = post.get("link", "")
        if not url or url in seen_urls:
            return None
        seen_urls.add(url)

        title_html = post.get("title", {}).get("rendered", "")
        title = unescape(self._strip_html(title_html))

        content_html = post.get("content", {}).get("rendered", "")
        content_text = self._strip_html(content_html)

        excerpt_html = post.get("excerpt", {}).get("rendered", "")
        excerpt = self._strip_html(excerpt_html)

        meta = post.get("meta", {})
        meta_text = ""
        if isinstance(meta, dict):
            for k, v in meta.items():
                if v and str(v).strip():
                    meta_text += f"{k}: {v}\n"

        raw_text = ""
        if meta_text:
            raw_text += meta_text + "\n"
        if excerpt:
            raw_text += f"Excerpt: {excerpt}\n\n"
        raw_text += content_text

        return CollectedItem(
            url=url,
            title=title,
            source=source_name,
            source_type="wordpress",
            raw_text=raw_text,
            collected_at=datetime.utcnow(),
            metadata={"search_source": "wordpress_rest_api"},
        )

    @staticmethod
    def _strip_html(html: str) -> str:
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
        except ImportError:
            import re
            return re.sub(r"<[^>]+>", "", html).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_wordpress.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/collectors/wordpress.py tests/test_wordpress.py
git commit -m "feat: config-driven WordPress REST API collector

Reads site URLs from YAML config. Async httpx with rate-limit retry.
Adding a new WordPress site = one YAML entry, zero code."
```

---

## Task 7: Playwright Collector

**Files:**
- Create: `observatory/collectors/playwright_collector.py`
- Create: `tests/test_playwright_collector.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_playwright_collector.py`:

```python
import pytest
from unittest.mock import patch
from observatory.collectors.playwright_collector import PlaywrightCollector, SITE_CONFIGS


def test_site_configs_defined():
    assert "finland" in SITE_CONFIGS
    assert "canada" in SITE_CONFIGS
    assert "germany" in SITE_CONFIGS


def test_collector_filters_enabled_sites():
    collector = PlaywrightCollector(enabled_sites=["finland", "germany"])
    assert len(collector.enabled_sites) == 2


@pytest.mark.asyncio
async def test_collect_without_playwright_installed():
    with patch("observatory.collectors.playwright_collector.sync_playwright", None):
        collector = PlaywrightCollector(enabled_sites=["finland"])
        items = await collector.collect()
        assert items == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_playwright_collector.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement observatory/collectors/playwright_collector.py**

```python
import asyncio
import logging
import random
import time
from datetime import datetime

from observatory.collectors.base import BaseCollector
from observatory.storage.models import CollectedItem

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
)

SITE_CONFIGS = {
    "finland": {
        "name": "Studyinfo.fi",
        "search_url": "https://opintopolku.fi/konfo/en/haku?keyword={query}",
        "link_pattern": "/konfo/en/toteutus/,/konfo/en/koulutus/",
        "base_domain": "https://opintopolku.fi",
        "max_detail_pages": 3,
        "default_query": "artificial intelligence",
    },
    "canada": {
        "name": "EduCanada",
        "search_url": "https://www.educanada.ca/scholarships-bourses/non_can/search-recherche.aspx?sk={query}",
        "link_pattern": "/scholarships-bourses/",
        "base_domain": "https://www.educanada.ca",
        "max_detail_pages": 5,
        "default_query": "artificial intelligence education",
    },
    "germany": {
        "name": "DAAD.de",
        "search_url": "https://www2.daad.de/deutschland/studienangebote/studiengang/en/?a=result&q={query}&degree%5B%5D=3&fos=4&sc=1",
        "link_pattern": "/studiengang/,detail",
        "base_domain": "https://www2.daad.de",
        "max_detail_pages": 5,
        "default_query": "artificial intelligence",
    },
}


class PlaywrightCollector(BaseCollector):
    name = "playwright"
    source_type = "playwright"

    def __init__(self, enabled_sites: list[str] | None = None):
        self.enabled_sites = enabled_sites or list(SITE_CONFIGS.keys())

    async def collect(self) -> list[CollectedItem]:
        if sync_playwright is None:
            logger.warning("Playwright not installed. Skipping browser-based scrapers.")
            return []
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> list[CollectedItem]:
        items = []
        for site_key in self.enabled_sites:
            config = SITE_CONFIGS.get(site_key)
            if not config:
                continue
            try:
                site_items = self._scrape_site(config)
                items.extend(site_items)
            except Exception as e:
                logger.error(f"Error scraping {config['name']}: {e}")
        return items

    def _scrape_site(self, config: dict) -> list[CollectedItem]:
        results = []
        query = config["default_query"]
        search_url = config["search_url"].format(query=query.replace(" ", "+"))

        logger.info(f"[Playwright] Opening browser for {config['name']}: {search_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=BROWSER_UA)
            page = context.new_page()

            try:
                page.goto(search_url, wait_until="networkidle", timeout=30000)
                time.sleep(random.uniform(2.0, 4.0))

                html = page.content()
                if BeautifulSoup is None:
                    logger.warning("BeautifulSoup not installed, cannot parse links")
                    return results

                soup = BeautifulSoup(html, "html.parser")
                patterns = [p.strip() for p in config["link_pattern"].split(",")]

                urls = set()
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(pat in href for pat in patterns):
                        full_url = href if href.startswith("http") else f"{config['base_domain']}{href}"
                        urls.add(full_url)

                logger.info(f"[Playwright] {config['name']}: {len(urls)} links found")

                for url in list(urls)[: config["max_detail_pages"]]:
                    try:
                        page.goto(url, wait_until="networkidle", timeout=20000)
                        time.sleep(random.uniform(1.0, 3.0))
                        raw_text = page.locator("body").inner_text()
                        title = page.title()

                        results.append(
                            CollectedItem(
                                url=url,
                                title=title,
                                source=config["name"],
                                source_type="playwright",
                                raw_text=raw_text,
                                collected_at=datetime.utcnow(),
                                metadata={"scrape_method": "playwright"},
                            )
                        )
                        logger.info(f"  -> Extracted: {title[:50]}...")
                    except Exception as e:
                        logger.error(f"Error visiting {url}: {e}")
            except Exception as e:
                logger.error(f"Error during {config['name']} scraping: {e}")
            finally:
                browser.close()

        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_playwright_collector.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/collectors/playwright_collector.py tests/test_playwright_collector.py
git commit -m "feat: Playwright collector for JS-rendered educational sites

Supports Finland (StudyInfo), Canada (EduCanada), Germany (DAAD).
Gracefully skips if Playwright is not installed."
```

---

## Task 8: Telegram Output

**Files:**
- Create: `observatory/outputs/telegram.py`
- Create: `tests/test_telegram.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_telegram.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from observatory.outputs.telegram import format_alert_message, send_telegram_alert


def test_format_alert_message_basic():
    msg = format_alert_message(
        title="AI Fellowship",
        url="https://example.com",
        source="TestSource",
        score=9,
        summary="Great opportunity",
        category="fellowship",
    )
    assert "AI Fellowship" in msg
    assert "9/10" in msg
    assert "FELLOWSHIP" in msg
    assert "https://example.com" in msg


def test_format_alert_message_general_category():
    msg = format_alert_message(
        title="Test", url="https://x.com", source="S", score=8,
        summary="Sum", category="general",
    )
    assert "Type:" not in msg


@pytest.mark.asyncio
@patch("observatory.outputs.telegram.httpx.AsyncClient")
async def test_send_alert_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    result = await send_telegram_alert(
        title="Test", url="https://x.com", source="S", score=9,
        summary="Sum", category="grant",
        token="fake-token", chat_id="123",
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_alert_not_configured():
    result = await send_telegram_alert(
        title="Test", url="https://x.com", source="S", score=9,
        summary="Sum", token="", chat_id="",
    )
    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_telegram.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement observatory/outputs/telegram.py**

```python
import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


def format_alert_message(
    title: str,
    url: str,
    source: str,
    score: int,
    summary: str,
    category: str = "general",
) -> str:
    cat_line = ""
    if category and category != "general":
        cat_line = f"*Type:* {category.upper()}\n"

    return (
        f"\U0001f31f *HIGH MATCH! ({score}/10)* \U0001f31f\n\n"
        f"*Source:* {source}\n"
        f"{cat_line}"
        f"*Title:* {title}\n"
        f"*AI Summary:* {summary}\n\n"
        f"\U0001f517 *Link:* {url}"
    )


async def send_telegram_alert(
    title: str,
    url: str,
    source: str,
    score: int,
    summary: str,
    category: str = "general",
    token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    token = token if token is not None else settings.telegram_bot_token
    chat_id = chat_id if chat_id is not None else settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("Telegram not configured. Skipping alert.")
        return False

    message = format_alert_message(title, url, source, score, summary, category)
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(api_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_telegram.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/outputs/telegram.py tests/test_telegram.py
git commit -m "feat: async Telegram alert output for high-affinity matches"
```

---

## Task 9: Email Output with Jinja2 Template

**Files:**
- Create: `observatory/outputs/templates/weekly_digest.html`
- Create: `observatory/outputs/email.py`
- Create: `tests/test_email.py`

- [ ] **Step 1: Create the Jinja2 email template**

Create `observatory/outputs/templates/weekly_digest.html`:

```html
<html>
<body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
  <h2 style="color: #2c3e50;">Weekly Opportunity Radar Summary</h2>
  <p>Found <strong>{{ items | length }}</strong> opportunities this week.</p>
  <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
    <tr style="background: #2c3e50; color: white;">
      <th>Title</th>
      <th>Source</th>
      <th>Type</th>
      <th>Score</th>
      <th>Link</th>
    </tr>
    {% for item in items %}
    <tr style="background: {{ '#e8f5e9' if item.score >= 8 else '#ffffff' }};">
      <td>{{ item.title }}</td>
      <td>{{ item.source }}</td>
      <td>{{ item.category }}</td>
      <td>{{ item.score }}/10</td>
      <td><a href="{{ item.url }}">View</a></td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_email.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from observatory.outputs.email import render_weekly_digest, send_weekly_email


def test_render_weekly_digest():
    items = [
        {"title": "AI PhD", "source": "DAAD", "category": "scholarship", "score": 9, "url": "https://x.com"},
        {"title": "ML Job", "source": "LinkedIn", "category": "job", "score": 6, "url": "https://y.com"},
    ]
    html = render_weekly_digest(items)
    assert "AI PhD" in html
    assert "ML Job" in html
    assert "2 opportunities" in html or "2</strong>" in html


def test_render_empty_digest():
    html = render_weekly_digest([])
    assert "0</strong>" in html or "0 opportunities" in html


@pytest.mark.asyncio
async def test_send_email_not_configured():
    result = await send_weekly_email(
        items=[],
        smtp_server="",
        sender="",
        password="",
        receiver="",
    )
    assert result is False


@pytest.mark.asyncio
@patch("observatory.outputs.email.smtplib.SMTP")
async def test_send_email_success(mock_smtp_cls):
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    items = [{"title": "Test", "source": "S", "category": "general", "score": 5, "url": "https://x.com"}]
    result = await send_weekly_email(
        items=items,
        smtp_server="smtp.test.com",
        smtp_port=587,
        sender="test@test.com",
        password="pass",
        receiver="recv@test.com",
    )
    assert result is True
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_email.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement observatory/outputs/email.py**

```python
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config.settings import settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_weekly_digest(items: list[dict]) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("weekly_digest.html")
    return template.render(items=items)


async def send_weekly_email(
    items: list[dict],
    smtp_server: str | None = None,
    smtp_port: int | None = None,
    sender: str | None = None,
    password: str | None = None,
    receiver: str | None = None,
) -> bool:
    smtp_server = smtp_server if smtp_server is not None else settings.smtp_server
    smtp_port = smtp_port if smtp_port is not None else settings.smtp_port
    sender = sender if sender is not None else settings.email_sender
    password = password if password is not None else settings.email_password
    receiver = receiver if receiver is not None else settings.email_receiver

    if not all([smtp_server, sender, password, receiver]):
        logger.warning("Email not configured. Skipping weekly digest.")
        return False

    html = render_weekly_digest(items)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Weekly Opportunity Radar: {len(items)} opportunities found"
    msg["From"] = sender
    msg["To"] = receiver
    msg.attach(MIMEText(html, "html"))

    def _send():
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

    try:
        await asyncio.to_thread(_send)
        logger.info(f"Weekly email sent to {receiver} with {len(items)} opportunities.")
        return True
    except Exception as e:
        logger.error(f"Failed to send weekly email: {e}")
        return False
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_email.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add observatory/outputs/templates/weekly_digest.html observatory/outputs/email.py tests/test_email.py
git commit -m "feat: weekly email digest with Jinja2 HTML template

Async SMTP send with configurable credentials. Highlights high-affinity
matches with green rows in the HTML table."
```

---

## Task 10: Google Sheets Output

**Files:**
- Create: `observatory/outputs/sheets.py`
- Create: `tests/test_sheets.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sheets.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from observatory.outputs.sheets import SheetsOutput


@patch("observatory.outputs.sheets.gspread", None)
def test_sheets_unavailable_without_gspread():
    output = SheetsOutput()
    assert output.available is False


def test_sheets_unavailable_without_config():
    output = SheetsOutput(sheet_id="", credentials_path="/nonexistent.json")
    assert output.available is False


@patch("observatory.outputs.sheets.gspread")
@patch("observatory.outputs.sheets.ServiceAccountCredentials")
def test_connect_and_append(mock_creds_cls, mock_gspread):
    mock_sheet = MagicMock()
    mock_client = MagicMock()
    mock_client.open_by_key.return_value.sheet1 = mock_sheet
    mock_gspread.authorize.return_value = mock_client
    mock_creds_cls.from_json_keyfile_name.return_value = MagicMock()

    output = SheetsOutput(sheet_id="test-id", credentials_path="creds.json")

    with patch("observatory.outputs.sheets.Path.exists", return_value=True):
        output._connect()

    assert output._sheet is not None

    output.append_row("Title", "https://x.com", "Source", 8, "Summary", "scholarship")
    mock_sheet.append_row.assert_called_once_with(
        ["Title", "https://x.com", "Source", 8, "Summary", "scholarship"]
    )


@patch("observatory.outputs.sheets.gspread")
@patch("observatory.outputs.sheets.ServiceAccountCredentials")
def test_append_row_retries_on_api_error(mock_creds_cls, mock_gspread):
    import gspread

    mock_sheet = MagicMock()
    mock_sheet.append_row.side_effect = [
        gspread.exceptions.APIError(MagicMock(status_code=503)),
        None,
    ]
    mock_client = MagicMock()
    mock_client.open_by_key.return_value.sheet1 = mock_sheet
    mock_gspread.authorize.return_value = mock_client
    mock_creds_cls.from_json_keyfile_name.return_value = MagicMock()

    output = SheetsOutput(sheet_id="test-id", credentials_path="creds.json")
    output._sheet = mock_sheet

    result = output.append_row("T", "U", "S", 5, "Sum", "general")
    assert mock_sheet.append_row.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_sheets.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement observatory/outputs/sheets.py**

```python
import logging
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    gspread = None
    ServiceAccountCredentials = None


class SheetsOutput:
    def __init__(
        self,
        sheet_id: str | None = None,
        credentials_path: str | None = None,
    ):
        self.sheet_id = sheet_id if sheet_id is not None else settings.google_sheet_id
        self.credentials_path = credentials_path or str(settings.google_credentials_path)
        self._sheet = None

    @property
    def available(self) -> bool:
        if gspread is None:
            return False
        if not self.sheet_id:
            return False
        if not Path(self.credentials_path).exists():
            return False
        return True

    def _connect(self):
        if self._sheet is not None:
            return
        if not self.available:
            return

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_path, scope)
        client = gspread.authorize(creds)
        self._sheet = client.open_by_key(self.sheet_id).sheet1
        logger.info("Connected to Google Sheets")

    def append_row(
        self,
        title: str,
        url: str,
        source: str,
        score: int,
        summary: str = "",
        category: str = "general",
    ) -> bool:
        if not self.available:
            return False

        self._connect()
        if self._sheet is None:
            return False

        row = [title, url, source, score, summary, category]
        try:
            self._sheet.append_row(row)
            return True
        except gspread.exceptions.APIError:
            logger.warning("Sheets API error. Reconnecting...")
            self._sheet = None
            self._connect()
            if self._sheet:
                try:
                    self._sheet.append_row(row)
                    return True
                except Exception as e:
                    logger.error(f"Sheets retry failed: {e}")
                    return False
        except Exception as e:
            logger.error(f"Error writing to Sheets: {e}")
            return False
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_sheets.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/outputs/sheets.py tests/test_sheets.py
git commit -m "feat: Google Sheets output with connection caching and single retry

Gracefully skips if gspread is not installed or credentials missing."
```

---

## Task 11: Pipeline Orchestrator

**Files:**
- Create: `observatory/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_pipeline.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from observatory.pipeline import run_pipeline, PipelineResult
from observatory.storage.models import CollectedItem
from datetime import datetime


def _make_item(url="https://example.com/1", title="Test Opp", source="TestSource"):
    return CollectedItem(
        url=url, title=title, source=source, source_type="wordpress",
        raw_text="AI fellowship in education technology",
        collected_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
@patch("observatory.pipeline.RSSCollector")
@patch("observatory.pipeline.WordPressCollector")
@patch("observatory.pipeline.is_duplicate", return_value=(False, None))
@patch("observatory.pipeline.evaluate_opportunity")
@patch("observatory.pipeline.chromadb_store")
@patch("observatory.pipeline.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_full_flow(
    mock_telegram, mock_store, mock_eval, mock_dedup, mock_wp, mock_rss
):
    item = _make_item()
    mock_rss_instance = AsyncMock()
    mock_rss_instance.collect.return_value = [item]
    mock_rss.return_value = mock_rss_instance

    mock_wp_instance = AsyncMock()
    mock_wp_instance.collect.return_value = []
    mock_wp.return_value = mock_wp_instance

    from observatory.storage.models import EvaluationResult
    mock_eval.return_value = EvaluationResult(
        affinity_score=9, is_free_or_funded=True,
        category="fellowship", summary="Great match", reasoning="Strong AI focus",
    )

    mock_store.upsert_item.return_value = "abc123"

    result = await run_pipeline(enable_playwright=False)

    assert isinstance(result, PipelineResult)
    assert result.collected == 1
    assert result.new_items == 1
    assert result.evaluated == 1
    assert result.high_affinity == 1
    mock_telegram.assert_called_once()


@pytest.mark.asyncio
@patch("observatory.pipeline.RSSCollector")
@patch("observatory.pipeline.WordPressCollector")
@patch("observatory.pipeline.is_duplicate", return_value=(True, "https://dup.com"))
async def test_pipeline_skips_duplicates(mock_dedup, mock_wp, mock_rss):
    mock_rss_instance = AsyncMock()
    mock_rss_instance.collect.return_value = [_make_item()]
    mock_rss.return_value = mock_rss_instance

    mock_wp_instance = AsyncMock()
    mock_wp_instance.collect.return_value = []
    mock_wp.return_value = mock_wp_instance

    result = await run_pipeline(enable_playwright=False)

    assert result.collected == 1
    assert result.duplicates == 1
    assert result.new_items == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement observatory/pipeline.py**

```python
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from config.settings import settings
from observatory.collectors.rss import RSSCollector
from observatory.collectors.wordpress import WordPressCollector
from observatory.intelligence.evaluator import evaluate_opportunity
from observatory.processing.deduplicator import is_duplicate
from observatory.processing.embedder import clean_for_embedding
from observatory.storage import chromadb_store
from observatory.storage.models import CollectedItem
from observatory.storage.state import PipelineState
from observatory.outputs.telegram import send_telegram_alert
from observatory.outputs.email import send_weekly_email
from observatory.outputs.sheets import SheetsOutput
from observatory.monitoring import metrics

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    collected: int = 0
    duplicates: int = 0
    new_items: int = 0
    evaluated: int = 0
    eval_failures: int = 0
    high_affinity: int = 0
    notifications_sent: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


async def run_pipeline(
    enable_rss: bool = True,
    enable_wordpress: bool = True,
    enable_playwright: bool = False,
    keywords: list[str] | None = None,
    source_filter: list[str] | None = None,
) -> PipelineResult:
    result = PipelineResult()
    logger.info("Starting opportunity pipeline...")

    items = await _collect(
        enable_rss=enable_rss,
        enable_wordpress=enable_wordpress,
        enable_playwright=enable_playwright,
        keywords=keywords,
        source_filter=source_filter,
    )
    result.collected = len(items)
    logger.info(f"Collected {len(items)} items from all sources")

    sheets = SheetsOutput()

    for item in items:
        dup, dup_of = is_duplicate(item.raw_text, item.url)
        if dup:
            result.duplicates += 1
            metrics.items_deduplicated.labels(source=item.source).inc()
            continue

        result.new_items += 1

        chromadb_store.upsert_item(
            url=item.url,
            title=item.title,
            source=item.source,
            source_type=item.source_type,
            raw_text=item.raw_text,
        )

        evaluation = await evaluate_opportunity(item.raw_text)

        if evaluation is None:
            result.eval_failures += 1
            metrics.llm_errors.labels(provider="unknown").inc()
            continue

        result.evaluated += 1
        metrics.items_evaluated.labels(source=item.source).inc()

        chromadb_store.update_item_evaluation(
            url=item.url,
            affinity_score=evaluation.affinity_score,
            category=evaluation.category,
            summary=evaluation.summary,
            reasoning=evaluation.reasoning,
            is_free_or_funded=evaluation.is_free_or_funded,
        )

        sheets.append_row(
            title=item.title,
            url=item.url,
            source=item.source,
            score=evaluation.affinity_score,
            summary=evaluation.summary,
            category=evaluation.category,
        )

        if evaluation.affinity_score >= settings.high_affinity_threshold:
            result.high_affinity += 1
            metrics.items_high_affinity.labels(source=item.source).inc()

            sent = await send_telegram_alert(
                title=item.title,
                url=item.url,
                source=item.source,
                score=evaluation.affinity_score,
                summary=evaluation.summary,
                category=evaluation.category,
            )
            if sent:
                result.notifications_sent += 1
                metrics.notifications_sent.labels(channel="telegram").inc()

    await _maybe_send_weekly_email()

    result.finished_at = datetime.utcnow()
    logger.info(
        f"Pipeline complete: {result.collected} collected, {result.new_items} new, "
        f"{result.evaluated} evaluated, {result.high_affinity} high-affinity"
    )
    return result


async def _collect(
    enable_rss: bool,
    enable_wordpress: bool,
    enable_playwright: bool,
    keywords: list[str] | None,
    source_filter: list[str] | None,
) -> list[CollectedItem]:
    items: list[CollectedItem] = []
    tasks = []

    if enable_rss:
        rss = RSSCollector()
        tasks.append(rss.collect())

    if enable_wordpress:
        wp_kwargs = {}
        if keywords:
            wp_kwargs["keywords"] = keywords
        wp = WordPressCollector(**wp_kwargs)
        tasks.append(wp.collect())

    if enable_playwright:
        try:
            from observatory.collectors.playwright_collector import PlaywrightCollector
            pw = PlaywrightCollector(enabled_sites=source_filter)
            tasks.append(pw.collect())
        except ImportError:
            logger.warning("Playwright collector not available")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Collector error: {r}")
        elif isinstance(r, list):
            items.extend(r)

    return items


async def _maybe_send_weekly_email():
    state = PipelineState(settings.state_db_path)
    if not state.should_send_weekly_email(interval_days=settings.weekly_email_interval_days):
        return

    since = datetime.utcnow() - timedelta(days=7)
    recent = chromadb_store.get_recent_items(since=since)

    if not recent:
        return

    items = []
    for r in recent:
        meta = r.get("metadata", {})
        items.append({
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "category": meta.get("category", "general"),
            "score": meta.get("affinity_score", 0),
        })

    sent = await send_weekly_email(items)
    if sent:
        state.mark_weekly_email_sent()
        metrics.notifications_sent.labels(channel="email").inc()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m pytest tests/test_pipeline.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add observatory/pipeline.py tests/test_pipeline.py
git commit -m "feat: async pipeline orchestrator — collect, dedup, evaluate, notify

Runs RSS + WordPress collectors in parallel, evaluates with LLM provider
chain, sends Telegram alerts for high scores, weekly email digest."
```

---

## Task 12: CLI Entry Point

**Files:**
- Create: `observatory/cli.py`

- [ ] **Step 1: Implement observatory/cli.py**

```python
import argparse
import asyncio
import logging
import sys

from config.settings import settings


def main():
    parser = argparse.ArgumentParser(
        prog="observatory",
        description="Digital Observatory — Intelligent opportunity monitoring",
    )
    subparsers = parser.add_subparsers(dest="command")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run the opportunity pipeline")
    pipeline_sub = pipeline_parser.add_subparsers(dest="action")

    run_parser = pipeline_sub.add_parser("run", help="Execute the pipeline")
    run_parser.add_argument("--http-only", action="store_true", help="Skip Playwright scrapers")
    run_parser.add_argument("--sources", type=str, help="Collector types: rss,wordpress,playwright")
    run_parser.add_argument("--keywords", type=str, help="Comma-separated search keywords")

    status_parser = pipeline_sub.add_parser("status", help="Show last run info")

    server_parser = subparsers.add_parser("serve", help="Start the FastAPI server")
    server_parser.add_argument("--port", type=int, default=settings.app_port)

    args = parser.parse_args()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.command == "pipeline" and args.action == "run":
        _run_pipeline(args)
    elif args.command == "pipeline" and args.action == "status":
        _show_status()
    elif args.command == "serve":
        _serve(args.port)
    else:
        parser.print_help()
        sys.exit(1)


def _run_pipeline(args):
    from observatory.pipeline import run_pipeline

    sources = [s.strip() for s in args.sources.split(",")] if args.sources else None
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None

    enable_rss = sources is None or "rss" in sources
    enable_wordpress = sources is None or "wordpress" in sources
    enable_playwright = not args.http_only and (sources is None or "playwright" in sources)

    result = asyncio.run(
        run_pipeline(
            enable_rss=enable_rss,
            enable_wordpress=enable_wordpress,
            enable_playwright=enable_playwright,
            keywords=keywords,
            source_filter=sources,
        )
    )

    print(f"\nPipeline complete:")
    print(f"  Collected:    {result.collected}")
    print(f"  Duplicates:   {result.duplicates}")
    print(f"  New items:    {result.new_items}")
    print(f"  Evaluated:    {result.evaluated}")
    print(f"  High affinity:{result.high_affinity}")
    print(f"  Notifications:{result.notifications_sent}")


def _show_status():
    from observatory.storage.state import PipelineState
    state = PipelineState(settings.state_db_path)

    last_run = state.get("last_pipeline_run")
    last_email = state.get("last_weekly_email")

    print("Pipeline Status:")
    print(f"  Last run:    {last_run or 'never'}")
    print(f"  Last email:  {last_email or 'never'}")


def _serve(port: int):
    import uvicorn
    uvicorn.run("observatory.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the CLI parses without errors**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -m observatory.cli --help`
Expected: Shows help text with `pipeline`, `serve` commands

- [ ] **Step 3: Commit**

```bash
git add observatory/cli.py
git commit -m "feat: CLI entry point — observatory pipeline run / serve"
```

---

## Task 13: API Endpoint Updates

**Files:**
- Modify: `observatory/app.py`

- [ ] **Step 1: Add pipeline endpoints to observatory/app.py**

Add the following imports at the top of `observatory/app.py` (after existing imports):

```python
from observatory.pipeline import run_pipeline, PipelineResult
from observatory.storage.state import PipelineState
```

Add these endpoints before the `if __name__` block at the end of the file:

```python
@app.post("/api/pipeline/run")
async def api_pipeline_run(
    http_only: bool = Query(default=False),
    sources: str = Query(default=""),
    keywords: str = Query(default=""),
):
    """Trigger the full opportunity pipeline. Used by n8n / cron."""
    source_list = [s.strip() for s in sources.split(",") if s.strip()] or None
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] or None

    enable_rss = source_list is None or "rss" in source_list
    enable_wordpress = source_list is None or "wordpress" in source_list
    enable_playwright = not http_only and (source_list is None or "playwright" in source_list)

    result = await run_pipeline(
        enable_rss=enable_rss,
        enable_wordpress=enable_wordpress,
        enable_playwright=enable_playwright,
        keywords=keyword_list,
        source_filter=source_list,
    )

    state = PipelineState(settings.state_db_path)
    state.set("last_pipeline_run", result.started_at.isoformat())

    return {
        "status": "ok",
        "collected": result.collected,
        "duplicates": result.duplicates,
        "new_items": result.new_items,
        "evaluated": result.evaluated,
        "high_affinity": result.high_affinity,
        "notifications_sent": result.notifications_sent,
        "duration_seconds": (result.finished_at - result.started_at).total_seconds()
        if result.finished_at
        else None,
    }


@app.get("/api/pipeline/status")
async def api_pipeline_status():
    state = PipelineState(settings.state_db_path)
    return {
        "last_run": state.get("last_pipeline_run"),
        "last_weekly_email": state.get("last_weekly_email"),
    }
```

Also update the existing `/api/collect/trigger` endpoint to support `source=wordpress`:

Add after the `if source == "rss":` block inside `trigger_collection`:

```python
    elif source == "wordpress":
        from observatory.collectors.wordpress import WordPressCollector
        collector = WordPressCollector()
        items = await collector.collect()

        new_count = 0
        dup_count = 0

        for item in items:
            metrics.items_collected.labels(source=item.source, source_type=item.source_type).inc()

            cleaned = clean_for_embedding(item.raw_text)
            dup, dup_of = is_duplicate(cleaned, item.url)

            if dup:
                metrics.items_deduplicated.labels(source=item.source).inc()
                dup_count += 1
                continue

            chromadb_store.upsert_item(
                url=item.url,
                title=item.title,
                source=item.source,
                source_type=item.source_type,
                raw_text=item.raw_text,
            )
            new_count += 1

        return {
            "status": "ok",
            "source": source,
            "collected": len(items),
            "new": new_count,
            "duplicates": dup_count,
        }
```

- [ ] **Step 2: Verify the app imports correctly**

Run: `cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory && python -c "from observatory.app import app; print('OK:', [r.path for r in app.routes if hasattr(r, 'path')])" 2>&1 | head -5`
Expected: Shows list of routes including `/api/pipeline/run` and `/api/pipeline/status`

- [ ] **Step 3: Commit**

```bash
git add observatory/app.py
git commit -m "feat: add pipeline run/status API endpoints and WordPress collector trigger

POST /api/pipeline/run — full pipeline execution via n8n/cron
GET /api/pipeline/status — last run and email timestamps"
```

---

## Task 14: Docker and Final Integration

**Files:**
- Modify: `docker-compose.yml`
- Modify: `Dockerfile`

- [ ] **Step 1: Update docker-compose.yml**

Replace the observatory service volumes section and add the credentials mount:

```yaml
services:
  observatory:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: observatory
    restart: unless-stopped
    ports:
      - "8400:8400"
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://localhost:11434}
      - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.1:8b}
      - OBSIDIAN_VAULT_PATH=/vault
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - APP_PORT=8400
      - STATE_DB_PATH=/data/state.db
      - USER_PROFILE_PATH=/app/config/profiles/user_profile.txt
      - WORDPRESS_CONFIG_PATH=/app/config/sources/wordpress_sites.yaml
    env_file:
      - .env
    volumes:
      - observatory-data:/data
      - ${OBSIDIAN_VAULT_PATH:-./vault}:/vault
      - ${GOOGLE_CREDENTIALS_PATH:-./credentials.json}:/app/credentials.json:ro
    depends_on:
      chromadb:
        condition: service_healthy
    networks:
      - observatory-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8400/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3

  chromadb:
    image: chromadb/chroma:latest
    container_name: chromadb
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - chroma-data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    networks:
      - observatory-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 768M

volumes:
  observatory-data:
  chroma-data:

networks:
  observatory-net:
    driver: bridge
```

- [ ] **Step 2: Update Dockerfile to install optional dependencies**

```dockerfile
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[notifications]"

COPY . .

RUN mkdir -p /data

EXPOSE 8400
CMD ["python", "-m", "observatory.cli", "serve"]
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml Dockerfile
git commit -m "feat: update Docker config for full pipeline deployment

Adds credentials mount, state DB volume, and installs notification
dependencies. Default CMD runs the FastAPI server."
```

---

## Task 15: Run Full Test Suite

- [ ] **Step 1: Install dev dependencies and run all tests**

```bash
cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory
pip install -e ".[dev,notifications]"
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass across all test files:
- `tests/test_state.py` (6 tests)
- `tests/test_chromadb_store.py` (5 tests)
- `tests/test_deduplicator.py` (4 tests)
- `tests/test_evaluator.py` (8 tests)
- `tests/test_wordpress.py` (4 tests)
- `tests/test_playwright_collector.py` (3 tests)
- `tests/test_telegram.py` (4 tests)
- `tests/test_email.py` (4 tests)
- `tests/test_sheets.py` (4 tests)
- `tests/test_pipeline.py` (2 tests)

Total: 44 tests

- [ ] **Step 2: Fix any failures and re-run**

- [ ] **Step 3: Final commit with any fixes**

```bash
git add -A
git commit -m "test: full test suite passing — 44 tests across 10 modules"
```

---

## Task 16: Verify CLI and Server

- [ ] **Step 1: Test CLI help**

```bash
cd /mnt/c/Users/HG_Co/OneDrive/Documents/Github/digital-observatory
python -m observatory.cli --help
python -m observatory.cli pipeline run --help
```

- [ ] **Step 2: Test pipeline status (no ChromaDB needed)**

```bash
python -m observatory.cli pipeline status
```

Expected: Shows "Last run: never" and "Last email: never"

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "chore: migration complete — educational-ops-scrapper → digital-observatory

All scrapper functionality now lives in the observatory's modular architecture:
- 6 WordPress + 13 RSS + 3 Playwright collectors
- LLM evaluator with Ollama → OpenAI → Gemini fallback chain
- Telegram alerts, weekly email digests, Google Sheets logging
- Dual deduplication (URL hash + semantic similarity)
- CLI and API entry points
- 44 tests across 10 modules"
```
