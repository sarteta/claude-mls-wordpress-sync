"""Tiny atomic JSON state store keyed by listing_key → content_hash.

File format is deliberately boring (JSON) so it can be inspected, version-
controlled in emergencies, or migrated to sqlite/redis later without pain.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import Listing


def content_hash(listing: Listing) -> str:
    """Stable hash of the raw listing payload.

    Sorting keys is what makes this deterministic — without it the same
    listing would get a different hash every fetch.
    """
    payload = json.dumps(listing.raw, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, str] | None = None

    def load(self) -> dict[str, str]:
        if self._cache is not None:
            return self._cache
        if not self.path.exists():
            self._cache = {}
            return self._cache
        with self.path.open("r", encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)
        self._cache = dict(data.get("listings", {}))
        return self._cache

    def save_atomic(self, state: dict[str, str]) -> None:
        """Write via temp file + os.replace so an interrupted sync never leaves
        a half-written state.json that would mis-diff the next run."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(self.path.parent),
            prefix=".state-",
            suffix=".tmp",
        )
        try:
            json.dump({"version": 1, "listings": state}, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, self.path)
        except Exception:
            tmp.close()
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise
        self._cache = dict(state)
