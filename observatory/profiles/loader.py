"""Loader for content profiles, account aliases, and the book catalog.

A Profile is a content "mode" (not a brand, not a user): it declares which
source_groups it cares about (source_weights), the voice Carla adopts for it,
and which output formats go to which account alias. Routing (pick_profile) is a
deterministic pure function over source_weights — no LLM involved.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# observatory/profiles/loader.py -> parents[2] == repo root
PROFILES_DIR = Path(__file__).resolve().parents[2] / "config" / "profiles"

# Profile output formats -> drafter PLATFORM_PROMPTS keys. Formats not present
# here are not yet supported by the drafter (subsystem C) and are skipped.
FORMAT_TO_PLATFORM = {
    "thread": "x",
    "bluesky": "bluesky",
    "linkedin": "linkedin",
    "blog": "blog",
    # YouTube scripts (subsistema C) — map to themselves; the drafter knows them.
    "youtube_long": "youtube_long",
    "youtube_short": "youtube_short",
}


class ProfileOutput(BaseModel):
    format: str
    account: str


class Profile(BaseModel):
    id: str
    display_name: str = ""
    emoji: str = ""
    source_weights: dict[str, float] = Field(default_factory=dict)
    voice: str = ""
    outputs: list[ProfileOutput] = Field(default_factory=list)
    min_score: int = 6
    active: bool = True


class Account(BaseModel):
    platform: str
    postiz_integration_id: str = ""
    destination: str = ""


class Book(BaseModel):
    id: str
    title: str
    audience: str = ""
    status: str = ""
    themes: list[str] = Field(default_factory=list)
    cta_url: str = ""


@lru_cache(maxsize=1)
def load_accounts() -> dict[str, Account]:
    path = PROFILES_DIR / "accounts.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {alias: Account(**cfg) for alias, cfg in raw.items()}


@lru_cache(maxsize=1)
def load_profiles() -> dict[str, Profile]:
    accounts = load_accounts()
    brands_dir = PROFILES_DIR / "brands"
    profiles: dict[str, Profile] = {}
    for path in sorted(brands_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        profile = Profile(**data)
        for out in profile.outputs:
            if out.account not in accounts:
                raise ValueError(
                    f"profile '{profile.id}' references unknown account "
                    f"'{out.account}' (not in accounts.yaml)"
                )
        profiles[profile.id] = profile
    return profiles


@lru_cache(maxsize=1)
def load_books() -> list[Book]:
    path = PROFILES_DIR / "books.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [Book(**b) for b in raw]


def resolve_account(alias: str) -> Optional[Account]:
    return load_accounts().get(alias)


def pick_profile(
    source_group: str, profiles: dict[str, Profile]
) -> Optional[Profile]:
    """Return the active profile with the highest source_weight for this
    source_group, or None if no active profile weights it above zero.

    Deterministic: ties are broken by profile id (sorted) so the same input
    always yields the same owner.
    """
    candidates = [
        (p.source_weights.get(source_group, 0.0), p.id, p)
        for p in profiles.values()
        if p.active
    ]
    candidates = [c for c in candidates if c[0] > 0.0]
    if not candidates:
        return None
    # Highest weight wins; tie-break by id ascending.
    candidates.sort(key=lambda c: (-c[0], c[1]))
    return candidates[0][2]
