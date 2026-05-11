# Migration: educational-ops-scrapper → digital-observatory

**Date:** 2026-05-11
**Status:** Approved
**Scope:** Migrate all working pipeline code from educational-ops-scrapper into digital-observatory's modular architecture

## Context

Two repositories exist for the same goal (monitoring educational and AI opportunities):

- **educational-ops-scrapper** — 97% functional pipeline (9 scrapers, LLM evaluation, Telegram/email notifications, Google Sheets). Monolithic CLI script, no API, no Docker, no monitoring.
- **digital-observatory** — 40% functional platform (FastAPI server, ChromaDB vector storage, RSS collection, Prometheus metrics, Docker). Clean modular architecture but empty `intelligence/` and `outputs/` modules.

This migration combines the working business logic of the scrapper with the production-grade architecture of the observatory. After migration, educational-ops-scrapper is archived.

## Architecture

```
                    ┌─────────────┐
                    │   Trigger   │
                    │ CLI / API / │
                    │   n8n cron  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  pipeline.py │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                  ▼
   ┌───────────┐    ┌────────────┐    ┌──────────────┐
   │    RSS    │    │ WordPress  │    │  Playwright   │
   │ Collector │    │ Collector  │    │  Collector    │
   └─────┬─────┘    └─────┬──────┘    └──────┬───────┘
         └─────────────────┼──────────────────┘
                           ▼
                    ┌──────────────┐
                    │ Deduplication│
                    │ URL hash +   │
                    │ semantic sim │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │  Evaluator   │
                    │ Ollama → OAI │
                    │  → Gemini    │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │ ChromaDB     │
                    │ upsert with  │
                    │ full metadata│
                    └──────┬───────┘
                           ▼
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                   ▼
   ┌──────────┐    ┌────────────┐    ┌───────────────┐
   │ Telegram │    │   Email    │    │ Google Sheets │
   │ (≥8/10)  │    │  (weekly)  │    │  (all items)  │
   └──────────┘    └────────────┘    └───────────────┘
```

## Module Mapping

| Source (scrapper) | Target (observatory) | Change type |
|---|---|---|
| `scraper.py` WordPress functions | `observatory/collectors/wordpress.py` | Rewrite: config-driven `WordPressCollector(BaseCollector)` |
| `scraper.py` Playwright functions | `observatory/collectors/playwright_collector.py` | Rewrite: `PlaywrightCollector(BaseCollector)`, optional dep |
| `evaluator.py` | `observatory/intelligence/evaluator.py` | Rewrite: Ollama-first provider chain, Pydantic output |
| `notifications.py` Telegram | `observatory/outputs/telegram.py` | Port: async httpx instead of sync requests |
| `notifications.py` email | `observatory/outputs/email.py` | Port: Jinja2 template for HTML body |
| `sheets.py` | `observatory/outputs/sheets.py` | Port: connection caching preserved |
| `db.py` dedup logic | Removed | ChromaDB handles deduplication |
| `db.py` run_metadata | `observatory/storage/state.py` | Port: lightweight SQLite for pipeline state only |
| `main.py` pipeline logic | `observatory/pipeline.py` | Rewrite: async pipeline orchestrator |
| `main.py` CLI | `observatory/cli.py` | Rewrite: proper CLI entry point |
| `user_profile.txt` | `config/profiles/user_profile.txt` | Move |

## New Files

```
config/sources/wordpress_sites.yaml              # WordPress site configurations
config/profiles/user_profile.txt                  # User profile for LLM context

observatory/intelligence/__init__.py              # (already exists, empty)
observatory/intelligence/evaluator.py             # LLM evaluation with provider chain

observatory/collectors/wordpress.py               # WordPress REST API collector
observatory/collectors/playwright_collector.py    # Browser-based collector (optional)

observatory/outputs/telegram.py                   # Telegram real-time alerts
observatory/outputs/email.py                      # Weekly email digest
observatory/outputs/sheets.py                     # Google Sheets logging
observatory/outputs/templates/weekly_digest.html  # Jinja2 email template

observatory/storage/state.py                      # SQLite for pipeline run metadata

observatory/pipeline.py                           # Pipeline orchestration
observatory/cli.py                                # CLI entry point
```

## Modified Files

```
config/settings.py                    # New settings for Sheets, profile path, Ollama model, WP config
observatory/app.py                    # New endpoints: /api/pipeline/run, /api/pipeline/status
observatory/storage/models.py         # Add EvaluationResult model
observatory/storage/chromadb_store.py # Add update_item_evaluation(), url_exists()
observatory/processing/deduplicator.py # Add URL hash check before semantic check
pyproject.toml                        # New dependencies
docker-compose.yml                    # Credentials volume mount
.env.example                          # New env vars
```

## Design Decisions

### D1: Dual deduplication (URL hash + semantic similarity)

The scrapper uses SHA256 URL hash (O(1), exact match). The observatory uses ChromaDB cosine distance (catches near-duplicates across sites). Both have value.

**Approach:** Check URL hash first (fast reject for re-scrapes, the 90% case), then check semantic similarity for genuinely new URLs (catches the same scholarship posted on multiple sites).

```python
def is_duplicate(item: CollectedItem) -> tuple[bool, str | None]:
    if chromadb_store.url_exists(item.url):
        return True, item.url  # exact URL match
    cleaned = clean_for_embedding(item.raw_text)
    distance, metadata = chromadb_store.find_nearest(cleaned)
    if distance is not None and distance < settings.dedup_distance_threshold:
        return True, metadata.get("url", "")  # semantic near-duplicate
    return False, None
```

### D2: LLM provider chain — Ollama first, cloud fallback

