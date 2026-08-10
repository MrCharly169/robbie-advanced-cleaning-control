#!/usr/bin/env python3
"""Build or validate an installable Robbie Advanced CC archive."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "robbie_advanced_cc"
CANONICAL_RESOURCE = "/robbie_advanced_cc/cleaning-control.js"
LEGACY_RESOURCE = COMPONENT / "frontend" / "robbie-advanced-card.js"
CALVER = re.compile(r"^20\d{2}\.(?:[1-9]|1[0-2])\.\d+(?:b\d+)?$")
REQUIRED = (
    COMPONENT / "manifest.json",
    COMPONENT / "__init__.py",
    COMPONENT / "config_flow.py",
    COMPONENT / "services.yaml",
    COMPONENT / "frontend" / "cleaning-control.js",
    LEGACY_RESOURCE,
    ROOT / "hacs.json",
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    ROOT / "LICENSE",
)


def validate(expected_tag: str | None = None) -> str:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        raise RuntimeError("Missing required files: " + ", ".join(missing))
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("domain") != "robbie_advanced_cc":
        raise RuntimeError("manifest domain must be robbie_advanced_cc")
    version = str(manifest.get("version", "")).strip()
    if not CALVER.fullmatch(version):
        raise RuntimeError("manifest version must use YYYY.M.PATCH or YYYY.M.PATCHbN")
    if expected_tag and expected_tag.removeprefix("v") != version:
        raise RuntimeError(f"release tag {expected_tag} does not match {version}")
    if 'import "./cleaning-control.js"' not in LEGACY_RESOURCE.read_text(encoding="utf-8"):
        raise RuntimeError("legacy frontend must only load cleaning-control.js")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if CANONICAL_RESOURCE not in readme or f"{CANONICAL_RESOURCE}?v=" in readme:
        raise RuntimeError("README must document the permanent unversioned resource")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if "## Unreleased" not in changelog or f"## {version}" not in changelog:
        raise RuntimeError("CHANGELOG must contain Unreleased and the manifest version")
    return version


def build(output: Path, expected_tag: str | None = None) -> None:
    version = validate(expected_tag)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(COMPONENT.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(ROOT))
        for name in ("README.md", "CHANGELOG.md", "LICENSE", "hacs.json"):
            archive.write(ROOT / name, name)
    print(f"Built {output} for Robbie Advanced Cleaning Control {version}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--tag")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "dist" / "robbie_advanced_cc.zip"
    )
    args = parser.parse_args()
    try:
        if args.check:
            print(f"Package structure valid for {validate(args.tag)}")
        else:
            build(args.output, args.tag)
    except Exception as exc:
        print(f"release validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
