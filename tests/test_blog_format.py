from observatory.intelligence.drafter import PLATFORM_PROMPTS, build_platform_prompt


def test_blog_platform_registered_and_long_form():
    assert "blog" in PLATFORM_PROMPTS
    # blog is long-form: no hard char cap
    assert PLATFORM_PROMPTS["blog"]["limit_chars"] == 0


def test_blog_prompt_mentions_long_form():
    p = build_platform_prompt(
        platform="blog", lang="es", hook="h", summary="s", angles=[], include_course_cta=False
    )
    assert "blog" in p.lower()
