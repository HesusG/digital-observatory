import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4

from config.settings import settings
from observatory.collectors.rss import RSSCollector
from observatory.collectors.wordpress import WordPressCollector
from observatory.intelligence.evaluator import evaluate_opportunity
from observatory.agents.edu import review_draft as edu_review_draft
from observatory.intelligence.ai_evaluator import evaluate_ai_signal
from observatory.storage import drafts_store
from observatory.storage import event_log
from observatory.storage.drafts_store import EduVerdict
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


EDU_EVENT = {
    EduVerdict.APPROVED_FOR_REVIEW: "edu.approved",
    EduVerdict.REVISE: "edu.revise",
    EduVerdict.REJECT: "edu.reject",
}


async def run_pipeline(
    enable_rss: bool = True,
    enable_wordpress: bool = True,
    enable_playwright: bool = False,
    enable_obsidian: bool = False,
    keywords: list[str] | None = None,
    source_filter: list[str] | None = None,
) -> PipelineResult:
    result = PipelineResult()
    run_id = uuid4().hex
    logger.info("Starting opportunity pipeline...")

    items = await _collect(
        enable_rss=enable_rss,
        enable_wordpress=enable_wordpress,
        enable_playwright=enable_playwright,
        enable_obsidian=enable_obsidian,
        keywords=keywords,
        source_filter=source_filter,
    )
    result.collected = len(items)
    logger.info(f"Collected {len(items)} items from all sources")

    sheets = SheetsOutput()

    for item in items:
        dup, dup_of = is_duplicate(item.raw_text, item.url, item.title)
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
            await _process_article(item, result, run_id=run_id)
            continue

        evaluation = await evaluate_opportunity(item.raw_text)

        if evaluation is None:
            result.eval_failures += 1
            metrics.llm_errors.labels(provider="unknown").inc()
            event_log.append_event(
                "tess", "tess.skipped",
                item_url=item.url, run_id=run_id,
                payload={"title": item.title, "skip_reason": "eval-failed"},
            )
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
            deadline=evaluation.deadline,
        )

        event_log.append_event(
            "tess", "tess.scored",
            item_url=item.url, run_id=run_id,
            payload={
                "title": item.title,
                "affinity_score": evaluation.affinity_score,
                "category": evaluation.category,
            },
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
                deadline=evaluation.deadline,
            )
            if sent:
                result.notifications_sent += 1
                metrics.notifications_sent.labels(channel="telegram").inc()

    await _maybe_send_daily_digest()
    await _maybe_notify_drafts_awaiting()
    await _maybe_send_weekly_email()

    result.finished_at = datetime.utcnow()
    logger.info(
        f"Pipeline complete: {result.collected} collected, {result.new_items} new, "
        f"{result.evaluated} evaluated, {result.high_affinity} high-affinity"
    )
    return result


async def _process_article(
    item: CollectedItem, result: PipelineResult, run_id: str | None = None
) -> None:
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

    event_log.append_event(
        "tess", "tess.scored",
        item_url=item.url, run_id=run_id,
        payload={
            "title": item.title,
            "teacher_relevance": evaluation.teacher_relevance,
            "audience_fit": evaluation.audience_fit,
            "lang_targets": evaluation.lang_targets,
            "suggested_platforms": evaluation.suggested_platforms,
            "skip_reason": evaluation.skip_reason or None,
        },
    )

    if evaluation.skip_reason:
        event_log.append_event(
            "tess", "tess.skipped",
            item_url=item.url, run_id=run_id,
            payload={"title": item.title, "skip_reason": evaluation.skip_reason},
        )
        return

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
            content = draft["content"]
            draft_text = content if isinstance(content, str) else "\n".join(content)
            verdict = await edu_review_draft(
                draft_text=draft_text,
                platform=draft["platform"],
                lang=draft["lang"],
                hook=evaluation.one_line_hook,
                summary=evaluation.summary,
                recent_posts=[],  # Slice 1: empty; Slice 2 will populate from ChromaDB
            )
            mapped = (
                EduVerdict(verdict.verdict)
                if verdict.verdict in {v.value for v in EduVerdict}
                else EduVerdict.REVISE
            )
            drafts_update_verdict(
                draft_id=draft["id"],
                verdict=mapped,
                reasoning=verdict.reasoning,
            )
            event_log.append_event(
                "edu", EDU_EVENT[mapped],
                item_url=item.url, draft_id=draft["id"],
                platform=draft["platform"], lang=draft["lang"], run_id=run_id,
                payload={
                    "verdict": verdict.verdict,
                    "reasoning": verdict.reasoning,
                    "fail_categories": getattr(verdict, "fail_categories", None),
                },
            )
            logger.info(
                "Edu %s draft %s (%s/%s): %s",
                verdict.verdict, draft["id"][:12], draft["platform"], draft["lang"],
                verdict.reasoning[:80],
            )
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


