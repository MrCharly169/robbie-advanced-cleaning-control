#!/usr/bin/env python3
"""Wait until Home Assistant has flushed the tested config entry to storage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--entity-registry", type=Path)
    parser.add_argument("--vacuum", action="append", default=[])
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=60)
    args = parser.parse_args()
    entry_id = str(json.loads(args.state.read_text(encoding="utf-8"))["entry_id"])
    deadline = time.monotonic() + args.wait_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            payload = json.loads(args.storage.read_text(encoding="utf-8"))
            entries = payload.get("data", {}).get("entries", [])
            entry_persisted = any(
                str(item.get("entry_id")) == entry_id for item in entries
            )
            registry_persisted = True
            if args.entity_registry and args.vacuum:
                registry_payload = json.loads(
                    args.entity_registry.read_text(encoding="utf-8")
                )
                registry_entities = registry_payload.get("data", {}).get(
                    "entities", []
                )
                by_id = {
                    str(item.get("entity_id")): item
                    for item in registry_entities
                }
                registry_persisted = all(
                    by_id.get(vacuum, {})
                    .get("options", {})
                    .get("vacuum", {})
                    .get("area_mapping")
                    for vacuum in args.vacuum
                )
            if entry_persisted and registry_persisted:
                print(f"Config entry {entry_id} and vacuum mappings persisted")
                return 0
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            last_error = exc
        time.sleep(1)
    raise SystemExit(
        f"Config entry {entry_id} or vacuum mappings were not persisted "
        f"within {args.wait_seconds}s: {last_error}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
