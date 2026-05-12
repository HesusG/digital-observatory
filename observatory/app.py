import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from config.settings import settings
from observatory.collectors.rss import RSSCollector
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
):
    since = datetime.utcnow() - timedelta(hours=since_hours)
    items = chromadb_store.get_recent_items(since=since, min_affinity=min_affinity)
    return {"count": len(items), "items": items}


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
