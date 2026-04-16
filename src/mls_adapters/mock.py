"""Mock adapter — returns a synthetic RESO-shaped feed so the sync engine
runs end-to-end without needing a real MLS account. Used in tests and demos.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from ..models import Listing

# Pinning the seed keeps demos deterministic (screenshots match docs).
_RNG = random.Random(42)

_CITIES = [
    ("Austin", "TX", "78701"),
    ("Denver", "CO", "80202"),
    ("Miami", "FL", "33101"),
    ("Seattle", "WA", "98101"),
    ("Chicago", "IL", "60601"),
]

_STATUSES = ["Active", "Active", "Active", "Pending", "Closed"]  # biased realistic


def _fake_listing(idx: int, drift: int = 0) -> dict:
    city, state, zipc = _RNG.choice(_CITIES)
    base_price = 250_000 + _RNG.randrange(0, 750_000, 5000)
    mod_ts = (datetime.now(timezone.utc) - timedelta(minutes=drift)).isoformat()
    return {
        "ListingKey": f"ACME-{10000 + idx}",
        "ListPrice": base_price,
        "BedroomsTotal": _RNG.randint(1, 5),
        "BathroomsTotalInteger": _RNG.randint(1, 4),
        "LivingArea": 800 + _RNG.randrange(0, 3200, 50),
        "UnparsedAddress": f"{_RNG.randrange(100, 9999)} Maple Ave",
        "City": city,
        "StateOrProvince": state,
        "PostalCode": zipc,
        "MlsStatus": _RNG.choice(_STATUSES),
        "ModificationTimestamp": mod_ts,
        "PublicRemarks": (
            f"Charming {_RNG.choice(['bungalow', 'townhouse', 'condo'])} in "
            f"{city}, steps from public transit. Demo data from Acme Realty."
        ),
        "ListAgentFullName": _RNG.choice([
            "Jamie Rivera", "Morgan Patel", "Taylor Kim", "Alex Nguyen",
        ]),
        "ListAgentPreferredPhone": f"+1555{_RNG.randrange(1000000, 9999999)}",
        "ListAgentEmail": "agent@acme-realty.example",
    }


class MockAdapter:
    def __init__(self, page_size: int = 200, total: int = 12, churn: float = 0.25):
        """
        `total` — how many listings the mock MLS "has".
        `churn` — fraction of listings that change payload each fetch, so the
                  diff engine has something to do.
        """
        self.page_size = page_size
        self.total = total
        self.churn = churn
        self._seq = 0

    async def fetch_all(self, since: str | None = None) -> list[Listing]:
        self._seq += 1
        listings: list[Listing] = []
        for i in range(self.total):
            drift = self._seq * 5 if _RNG.random() < self.churn else 0
            raw = _fake_listing(i, drift=drift)
            listings.append(
                Listing(
                    listing_key=raw["ListingKey"],
                    modification_ts=raw["ModificationTimestamp"],
                    raw=raw,
                )
            )
        return listings
