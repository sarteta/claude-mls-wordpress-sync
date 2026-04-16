"""MLS provider adapters. Add a new vendor by dropping a file here.

Each adapter must expose an async `fetch_all(since: str | None) -> list[Listing]`.
"""
from __future__ import annotations

from typing import Protocol

from ..models import Listing


class MLSAdapter(Protocol):
    async def fetch_all(self, since: str | None = None) -> list[Listing]: ...


def get_adapter(name: str, **kwargs) -> MLSAdapter:
    name = name.lower().strip()
    if name == "mock":
        from .mock import MockAdapter
        return MockAdapter(**kwargs)
    if name == "reso":
        from .reso import RESOAdapter
        return RESOAdapter(**kwargs)
    raise ValueError(
        f"Unknown MLS provider '{name}'. Available: mock, reso. "
        f"Bridge and Spark adapters are on the roadmap."
    )
