#!/usr/bin/env python3
"""Validate the branch, version and changelog for publication."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from release_changelog import extract_release_notes, validate_version

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=("beta", "stable"), required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--confirm-version", required=True)
    args = parser.parse_args()
    try:
        version = json.loads((ROOT / "custom_components" / "robbie_advanced_cc" / "manifest.json").read_text(encoding="utf-8"))["version"]
        expected = "develop" if args.channel == "beta" else "main"
        if args.branch.removeprefix("refs/heads/") != expected:
            raise RuntimeError(f"{args.channel} releases must run from {expected}")
        validate_version(args.channel, version)
        if args.confirm_version != version:
            raise RuntimeError("confirmation does not match manifest version")
        extract_release_notes((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    except Exception as exc:
        print(f"release channel validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated {args.channel} release v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
