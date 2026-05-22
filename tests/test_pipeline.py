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


@pytest.mark.asyncio
async def test_pipeline_article_path_invokes_edu_per_draft(monkeypatch):
    """When an article passes Tess, every Carla draft must go through Edu."""
    from observatory import pipeline
    from observatory.storage.models import CollectedItem

    edu_calls: list[dict] = []
    verdict_calls: list[dict] = []

    eval_obj = type("E", (), dict(
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

    monkeypatch.setattr(pipeline, "evaluate_ai_signal", AsyncMock(return_value=eval_obj))
    monkeypatch.setattr(pipeline, "write_article_drafts", AsyncMock(return_value=[]))
    monkeypatch.setattr(pipeline.chromadb_store, "update_item_ai_evaluation", lambda **kw: None)

    async def fake_carla(item, evaluation):
        return [
            {"id": "draft-x", "platform": "x", "lang": "en", "content": "x text"},
            {"id": "draft-li", "platform": "linkedin", "lang": "en", "content": "li text"},
        ]

    async def fake_edu(**kwargs):
        edu_calls.append(kwargs)
        return type("V", (), {"verdict": "approved-for-review", "reasoning": "ok",
                              "fail_categories": [], "hand_back": ""})()

    monkeypatch.setattr(pipeline, "carla_draft_for_item", fake_carla)
    monkeypatch.setattr(pipeline, "edu_review_draft", fake_edu)
    monkeypatch.setattr(
        pipeline, "drafts_update_verdict",
        lambda **kw: verdict_calls.append(kw),
    )

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
    assert len(verdict_calls) == 2
