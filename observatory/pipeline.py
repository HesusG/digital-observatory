import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from config.settings import settings
from observatory.collectors.rss import RSSCollector
from observatory.collectors.wordpress import WordPressCollector
from observatory.intelligence.evaluator import evaluate_opportunity
from observatory.intelligence.ai_evaluator import evaluate_ai_signal
from observatory.processing.deduplicator import is_duplicate
from observatory.processing.embedder import clean_for_embedding
from observatory.storage import chromadb_store
from observatory.storage.models import CollectedItem
from observatory.storage.state import PipelineState
from observatory.outputs.telegram import send_telegram_alert
from observatory.outputs.email import send_weekly_email
from observatory.outputs.sheets import SheetsOutput
from observatory.outputs.vault import write_article_drafts
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
    articles_drafted: int = 0
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
            kind=item.kind,
            source_group=item.source_group,
            lang_hint=item.lang_hint,
        )

        if item.kind == "article":
            await _process_article(item, result)
            continue

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


async def _process_article(item: CollectedItem, result: PipelineResult) -> None:
    """Article kind: teacher-lens AI evaluator, then vault drafts. Never touches
    the opportunity Telegram channel or the opportunities Sheets log."""
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

    if evaluation.teacher_relevance >= settings.ai_article_min_relevance:
        written = await write_article_drafts(item, evaluation)
        result.articles_drafted += len(written)


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
    try:
        recent = chromadb_store.get_recent_items(since=since)
    except Exception as exc:
        logger.warning(f"Could not fetch recent items for weekly email: {exc}")
        return

    if not recent:
        return

    items = []
    for r in recent:
        meta = r.get("metadata", {})
        # Articles belong to the marketing pipeline, not the opportunity digest.
        if meta.get("kind") == "article":
            continue
        items.append({
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "category": meta.get("category", "general"),
            "score": int(meta.get("affinity_score", 0) or 0),
            "summary": meta.get("summary", "") or "",
            "reasoning": meta.get("reasoning", "") or "",
        })

    sent = await send_weekly_email(items)
    if sent:
        state.mark_weekly_email_sent()
        metrics.notifications_sent.labels(channel="email").inc()
