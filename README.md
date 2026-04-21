# claude-mls-wordpress-sync

Diff-based sync engine. Pulls real-estate listings from an MLS (RESO Web API / Bridge Interactive / Spark / IDX Broker) and pushes only the **changed** listings into WordPress (Custom Post Type) via the WP REST API.

Meant for brokerage sites that were either burning their MLS API quota on full re-syncs or losing custom fields every time the cron ran.

> Demo data is synthetic (`Acme Realty`, `+1555...`). Plug your real MLS credentials in `.env` to sync a live feed.

---

## Why this exists

Most "MLS → WordPress" integrations I've worked on do a full overwrite on
every cron. That burns MLS API quota (Spark/Bridge rate-limit you in
hours), it re-creates WP posts (kills SEO permalinks and wipes whatever
custom fields staff edited), and it re-downloads every image on every
run (sync goes from minutes to hours).

This project does a diff sync:

1. Pull listings from MLS (paginated, with `ModificationTimestamp` filter when supported)
2. Load local state snapshot (`state/listings.json`) — `listing_id → content_hash`
3. Compute diff: `created | updated | unchanged | removed`
4. Push only `created + updated` to WordPress via REST
5. Mark `removed` as `status=draft` (never hard-delete — lets the broker review first)
6. Persist new state snapshot atomically

Result: a 1,200-listing MLS that runs every 15 minutes typically touches <20 listings per cycle.

---

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌──────────────────┐
│   MLS provider  │         │  sync engine (this)  │         │     WordPress    │
│  RESO / Spark   │ ──────► │                      │ ──────► │  /wp/v2/listing  │
│  Bridge / IDX   │  GET    │  ┌────────────────┐  │  POST   │   (Custom Post)  │
└─────────────────┘         │  │  MLSAdapter    │  │         └──────────────────┘
                            │  │  StateStore    │  │
                            │  │  Differ        │  │
                            │  │  WPClient      │  │
                            │  └────────────────┘  │
                            └──────────────────────┘
                                     │
                                     ▼
                             state/listings.json
                             (SHA-256 per listing)
```

## Features

- **Adapter pattern for MLS providers.** `src/mls_adapters/` has one file per provider (`reso.py`, `bridge.py`, `spark.py`, `mock.py`). Switching providers = config change, no code change in sync loop.
- **Configurable field mapping.** `config/field_mapping.yaml` declares how MLS fields map to WP post fields + meta keys. Change vendor, just edit YAML.
- **Idempotent.** Running sync twice in a row on an unchanged MLS = zero writes to WordPress.
- **Exponential retry + dead-letter log.** Network failures retry 3x with backoff; permanent failures logged to `logs/dead-letter.jsonl` for human review.
- **Async with `httpx.AsyncClient`.** Pulls + pushes are concurrent with semaphore-bounded parallelism.
- **Zero-cost health endpoint.** `python -m src.health` prints last-sync timestamp, success rate last 24h, and dead-letter count — pipe to Slack/Uptime Kuma.

## Quickstart

```bash
git clone https://github.com/sarteta/claude-mls-wordpress-sync.git
cd claude-mls-wordpress-sync
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # edit creds
python -m src.sync --provider mock --dry-run          # preview diff
python -m src.sync --provider mock                    # actually sync
```

`--provider mock` uses the bundled synthetic feed so you can see the engine work before connecting a real MLS.

## Configuration

Everything lives in `.env` + `config/field_mapping.yaml`:

```ini
# .env
MLS_PROVIDER=reso              # reso | bridge | spark | mock
MLS_BASE_URL=https://api.example-mls.com
MLS_ACCESS_TOKEN=<redacted>
MLS_PAGE_SIZE=200

WP_BASE_URL=https://your-wp-site.com
WP_USER=integration-bot
WP_APP_PASSWORD=<redacted>
WP_POST_TYPE=listing

SYNC_INTERVAL_MINUTES=15
STATE_PATH=./state/listings.json
LOG_LEVEL=INFO
```

```yaml
# config/field_mapping.yaml
post_fields:
  title: ListingKey
  content: PublicRemarks
  status: derived_from_MlsStatus  # maps Active→publish, Closed→draft
meta_fields:
  price: ListPrice
  bedrooms: BedroomsTotal
  bathrooms: BathroomsTotalInteger
  sqft: LivingArea
  address: UnparsedAddress
  listing_agent_name: ListAgentFullName
  listing_agent_phone: ListAgentPreferredPhone
```

## Scheduling

Linux cron:
```
*/15 * * * * cd /srv/claude-mls-sync && /srv/claude-mls-sync/.venv/bin/python -m src.sync >> logs/cron.log 2>&1
```

Windows Task Scheduler: use `scripts/run-sync.ps1`.

Docker: `docker compose up -d` runs the sync loop internally every `SYNC_INTERVAL_MINUTES`.

## Project status

- [x] Core diff engine
- [x] Mock adapter (synthetic feed for demos/tests)
- [x] RESO Web API adapter
- [x] WordPress REST client with app-password auth
- [x] Field mapping via YAML
- [x] Exponential retry + dead-letter
- [ ] Spark API adapter (planned — next release)
- [ ] Bridge Interactive adapter (planned)
- [ ] Image diff + lazy download (planned)

## License

MIT — see [LICENSE](./LICENSE).

Built by [Santiago Arteta](https://github.com/sarteta) out of real-estate
integration work. Forks and issues welcome; happy to consult on custom
MLS feeds.