# ---- Indirection layer so tests can monkey-patch these entry points ----


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


def drafts_update_verdict(draft_id, verdict, reasoning):
    drafts_store.update_edu_verdict(
        draft_id=draft_id,
        verdict=verdict,
        reasoning=reasoning,
    )


async def _collect(
    enable_rss: bool,
    enable_wordpress: bool,
    enable_playwright: bool,
    keywords: list[str] | None,
    source_filter: list[str] | None,
    enable_obsidian: bool = False,
) -> list[CollectedItem]:
    items: list[CollectedItem] = []
    tasks = []

    if enable_rss:
        rss = RSSCollector()
        tasks.append(rss.collect())

    if enable_obsidian:
        from observatory.collectors.obsidian import ObsidianNotesCollector

        tasks.append(ObsidianNotesCollector().collect())

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


async def _maybe_send_daily_digest():
    from observatory.outputs.digest import send_daily_opportunity_digest

    state = PipelineState(settings.state_db_path)
    if not state.should_send_daily_digest():
        return

    since = datetime.utcnow() - timedelta(hours=24)
    try:
        recent = chromadb_store.get_recent_items(since=since, kind="opportunity")
    except Exception as exc:
        logger.warning(f"daily digest: recent fetch failed: {exc}")
        return

    items = [
        {
            "title": r.get("metadata", {}).get("title", ""),
            "url": r.get("metadata", {}).get("url", ""),
            "score": int(r.get("metadata", {}).get("affinity_score", 0) or 0),
        }
        for r in recent
    ]
    sent = await send_daily_opportunity_digest(items)
    if sent:
        metrics.notifications_sent.labels(channel="telegram").inc()
    # Mark the day done whether we sent or there was simply nothing to send, so
    # an empty day doesn't re-trigger on every later run. (A real send failure
    # returns False too, but the next scheduled run retries — acceptable.)
    eligible = [i for i in items if int(i.get("score", 0) or 0) >= settings.high_affinity_threshold]
    if sent or not eligible:
        state.mark_daily_digest_sent()


async def _maybe_notify_drafts_awaiting():
    """Ping Telegram when article drafts are sitting in 'awaiting-user'."""
    from observatory.outputs.digest import send_drafts_awaiting_notice
    from observatory.storage import drafts_store

    try:
        pending = drafts_store.list_drafts_by_status("awaiting-user", limit=100)
    except Exception as exc:
        logger.warning(f"drafts notice: list failed: {exc}")
        return

    state = PipelineState(settings.state_db_path)
    if not state.should_notify_drafts(len(pending)):
        return

    sent = await send_drafts_awaiting_notice(pending)
    if sent:
        state.mark_drafts_notified(len(pending))
        metrics.notifications_sent.labels(channel="telegram").inc()


async def _maybe_send_weekly_email():
    state = PipelineState(settings.state_db_path)
    if not state.should_send_weekly_email(interval_days=settings.weekly_email_interval_days):
        return

    since = datetime.utcnow() - timedelta(days=settings.weekly_email_interval_days)
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

    # Don't send a useless "0 opportunities" email when everything collected was
    # an article (filtered out above) or nothing scored.
    scored = [i for i in items if int(i.get("score", 0) or 0) > 0]
    if not scored:
        logger.info("Weekly email: no scored opportunities in window; skipping.")
        return

    sent = await send_weekly_email(items)
    if sent:
        state.mark_weekly_email_sent()
        metrics.notifications_sent.labels(channel="email").inc()
