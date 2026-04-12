"""Domain models — intentionally thin, work across all MLS vendors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Listing:
    """Normalized listing as produced by any MLSAdapter."""

    listing_key: str                   # stable primary key from MLS
    modification_ts: str                # ISO-8601; used for incremental fetch
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.listing_key:
            raise ValueError("listing_key is required")


@dataclass
class DiffResult:
    created: list[Listing] = field(default_factory=list)
    updated: list[Listing] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)   # listing_keys
    removed: list[str] = field(default_factory=list)     # listing_keys

    @property
    def summary(self) -> dict[str, int]:
        return {
            "created": len(self.created),
            "updated": len(self.updated),
            "unchanged": len(self.unchanged),
            "removed": len(self.removed),
        }

    @property
    def has_writes(self) -> bool:
        return bool(self.created or self.updated or self.removed)
