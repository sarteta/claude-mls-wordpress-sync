# Architecture notes

## Why a diff engine instead of full overwrite

Most off-the-shelf MLS importers re-create WordPress posts on every cron.
That introduces three concrete costs:

1. **API quota burn.** Spark API free tier is 1000 requests/day. Bridge
   throttles aggressively. A 1,200-listing MLS hit every 15 minutes full-
   fetch = 115k+ requests/day. The diff approach stays well inside the free
   tier because we only write on change.
2. **SEO / permalink churn.** Deleting and re-creating posts regenerates
   slugs (`acme-1` → `acme-1-2` → `acme-1-3`). The diff approach calls
   `POST /wp/v2/listing/{id}` which preserves the original slug.
3. **Staff-set custom fields get clobbered.** Agents often edit the post
   on the WP side (add description, tag neighborhoods, pin photos). A
   full-overwrite importer wipes that work every 15 minutes.

The diff engine compares SHA-256 hashes of the full MLS payload against the
previous snapshot. If the hash matches, we do nothing — even the HTTP call
to WP is skipped.

## Why "removed" → draft, never delete

Brokers hate when a listing disappears from their site silently — it's
typically a data glitch at the MLS end (stale `MlsStatus` flip, paging bug)
rather than an actual delisting. Marking `status=draft` keeps the post
recoverable and flags it for human review on the WP dashboard. If the
listing reappears in the next fetch, we flip it back to publish.

## State file format

`state/listings.json`:

```json
{
  "version": 1,
  "listings": {
    "ACME-10001": "a3f7...sha256",
    "ACME-10002": "82cd...sha256"
  }
}
```

Deliberately boring. If we ever need to reset and re-push everything,
`rm state/listings.json` does it.

## Extending to a new MLS vendor

Create `src/mls_adapters/<vendor>.py` with a class that implements:

```python
async def fetch_all(self, since: str | None = None) -> list[Listing]:
    ...
```

Register it in `src/mls_adapters/__init__.py:get_adapter`.

Nothing else in the sync engine needs to change.
