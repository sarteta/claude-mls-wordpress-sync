# claude-mls-wordpress-sync

[![tests](https://github.com/sarteta/claude-mls-wordpress-sync/actions/workflows/tests.yml/badge.svg)](https://github.com/sarteta/claude-mls-wordpress-sync/actions/workflows/tests.yml)
[![python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org)
[![license](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Diff-based sync engine: MLS listings (RESO / Bridge / Spark / mock adapter) → WordPress Custom Post Type via the REST API. Python async, YAML-driven field mapping, atomic state store, dead-letter log.

![demo](./examples/demo.png)

## Why did I build this?

Let's be honest: most "MLS → WordPress" integrations just blindly overwrite everything on every cron run. That’s a nightmare because:

It burns your MLS API quota (Spark and Bridge will rate-limit you fast).

It deletes and recreates WP posts, which kills your SEO permalinks and wipes any custom data your agents added manually.

It re-downloads the same images every single time. A 5-minute sync turns into a 3-hour crawl.

This script takes a smarter approach using a diff sync:

Grabs the listings from the MLS (handling pagination and filtering by ModificationTimestamp if supported).

Loads a local snapshot (state/listings.json) mapping listing_id to its content hash.

Figures out exactly what changed: created, updated, unchanged, or removed.

Pushes only the new or updated stuff to WordPress via the REST API.

Drafts removed listings (it never hard-deletes, so the broker can review them first).

Saves the new state atomically.

The result? A 1,200-listing MLS feed running every 15 minutes usually updates fewer than 20 posts per cycle. It's fast and light.

flowchart LR
    MLS[MLS provider<br/>RESO / Spark / Bridge / IDX] -->|GET paginated| ENG[sync engine<br/>MLSAdapter → Differ → WPClient]
    ENG -->|POST changed only| WP[WordPress<br/>/wp/v2/listing]
    ENG <--> ST[(state/listings.json<br/>SHA-256 per listing)]


What's under the hood?
Drop-in MLS Adapters. Check out src/mls_adapters/ (reso.py, bridge.py, etc.). Switching providers is just a config tweak; you don't have to touch the core sync loop.

No-code Field Mapping. How do MLS fields map to your WP setup? It's all in config/field_mapping.yaml. If you change vendors, just edit the YAML file.

Idempotent. Run it twice in a row without MLS changes, and it won't make a single write to WordPress.

Built-in Resilience. Network hiccups? It retries 3x with an exponential backoff. Permanent failures get dumped to logs/dead-letter.jsonl so you can figure out what went wrong later.

Fast & Async. Uses httpx.AsyncClient with bounded concurrency so it doesn't overwhelm your server or WordPress.

Easy Health Checks. Run python -m src.health to get the last sync time, success rate, and dead-letter count. Super easy to pipe into Slack or Uptime Kuma.



git clone https://github.com/sarteta/claude-mls-wordpress-sync.git
cd claude-mls-wordpress-sync
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # edit your creds here
python -m src.sync --provider mock --dry-run          # preview the diff
python -m src.sync --provider mock                    # actually sync it

--provider mock uses the bundled fake feed. Try it out to see the diff engine in action before hooking up your real MLS.

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


  */15 * * * * cd /srv/claude-mls-sync && /srv/claude-mls-sync/.venv/bin/python -m src.sync >> logs/cron.log 2>&1

  Windows Task Scheduler: Use the included scripts/run-sync.ps1.

Docker: docker compose up -d runs the sync loop internally every SYNC_INTERVAL_MINUTES.

Roadmap
[x] Core diff engine

[x] Mock adapter (fake feed for testing)

[x] RESO Web API adapter

[x] WP REST client (via app passwords)

[x] YAML field mapping

[x] Exponential retries & dead-letter logging

[ ] Spark API adapter (up next)

[ ] Bridge Interactive adapter (planned)

[ ] Image diffing + lazy downloads (planned)

License & Credits
MIT License — see LICENSE.

Built by Santiago Arteta after dealing with one too many broken real estate integrations. Forks and pull requests are welcome! If you need help untangling a weird custom MLS feed, feel free to reach out.

