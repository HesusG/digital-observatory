from pathlib import Path

import pytest

from observatory.profiles.loader import (
    Account,
    Book,
    Profile,
    load_accounts,
    load_books,
    load_profiles,
    resolve_account,
)


def test_load_profiles_returns_all_four():
    profiles = load_profiles()
    assert set(profiles) == {
        "tech-reviewer",
        "tech-educator",
        "linkedin-influencer",
        "promo",
    }
    reviewer = profiles["tech-reviewer"]
    assert isinstance(reviewer, Profile)
    assert reviewer.source_weights["ai_news"] == 1.5
    assert reviewer.min_score == 6
    assert reviewer.outputs[0].format == "thread"
    assert reviewer.outputs[0].account == "x"
    assert "primera persona" in reviewer.voice


def test_load_accounts_and_resolve():
    accounts = load_accounts()
    assert isinstance(accounts["bluesky"], Account)
    assert accounts["bluesky"].platform == "bluesky"
    resolved = resolve_account("bluesky")
    assert resolved.platform == "bluesky"


def test_resolve_unknown_account_returns_none():
    assert resolve_account("does-not-exist") is None


def test_load_books_seeded():
    books = load_books()
    ids = {b.id for b in books}
    assert "ser-tutor" in ids
    assert "ia-para-docentes" in ids
    assert all(isinstance(b, Book) for b in books)


def test_profile_referencing_unknown_account_fails(tmp_path, monkeypatch):
    """Loader must fail-fast if a profile output names an account alias that
    does not exist in accounts.yaml."""
    load_profiles.cache_clear()
    load_accounts.cache_clear()
    brands = tmp_path / "brands"
    brands.mkdir()
    (brands / "bad.yaml").write_text(
        "id: bad\ndisplay_name: Bad\nsource_weights: {}\n"
        "voice: x\noutputs:\n  - {format: thread, account: nope}\n"
        "min_score: 1\nactive: true\n",
        encoding="utf-8",
    )
    (tmp_path / "accounts.yaml").write_text(
        "x: {platform: x, postiz_integration_id: ''}\n", encoding="utf-8"
    )
    (tmp_path / "books.yaml").write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr("observatory.profiles.loader.PROFILES_DIR", tmp_path)
    with pytest.raises(ValueError, match="unknown account"):
        load_profiles()
    # Restore caches for other tests.
    load_profiles.cache_clear()
    load_accounts.cache_clear()
