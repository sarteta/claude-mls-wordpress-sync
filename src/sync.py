"""Entry point: `python -m src.sync [--provider mock] [--dry-run]`."""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .differ import diff, new_state
from .mapping import FieldMapping
from .mls_adapters import get_adapter
from .state_store import StateStore
from .wp_client import WPClient

logger = logging.getLogger("mls-sync")


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


def _build_adapter(provider: str):
    if provider == "mock":
        return get_adapter("mock")
    if provider == "reso":
        return get_adapter(
            "reso",
            base_url=os.environ["MLS_BASE_URL"],
            access_token=os.environ["MLS_ACCESS_TOKEN"],
            page_size=int(os.environ.get("MLS_PAGE_SIZE", "200")),
        )
    raise SystemExit(f"provider '{provider}' not implemented yet.")


async def _run(provider: str, dry_run: bool) -> int:
    load_dotenv()
    _configure_logging(os.environ.get("LOG_LEVEL", "INFO"))

    state = StateStore(os.environ.get("STATE_PATH", "./state/listings.json"))
    mapping = FieldMapping(Path("config/field_mapping.yaml"))
    adapter = _build_adapter(provider)

    previous = state.load()
    # The `since` filter is only safe when we already have state AND the
    # adapter supports incremental fetch. Mock always does a full fetch.
    since = max(previous.values(), default=None) if provider != "mock" else None
    # NOTE: `previous` stores hashes; for incremental we'd track the max
    # ModificationTimestamp in a separate key -- kept simple here.

    current = await adapter.fetch_all(since=None)
    result = diff(previous, current)
    logger.info("diff: %s", result.summary)

    if dry_run:
        logger.info("dry-run: no writes to WordPress, no state saved.")
        return 0

    if not result.has_writes:
        logger.info("nothing to do -- WordPress already in sync.")
        return 0

    wp = WPClient(
        base_url=os.environ["WP_BASE_URL"],
        user=os.environ["WP_USER"],
        app_password=os.environ["WP_APP_PASSWORD"],
        post_type=os.environ.get("WP_POST_TYPE", "listing"),
    )

    # Upsert created + updated, concurrently but bounded by WPClient.semaphore.
    writes = [
        wp.upsert(l.listing_key, mapping.to_wp_payload(l))
        for l in (*result.created, *result.updated)
    ]
    drafts = [wp.mark_draft(k) for k in result.removed]
    await asyncio.gather(*writes, *drafts)

    # Only persist state after all writes completed -- if this run was
    # interrupted mid-batch, next run will re-push the same diff idempotently.
    state.save_atomic(new_state(previous, current))
    logger.info("state saved: %d entries", len(current))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="MLS → WordPress diff-sync.")
    parser.add_argument(
        "--provider",
        default=os.environ.get("MLS_PROVIDER", "mock"),
        help="mock | reso (bridge & spark planned)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute diff but don't write to WP or state.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.provider, args.dry_run)))


if __name__ == "__main__":
    main()
