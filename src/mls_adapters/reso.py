"""RESO Web API adapter (OData-ish).

Works against MLS providers that expose the standard RESO `/Property` endpoint:
Bridge Interactive, Trestle, MLSGrid, etc. all support this shape.

The interesting bits:
- Paginates with `$skip` + `$top`.
- Incremental fetch uses `$filter=ModificationTimestamp gt <iso>` so we don't
  refetch 10k listings every 15 minutes.
- Retries transient 5xx / 429 with exponential backoff via tenacity.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..models import Listing

logger = logging.getLogger(__name__)


class RESOAdapter:
    def __init__(
        self,
        base_url: str,
        access_token: str,
        page_size: int = 200,
        timeout: float = 30.0,
    ) -> None:
        if not base_url:
            raise ValueError("RESO base_url is required")
        if not access_token:
            raise ValueError("RESO access_token is required")
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        self.page_size = page_size
        self.timeout = timeout

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((httpx.HTTPError,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _get_page(
        self, client: httpx.AsyncClient, skip: int, since: str | None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "$top": self.page_size,
            "$skip": skip,
            "$orderby": "ModificationTimestamp asc",
        }
        if since:
            params["$filter"] = f"ModificationTimestamp gt {since}"
        r = await client.get(f"{self.base_url}/Property", params=params)
        r.raise_for_status()
        return r.json()

    async def fetch_all(self, since: str | None = None) -> list[Listing]:
        results: list[Listing] = []
        skip = 0
        async with httpx.AsyncClient(
            headers=self.headers, timeout=self.timeout
        ) as client:
            while True:
                payload = await self._get_page(client, skip=skip, since=since)
                batch = payload.get("value", [])
                if not batch:
                    break
                for raw in batch:
                    key = raw.get("ListingKey")
                    if not key:
                        logger.warning("skipping listing with missing ListingKey")
                        continue
                    results.append(
                        Listing(
                            listing_key=str(key),
                            modification_ts=str(raw.get("ModificationTimestamp", "")),
                            raw=raw,
                        )
                    )
                if len(batch) < self.page_size:
                    break
                skip += self.page_size
        logger.info("RESO: fetched %d listings (since=%s)", len(results), since)
        return results
