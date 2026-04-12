"""Pure-function differ: (previous state, current listings) -> DiffResult."""
from __future__ import annotations

from .models import DiffResult, Listing
from .state_store import content_hash


def diff(previous: dict[str, str], current: list[Listing]) -> DiffResult:
    """Compute the diff deterministically.

    `previous`: {listing_key: content_hash} from last sync
    `current`:  listings just fetched from the MLS

    Anything that appears in `previous` but not in `current` is considered
    `removed` — but we NEVER hard-delete from WordPress. The caller should
    set those posts to draft and let a human confirm.
    """
    result = DiffResult()
    seen: set[str] = set()

    for listing in current:
        seen.add(listing.listing_key)
        new_hash = content_hash(listing)
        old_hash = previous.get(listing.listing_key)
        if old_hash is None:
            result.created.append(listing)
        elif old_hash != new_hash:
            result.updated.append(listing)
        else:
            result.unchanged.append(listing.listing_key)

    for key in previous.keys() - seen:
        result.removed.append(key)

    return result


def new_state(previous: dict[str, str], current: list[Listing]) -> dict[str, str]:
    """State snapshot to persist AFTER a successful push.

    Keeps entries for everything in `current`, drops the ones not present
    (they'll live on in WordPress as drafts — decoupling WP deletion policy
    from our state tracking is intentional).
    """
    return {listing.listing_key: content_hash(listing) for listing in current}