Priority order: Ollama → OpenAI → Gemini. Each provider implements a common interface. The evaluator checks Ollama health first; if reachable, uses it. Otherwise falls through to cloud APIs based on configured API keys.

```python
async def get_llm_provider() -> BaseLLMProvider:
    if await check_ollama():
        return OllamaProvider(model=settings.ollama_model)
    if settings.openai_api_key:
        return OpenAIProvider(model="gpt-4o-mini")
    if settings.gemini_api_key:
        return GeminiProvider(model="gemini-1.5-flash")
    raise NoProviderAvailableError("No LLM provider reachable")
```

**Ollama model:** `llama3.1:8b` (configurable via `OLLAMA_MODEL` env var).

### D3: WordPress collector config-driven via YAML

Instead of one function per WordPress site, a single `WordPressCollector` reads site configs from `config/sources/wordpress_sites.yaml`. Adding a new site = one YAML entry, zero code changes.

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

### D4: Pipeline state in SQLite, items in ChromaDB

ChromaDB stores all opportunity items with full metadata (score, category, summary, reasoning). SQLite (`state.db`) only tracks lightweight pipeline state: last weekly email timestamp, last pipeline run time. ChromaDB is not designed for simple key-value state tracking.

### D5: Async throughout

The observatory is async (FastAPI + httpx). All migrated code uses `async`/`await`:
- WordPress collector: `httpx.AsyncClient` replaces sync `requests`
- Telegram output: `httpx.AsyncClient` replaces sync `requests`
- Playwright collector: sync Playwright runs via `asyncio.to_thread()` since Playwright is inherently synchronous
- Email/Sheets: sync operations wrapped in `asyncio.to_thread()` (smtplib and gspread are sync)

### D6: Pipeline orchestrator as the single entry point

`pipeline.py` encapsulates the full collect→dedupe→evaluate→store→notify flow. It can be triggered from:
1. **CLI:** `observatory pipeline run --http-only`
2. **API:** `POST /api/pipeline/run?http_only=true`
3. **External:** n8n webhook calls the API endpoint on a cron schedule

The pipeline returns a structured result (items collected, new items, evaluations, notifications sent) for observability.

## Bug Fixes Included in Migration

### B1: Category not persisted after evaluation
**Root cause:** Old code inserts to DB with `category="general"` BEFORE evaluation, then never updates category after LLM returns it.
**Fix:** Pipeline evaluates first, then stores the fully evaluated item (including category) in a single ChromaDB upsert.

### B2: Weekly email timing
**Root cause:** Email only marks as sent on successful send; failed sends don't record the attempt, causing stale retry loops.
**Fix:** `state.py` tracks both `last_weekly_email_attempt` and `last_weekly_email_success`. The 7-day gate checks success, but a failed attempt within 1 hour suppresses retries.

### B3: Sheets reconnection loop
**Root cause:** No retry limit on `gspread.exceptions.APIError` catch — could theoretically loop forever.
**Fix:** Single retry on API error. If reconnection also fails, log and continue.

## Dependencies

Added to `pyproject.toml` core dependencies:
```
langchain-core>=0.3.0
langchain-openai>=0.1.1
langchain-google-genai>=1.0.2
langchain-ollama>=0.3.0
openai>=1.14.2
google-generativeai>=0.4.1
```

Added to `[project.optional-dependencies]`:
```toml
notifications = [
    "requests>=2.31.0",
    "gspread>=6.0.2",
    "oauth2client>=4.1.3",
]
scraping = [
    "playwright>=1.42.0",
    "beautifulsoup4>=4.12.0",
]
```

## Settings Additions

New fields in `config/settings.py`:
```python
google_sheet_id: str = ""
google_credentials_path: Path = Path("credentials.json")
user_profile_path: Path = Path("config/profiles/user_profile.txt")
wordpress_config_path: Path = Path("config/sources/wordpress_sites.yaml")
ollama_model: str = "llama3.1:8b"
state_db_path: Path = Path("data/state.db")
wp_default_keywords: list[str] = ["artificial intelligence", "data science", "education technology", "scholarship PhD", "fellowship AI", "remote AI jobs"]
wp_max_results_per_site: int = 10
wp_request_delay_min: float = 1.0
wp_request_delay_max: float = 2.5
high_affinity_threshold: int = 8
weekly_email_interval_days: int = 7
```

## CLI Interface

```bash
observatory pipeline run                              # all sources
observatory pipeline run --http-only                   # skip Playwright
observatory pipeline run --sources rss,wordpress       # specific collector types
observatory pipeline run --sources wordpress --keywords "AI,PhD"
observatory pipeline run --collectors globalsouth,rss   # granular source selection
```

## API Interface

```
POST /api/pipeline/run?http_only=true&keywords=AI,PhD  # trigger pipeline
GET  /api/pipeline/status                               # last run info
POST /api/collect/trigger?source=rss                    # existing: RSS only
POST /api/collect/trigger?source=wordpress              # new: WordPress only
GET  /api/search?q=AI+education&limit=10                # existing: semantic search
GET  /api/items/recent?since_hours=24&min_affinity=8    # existing: recent items
```

## Docker Changes

```yaml
# docker-compose.yml additions
services:
  observatory:
    volumes:
      - observatory-data:/data          # existing
      - ${OBSIDIAN_VAULT_PATH:-./vault}:/vault  # existing
      - ./credentials.json:/app/credentials.json:ro  # new: Google Sheets
      - ./config/profiles/user_profile.txt:/app/config/profiles/user_profile.txt:ro  # new
```

## Post-Migration

After confirming digital-observatory works end-to-end:
1. Archive educational-ops-scrapper on GitHub (mark as archived)
2. Update educational-ops-scrapper README to point to digital-observatory
3. Delete local `scraper_cache.db` (data migrated to ChromaDB)
