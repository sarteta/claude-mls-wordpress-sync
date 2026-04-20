"""Unit tests for the pure-function differ."""
from __future__ import annotations

from src.differ import diff, new_state
from src.models import Listing
from src.state_store import content_hash


def _listing(key: str, price: int = 100_000) -> Listing:
    return Listing(
        listing_key=key,
        modification_ts="2026-04-20T00:00:00Z",
        raw={"ListingKey": key, "ListPrice": price},
    )


def test_empty_previous_marks_everything_created() -> None:
    current = [_listing("A"), _listing("B")]
    result = diff({}, current)
    assert [l.listing_key for l in result.created] == ["A", "B"]
    assert result.updated == []
    assert result.removed == []
    assert result.unchanged == []


def test_unchanged_payload_produces_no_writes() -> None:
    current = [_listing("A"), _listing("B")]
    previous = {l.listing_key: content_hash(l) for l in current}
    result = diff(previous, current)
    assert result.has_writes is False
    assert sorted(result.unchanged) == ["A", "B"]


def test_payload_change_is_detected_as_update() -> None:
    old = _listing("A", price=100_000)
    new = _listing("A", price=150_000)
    previous = {old.listing_key: content_hash(old)}
    result = diff(previous, [new])
    assert [l.listing_key for l in result.updated] == ["A"]
    assert result.created == []


def test_missing_from_current_is_marked_removed() -> None:
    old = _listing("A")
    previous = {old.listing_key: content_hash(old)}
    result = diff(previous, [])
    assert result.removed == ["A"]


def test_new_state_reflects_current_only() -> None:
    current = [_listing("A"), _listing("B")]
    state = new_state({"Z": "old-hash"}, current)
    assert set(state.keys()) == {"A", "B"}
