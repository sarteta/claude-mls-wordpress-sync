"""Field mapping smoke tests using the bundled config."""
from __future__ import annotations

from pathlib import Path

from src.mapping import FieldMapping
from src.models import Listing


def _cfg() -> FieldMapping:
    return FieldMapping(Path(__file__).parent.parent / "config" / "field_mapping.yaml")


def test_active_listing_maps_to_publish() -> None:
    mapping = _cfg()
    listing = Listing(
        listing_key="ACME-1",
        modification_ts="2026-04-20T00:00:00Z",
        raw={
            "ListingKey": "ACME-1",
            "PublicRemarks": "Charming condo.",
            "MlsStatus": "Active",
            "ListPrice": 350_000,
        },
    )
    payload = mapping.to_wp_payload(listing)
    assert payload["title"] == "ACME-1"
    assert payload["status"] == "publish"
    assert payload["meta"]["price"] == 350_000


def test_closed_listing_is_never_published() -> None:
    mapping = _cfg()
    listing = Listing(
        listing_key="ACME-2",
        modification_ts="2026-04-20T00:00:00Z",
        raw={"ListingKey": "ACME-2", "MlsStatus": "Closed"},
    )
    payload = mapping.to_wp_payload(listing)
    assert payload["status"] == "draft"


def test_unknown_status_defaults_to_draft() -> None:
    mapping = _cfg()
    listing = Listing(
        listing_key="ACME-3",
        modification_ts="2026-04-20T00:00:00Z",
        raw={"ListingKey": "ACME-3", "MlsStatus": "Bogus"},
    )
    payload = mapping.to_wp_payload(listing)
    assert payload["status"] == "draft"
