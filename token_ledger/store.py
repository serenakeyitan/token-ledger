"""Persistent storage for the ledger — a single YAML file in ~/.config/token-ledger/."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from .models import Entry

DEFAULT_CONFIG_DIR = Path(os.environ.get("TOKEN_LEDGER_DIR", "~/.config/token-ledger")).expanduser()
LEDGER_FILE = "ledger.yaml"


def _ledger_path(config_dir: Path = DEFAULT_CONFIG_DIR) -> Path:
    return config_dir / LEDGER_FILE


def load(config_dir: Path = DEFAULT_CONFIG_DIR) -> list[Entry]:
    """Load all entries from the ledger file. Returns empty list if not found."""
    path = _ledger_path(config_dir)
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text()) or {}
    entries_data = raw.get("entries", [])
    return [Entry.from_dict(d) for d in entries_data]


def save(entries: list[Entry], config_dir: Path = DEFAULT_CONFIG_DIR) -> None:
    """Persist entries to disk."""
    config_dir.mkdir(parents=True, exist_ok=True)
    path = _ledger_path(config_dir)
    data = {"entries": [e.to_dict() for e in entries]}
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def get(entry_id: str, config_dir: Path = DEFAULT_CONFIG_DIR) -> Optional[Entry]:
    """Fetch a single entry by id."""
    for e in load(config_dir):
        if e.id == entry_id:
            return e
    return None


def upsert(entry: Entry, config_dir: Path = DEFAULT_CONFIG_DIR) -> None:
    """Add or replace an entry."""
    entries = load(config_dir)
    entries = [e for e in entries if e.id != entry.id]
    entries.append(entry)
    save(entries, config_dir)


def remove(entry_id: str, config_dir: Path = DEFAULT_CONFIG_DIR) -> bool:
    """Remove entry by id. Returns True if found and removed."""
    entries = load(config_dir)
    new = [e for e in entries if e.id != entry_id]
    if len(new) == len(entries):
        return False
    save(new, config_dir)
    return True
