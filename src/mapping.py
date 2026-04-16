"""YAML-driven mapping from MLS raw payload -> WordPress post body."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Listing


class FieldMapping:
    def __init__(self, config_path: str | Path) -> None:
        with open(config_path, "r", encoding="utf-8") as fh:
            self._cfg: dict[str, Any] = yaml.safe_load(fh)

    def mls_status_to_wp_status(self, mls_status: str | None) -> str:
        if not mls_status:
            return "draft"
        if mls_status in self._cfg.get("publish_statuses", []):
            return "publish"
        if mls_status in self._cfg.get("draft_statuses", []):
            return "draft"
        return "draft"

    def to_wp_payload(self, listing: Listing) -> dict[str, Any]:
        raw = listing.raw
        post_fields = self._cfg.get("post_fields", {})
        meta_fields = self._cfg.get("meta_fields", {})

        payload: dict[str, Any] = {
            "title": raw.get(post_fields.get("title", "ListingKey")) or listing.listing_key,
            "content": raw.get(post_fields.get("content", "PublicRemarks")) or "",
            "status": self.mls_status_to_wp_status(raw.get("MlsStatus")),
            "meta": {
                wp_key: raw.get(mls_key) for wp_key, mls_key in meta_fields.items()
            },
        }
        # Drop meta keys that are None to keep payload clean.
        payload["meta"] = {k: v for k, v in payload["meta"].items() if v is not None}
        return payload
