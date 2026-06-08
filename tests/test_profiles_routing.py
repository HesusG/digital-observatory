from observatory.profiles.loader import load_profiles, pick_profile


def test_ai_news_routes_to_tech_reviewer():
    profiles = load_profiles()
    chosen = pick_profile("ai_news", profiles)
    assert chosen is not None
    assert chosen.id == "tech-reviewer"


def test_edtech_routes_to_tech_educator():
    profiles = load_profiles()
    chosen = pick_profile("edtech", profiles)
    assert chosen is not None
    assert chosen.id == "tech-educator"


def test_opportunities_routes_to_influencer():
    profiles = load_profiles()
    chosen = pick_profile("opportunities", profiles)
    assert chosen is not None
    assert chosen.id == "linkedin-influencer"


def test_unknown_source_group_has_no_owner():
    profiles = load_profiles()
    assert pick_profile("totally_unknown_group", profiles) is None


def test_inactive_profile_never_selected():
    # Build an isolated copy so we don't mutate the cached singletons.
    profiles = {k: v.model_copy(deep=True) for k, v in load_profiles().items()}
    profiles["tech-reviewer"].active = False
    chosen = pick_profile("ai_news", profiles)
    # With reviewer inactive, ai_news falls to next-highest weight (educator 0.4).
    assert chosen is not None
    assert chosen.id != "tech-reviewer"
