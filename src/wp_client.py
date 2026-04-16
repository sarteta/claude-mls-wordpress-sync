"""WordPress REST client.

- Auth: app passwords (HTTPS basic) — don't use real admin passwords.
- Finds existing post by meta key `_mls_listing_key` so our engine can PATCH
  instead of POST-duplicate on every run.
- Dead-letter write on permanent failures so a bad payload doesn't stall
  the whole batch.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

DEAD_LETTER_PATH = Path("logs/dead-letter.jsonl")


class WPClient:
    def __init__(
        self,
        base_url: str,
        user: str,
        app_password: str,
        post_type: str = "listing",
        concurrency: int = 4,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.post_type = post_type
        self._auth = (user, app_password)
        self._sem = asyncio.Semaphore(concurrency)
        self.timeout = timeout

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _find_by_listing_key(
        self, client: httpx.AsyncClient, listing_key: str
    ) -> int | None:
        # We index on meta_key=_mls_listing_key on the WP side.
        r = await client.get(
            f"{self.base_url}/wp-json/wp/v2/{self.post_type}",
            params={
                "meta_key": "_mls_listing_key",
                "meta_value": listing_key,
                "per_page": 1,
                "_fields": "id",
            },
        )
        r.raise_for_status()
        data = r.json()
        if data:
            return int(data[0]["id"])
        return None

    async def upsert(self, listing_key: str, payload: dict[str, Any]) -> int | None:
        async with self._sem:
            async with httpx.AsyncClient(
                auth=self._auth, timeout=self.timeout
            ) as client:
                try:
                    post_id = await self._find_by_listing_key(client, listing_key)
                    # Stamp the meta key used for future lookups.
                    payload = {**payload}
                    payload.setdefault("meta", {})
                    payload["meta"]["_mls_listing_key"] = listing_key

                    if post_id:
                        url = f"{self.base_url}/wp-json/wp/v2/{self.post_type}/{post_id}"
                        r = await client.post(url, json=payload)
                    else:
                        url = f"{self.base_url}/wp-json/wp/v2/{self.post_type}"
                        r = await client.post(url, json=payload)
                    r.raise_for_status()
                    return int(r.json()["id"])
                except Exception as exc:
                    _to_dead_letter(listing_key, payload, exc)
                    return None

    async def mark_draft(self, listing_key: str) -> bool:
        async with self._sem:
            async with httpx.AsyncClient(
                auth=self._auth, timeout=self.timeout
            ) as client:
                try:
                    post_id = await self._find_by_listing_key(client, listing_key)
                    if not post_id:
                        return False
                    r = await client.post(
                        f"{self.base_url}/wp-json/wp/v2/{self.post_type}/{post_id}",
                        json={"status": "draft"},
                    )
                    r.raise_for_status()
                    return True
                except Exception as exc:
                    _to_dead_letter(listing_key, {"action": "mark_draft"}, exc)
                    return False


def _to_dead_letter(listing_key: str, payload: dict[str, Any], exc: BaseException) -> None:
    DEAD_LETTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "listing_key": listing_key,
        "error": repr(exc),
        "payload": payload,
    }
    with DEAD_LETTER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
    logger.error("dead-letter for %s: %s", listing_key, exc)
