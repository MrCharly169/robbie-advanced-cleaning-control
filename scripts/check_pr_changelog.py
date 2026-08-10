#!/usr/bin/env python3
"""Require a changelog update for production or release changes."""
from __future__ import annotations

import subprocess
import sys

PREFIXES = ("custom_components/robbie_advanced_cc/", "scripts/", ".github/workflows/")
EXEMPT = {"custom_components/robbie_advanced_cc/manifest.json"}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_pr_changelog.py BASE_REF", file=sys.stderr)
        return 2
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{sys.argv[1]}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    changed = {line for line in result.stdout.splitlines() if line}
    production = any(
        path.startswith(PREFIXES) and path not in EXEMPT for path in changed
    )
    if production and "CHANGELOG.md" not in changed:
        print("Production changed without CHANGELOG.md.", file=sys.stderr)
        return 1
    print("PR changelog policy is satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
