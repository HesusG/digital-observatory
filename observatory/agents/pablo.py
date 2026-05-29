"""Pablo — Publisher agent. No LLM. Relays approved drafts to Postiz.

Slice 1: only Bluesky is wired (we connect that account first). X and
LinkedIn integration IDs land in Slice 6 / Phase 7 after their respective
developer accounts clear.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from config.settings import settings
from observatory.storage import drafts_store

logger = logging.getLogger(__name__)


PLATFORM_INTEGRATION_ENV = {
    "bluesky": "postiz_bluesky_integration_id",
    # "x":        "postiz_x_integration_id",        # Slice 6
    # "linkedin": "postiz_linkedin_integration_id", # Phase 7
}


@dataclass
class PabloResult:
    ok: bool
    postiz_post_id: Optional[str] = None
    error: Optional[str] = None


async def publish_draft(draft_id: str) -> PabloResult:
    draft = drafts_store.get_draft(draft_id)
    if not draft:
        return PabloResult(ok=False, error=f"draft not found: {draft_id}")

    meta = draft["metadata"]
    platform = meta.get("platform", "")
    content = draft["document"]

    integration_attr = PLATFORM_INTEGRATION_ENV.get(platform)
    if integration_attr is None:
        return PabloResult(ok=False, error=f"unsupported platform in Slice 1: {platform!r}")

    integration_id = getattr(settings, integration_attr, "")
    if not integration_id or not settings.postiz_api_key:
        return PabloResult(ok=False, error="Postiz not configured (api key / integration id missing)")

    # Postiz public API (v2.11.x) requires date + tags, and each value entry
    # must carry an image array (empty for text-only posts).
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = {
        "type": "now",
        "shortLink": False,
        "date": now_iso,
        "tags": [],
        "posts": [
            {
                "integration": {"id": integration_id},
                "value": [{"content": content, "image": []}],
            }
        ],
    }

    url = settings.postiz_base_url.rstrip("/") + "/api/public/v1/posts"
    headers = {
        # Postiz public API expects the raw API key (no "Bearer " prefix).
        "Authorization": settings.postiz_api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error("Pablo: Postiz call failed: %s", e)
        return PabloResult(ok=False, error=f"postiz request failed: {e}")
    except Exception as e:
        logger.error("Pablo: unexpected: %s", e)
        return PabloResult(ok=False, error=f"unexpected: {e}")

    # Postiz v2.11.x returns a list: [{"postId": "...", "integration": "..."}].
    # Older shapes used {"posts": [{"id": "..."}]}; handle both defensively.
    postiz_post_id = None
    if isinstance(data, list) and data:
        postiz_post_id = data[0].get("postId") or data[0].get("id")
    elif isinstance(data, dict):
        posts = data.get("posts") or []
        postiz_post_id = posts[0].get("id") if posts else None
    if not postiz_post_id:
        return PabloResult(ok=False, error=f"postiz returned no post id: {data}")

    drafts_store.mark_published(
        draft_id=draft_id,
        postiz_post_id=postiz_post_id,
        scheduled_at="",
    )
    return PabloResult(ok=True, postiz_post_id=postiz_post_id)
