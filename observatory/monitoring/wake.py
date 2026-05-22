"""Wake-on-LAN orchestration for the d3r-ser Ollama host.

The observatory itself can't broadcast a magic packet (it runs in a bridged
container). Instead it talks to a host-networking sidecar (see
deploy/wol-service/) and then polls Ollama until it responds.
"""
import asyncio
import logging
import time

import httpx

from config.settings import settings
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)


async def _send_wol_packet() -> dict:
    """Calls the WOL sidecar. Returns its JSON response or raises."""
    url = f"{settings.wol_service_url.rstrip('/')}/wake"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(url)
        r.raise_for_status()
        return r.json()


async def wake_ollama_if_needed() -> dict:
    """Ensure Ollama is reachable. Returns a status dict.

    - If Ollama already responds, returns immediately (action=none).
    - Otherwise sends WOL via the sidecar and polls until Ollama answers or
      wol_wait_max_seconds elapses.
    """
    started = time.monotonic()

    if await check_ollama():
        return {
            "status": "ok",
            "action": "none",
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }

    logger.info("Ollama unreachable; calling WOL sidecar at %s", settings.wol_service_url)
    try:
        wol_response = await _send_wol_packet()
    except (httpx.HTTPError, OSError) as e:
        logger.error("WOL sidecar call failed: %s", e)
        return {
            "status": "wol-sidecar-unreachable",
            "action": "tried-wol",
            "error": str(e),
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }

    deadline = started + settings.wol_wait_max_seconds
    while time.monotonic() < deadline:
        await asyncio.sleep(settings.wol_poll_interval_seconds)
        if await check_ollama():
            elapsed = round(time.monotonic() - started, 2)
            logger.info("Ollama responded %.1fs after WOL", elapsed)
            return {
                "status": "ok",
                "action": "woke",
                "wol": wol_response,
                "elapsed_seconds": elapsed,
            }

    elapsed = round(time.monotonic() - started, 2)
    logger.error("Ollama still unreachable after %.1fs", elapsed)
    return {
        "status": "timeout",
        "action": "woke",
        "wol": wol_response,
        "elapsed_seconds": elapsed,
    }
