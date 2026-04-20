"""State store round-trip + atomic write tests."""
from __future__ import annotations

import json
from pathlib import Path

from src.state_store import StateStore


def test_round_trip(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    assert store.load() == {}
    store.save_atomic({"A": "hash-a", "B": "hash-b"})
    reloaded = StateStore(tmp_path / "state.json")
    assert reloaded.load() == {"A": "hash-a", "B": "hash-b"}


def test_file_format_is_versioned_json(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.save_atomic({"A": "hash-a"})
    with (tmp_path / "state.json").open() as fh:
        data = json.load(fh)
    assert data["version"] == 1
    assert data["listings"] == {"A": "hash-a"}


def test_no_temp_file_left_behind_on_success(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.save_atomic({"A": "hash-a"})
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".state-")]
    assert leftovers == []
