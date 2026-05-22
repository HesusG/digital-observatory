import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Body, FastAPI, Query
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from config.settings import settings
from observatory.collectors.rss import RSSCollector
from observatory.intelligence.drafter import draft_for_platforms
from observatory.pipeline import run_pipeline, PipelineResult
from observatory.storage import chromadb_store
from observatory.storage.state import PipelineState
from observatory.processing.deduplicator import is_duplicate
from observatory.processing.embedder import clean_for_embedding
from observatory.monitoring import metrics
from observatory.monitoring.health import check_chromadb, check_ollama

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Digital Observatory starting up...")
    yield
    logger.info("Digital Observatory shutting down...")


app = FastAPI(title="Digital Observatory", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    chroma_ok = await check_chromadb()
    return JSONResponse(
        status_code=200 if chroma_ok else 503,
        content={"status": "healthy" if chroma_ok else "degraded", "chromadb": chroma_ok},
    )


@app.get("/readyz")
async def readyz():
    chroma_ok = await check_chromadb()
    ollama_ok = await check_ollama()
    metrics.ollama_available.set(1 if ollama_ok else 0)
    ready = chroma_ok
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"ready": ready, "chromadb": chroma_ok, "ollama": ollama_ok},
    )


@app.get("/metrics")
async def prometheus_metrics():
    try:
        metrics.chromadb_items_count.set(chromadb_store.get_item_count())
    except Exception:
        pass
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/collect/trigger")
async def trigger_collection(source: str = Query(default="rss")):
    """Triggered by n8n to run a specific collector."""
    if source == "rss":
        collector = RSSCollector()
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
                kind=item.kind,
                source_group=item.source_group,
                lang_hint=item.lang_hint,
            )
            new_count += 1

        return {
            "status": "ok",
            "source": source,
            "collected": len(items),
            "new": new_count,
            "duplicates": dup_count,
        }

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
                kind=item.kind,
                source_group=item.source_group,
                lang_hint=item.lang_hint,
            )
            new_count += 1

        return {
            "status": "ok",
            "source": source,
            "collected": len(items),
            "new": new_count,
            "duplicates": dup_count,
        }

    return JSONResponse(status_code=400, content={"error": f"Unknown source: {source}"})


@app.get("/api/search")
async def semantic_search(q: str = Query(...), limit: int = Query(default=10)):
    """Semantic search over all collected items."""
    results = chromadb_store.query_similar(q, n_results=limit)
    return {"query": q, "results": results}


@app.get("/api/items/recent")
async def recent_items(
    since_hours: int = Query(default=24),
    min_affinity: int = Query(default=0),
    kind: str | None = Query(default=None, pattern="^(opportunity|article)$"),
    lang: str | None = Query(default=None, pattern="^(es|en)$"),
    min_relevance: int = Query(default=0),
):
    since = datetime.utcnow() - timedelta(hours=since_hours)
    items = chromadb_store.get_recent_items(
        since=since,
        min_affinity=min_affinity,
        kind=kind,
        lang=lang,
        min_relevance=min_relevance,
    )
    return {"count": len(items), "items": items}


@app.post("/api/content/draft")
async def content_draft(payload: dict = Body(...)):
    """Generate per-platform per-language draft text for an already-stored
    article. n8n's marketing-team workflow calls this."""
    url = payload.get("url", "")
    if not url:
        return JSONResponse(status_code=400, content={"error": "url required"})

    item = chromadb_store.get_item_by_url(url)
    if not item:
        return JSONResponse(status_code=404, content={"error": f"unknown url: {url}"})

    meta = item.get("metadata", {})
    if meta.get("kind") != "article":
        return JSONResponse(
            status_code=400,
            content={"error": "drafter only handles kind=article"},
        )

    platforms = payload.get("platforms") or settings.ai_default_platforms
    lang = payload.get("lang") or "en"
    if lang not in settings.ai_supported_langs:
        return JSONResponse(
            status_code=400,
            content={"error": f"unsupported lang: {lang}"},
        )

    include_course_cta = bool(payload.get("include_course_cta", False))
    tone = str(payload.get("tone", ""))

    # post_angles came from the AI evaluator and was stored as JSON-ish; we
    # accept a fallback if the metadata only kept tag-lists.
    angles_meta = meta.get("post_angles_json") or ""
    angles: list[dict] = []
    if angles_meta:
        try:
            import json as _json
            angles = _json.loads(angles_meta)
        except Exception:
            angles = []

    drafts = await draft_for_platforms(
        hook=meta.get("one_line_hook", "") or meta.get("title", ""),
        summary=meta.get("summary", ""),
        angles=angles,
        platforms=list(platforms),
        lang=lang,
        include_course_cta=include_course_cta,
        tone=tone,
    )

    return {
        "url": url,
        "lang": lang,
        "platforms": list(platforms),
        "drafts": drafts,
    }


@app.post("/api/items/skip")
async def skip_item(item_id: str = Query(...), reason: str = Query(default="user-skip")):
    ok = chromadb_store.mark_item_skipped(item_id, reason=reason)
    return JSONResponse(
        status_code=200 if ok else 404,
        content={"status": "ok" if ok else "not-found", "item_id": item_id},
    )


@app.get("/api/stats")
async def stats():
    return {
        "total_items": chromadb_store.get_item_count(),
        "chromadb_host": f"{settings.chroma_host}:{settings.chroma_port}",
    }


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
        "articles_drafted": result.articles_drafted,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)
