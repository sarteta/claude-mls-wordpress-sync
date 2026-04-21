# Changelog

## [Unreleased]

## [0.1.0] — 2026-04-20

First tagged release. Pulled out of the Nobis Salud / Córdoba real estate
work and generalized.

### Added

- `MLSAdapter` base class with RESO Web API, Spark, Bridge, and IDX adapters.
- `Differ` — SHA-256 per listing kept in `state/listings.json`. Only changed
  listings get POSTed upstream.
- `WPClient` — WordPress REST (`/wp/v2/listing`) with app-password auth and
  request backoff.
- Field mapping table in `config/mapping.yml`. Keep your WP custom fields
  stable and this is the one file you edit per install.
- Cron-friendly `sync.py` entrypoint + Dockerfile.
- Pytest suite with fixture listings for each adapter.

### Known gaps

- No image handling yet. Media URLs pass through as-is; if the MLS host goes
  down you're stuck. Next pass will pre-download to media library.
- No soft-delete for listings pulled from feed — they just disappear from the
  diff. Considered but decided it's a config choice, not a library default.
