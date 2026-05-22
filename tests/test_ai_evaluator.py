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

    assert "You are Tess" in prompt
    assert "teacher_relevance" in prompt
    assert "skip_reason" in prompt
    assert "Course owner: Hesus" in prompt
    assert "Article body" in prompt


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
