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
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "affinity_score": 8,
        "is_free_or_funded": True,
        "category": "fellowship",
        "summary": "AI fellowship",
        "reasoning": "Good match",
    })
    mock_provider.ainvoke.return_value = mock_response
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
