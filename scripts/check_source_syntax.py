#!/usr/bin/env python3
"""Validate all tracked and untracked source files used by the project."""
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = {".github", "custom_components", "scripts", "tests"}


def repository_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(
        ROOT / item
        for item in result.stdout.splitlines()
        if item and item.split("/", 1)[0] in SOURCE_ROOTS
    )


def main() -> int:
    files = repository_files()
    python_files = [path for path in files if path.suffix == ".py"]
    javascript_files = [path for path in files if path.suffix in {".js", ".mjs", ".cjs"}]
    json_files = [path for path in files if path.suffix == ".json"]
    with tempfile.TemporaryDirectory(prefix="racc-syntax-") as temp:
        root = Path(temp)
        for source in python_files:
            target = root / source.relative_to(ROOT).with_suffix(".pyc")
            target.parent.mkdir(parents=True, exist_ok=True)
            py_compile.compile(str(source), cfile=str(target), doraise=True)
    for source in json_files:
        json.loads(source.read_text(encoding="utf-8"))
    for source in javascript_files:
        subprocess.run(["node", "--check", str(source)], cwd=ROOT, check=True)
    print(
        f"Source syntax valid: Python={len(python_files)}, "
        f"JavaScript={len(javascript_files)}, JSON={len(json_files)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Source syntax validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
