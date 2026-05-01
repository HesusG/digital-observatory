import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


async def check_chromadb() -> bool:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1/heartbeat",
                timeout=5.0,
            )
            return r.status_code == 200
    except Exception:
        return False


async def check_ollama() -> bool:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
            return r.status_code == 200
    except Exception:
        return False
