"""Smoke test: mock adapter returns a valid synthetic feed."""
from __future__ import annotations

import asyncio

from src.mls_adapters.mock import MockAdapter


def test_mock_returns_listings_with_stable_keys() -> None:
    adapter = MockAdapter(total=5)
    listings = asyncio.run(adapter.fetch_all())
    assert len(listings) == 5
    for l in listings:
        assert l.listing_key.startswith("ACME-")
        assert "ListPrice" in l.raw
        assert "MlsStatus" in l.raw


def test_mock_churn_produces_some_changes_between_calls() -> None:
    adapter = MockAdapter(total=20, churn=1.0)   # force 100% churn
    first = asyncio.run(adapter.fetch_all())
    second = asyncio.run(adapter.fetch_all())
    changed = sum(
        1 for a, b in zip(first, second)
        if a.raw["ModificationTimestamp"] != b.raw["ModificationTimestamp"]
    )
    assert changed > 0
