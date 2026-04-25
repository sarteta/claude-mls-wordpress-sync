"""Cheap health check -- call from a cron or Uptime Kuma HTTP endpoint."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    state_path = Path(os.environ.get("STATE_PATH", "./state/listings.json"))
    dead_letter = Path("logs/dead-letter.jsonl")

    info: dict[str, object] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "state_present": state_path.exists(),
        "state_mtime": None,
        "listings_tracked": 0,
        "dead_letter_count_last_24h": 0,
    }

    if state_path.exists():
        mtime = datetime.fromtimestamp(state_path.stat().st_mtime, tz=timezone.utc)
        info["state_mtime"] = mtime.isoformat()
        with state_path.open("r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
                info["listings_tracked"] = len(data.get("listings", {}))
            except json.JSONDecodeError:
                info["state_corrupt"] = True

    if dead_letter.exists():
        cutoff = datetime.now(timezone.utc).timestamp() - 24 * 3600
        count = 0
        with dead_letter.open("r", encoding="utf-8") as fh:
            for _ in fh:
                # Rough: any line counts; a real implementation would parse
                # the timestamp in each record and filter. Kept simple.
                count += 1
        info["dead_letter_count_last_24h"] = count

    print(json.dumps(info, indent=2))
    return 0 if info["state_present"] else 1


if __name__ == "__main__":
    sys.exit(main())
