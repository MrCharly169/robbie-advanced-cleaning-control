#!/usr/bin/env python3
"""Prepare and extract changelog-driven CalVer releases."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BETA = re.compile(r"^20\d{2}\.(?:[1-9]|1[0-2])\.\d+b\d+$")
STABLE = re.compile(r"^20\d{2}\.(?:[1-9]|1[0-2])\.\d+$")
HEADING = re.compile(r"(?m)^##\s+([^\r\n]+)\s*$")


def validate_version(channel: str, version: str) -> str:
    pattern = BETA if channel == "beta" else STABLE
    if channel not in {"beta", "stable"} or not pattern.fullmatch(version):
        expected = "YYYY.M.PATCHbN" if channel == "beta" else "YYYY.M.PATCH"
        raise RuntimeError(f"version {version!r} is invalid for {channel}; expected {expected}")
    return version


def sections(text: str) -> list[tuple[str, int, int, str]]:
    matches = list(HEADING.finditer(text))
    return [
        (
            match.group(1).strip(),
            match.start(),
            matches[index + 1].start() if index + 1 < len(matches) else len(text),
            text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip(),
        )
        for index, match in enumerate(matches)
    ]


def extract_release_notes(text: str, version: str) -> str:
    version = version.removeprefix("v")
    matches = [body for title, _, _, body in sections(text) if title.split(" - ", 1)[0] == version]
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError(f"CHANGELOG must contain one non-empty section for {version}")
    return matches[0]


def _version_from_title(title: str) -> str | None:
    candidate = title.split(" - ", 1)[0]
    return candidate if BETA.fullmatch(candidate) or STABLE.fullmatch(candidate) else None


def _nest_headings(text: str) -> str:
    """Keep aggregated beta headings below their version heading."""
    return re.sub(
        r"(?m)^(#{3,5})\s+(.+)$",
        lambda match: f"{'#' * (len(match.group(1)) + 2)} {match.group(2)}",
        text,
    )


def _release_notes(channel: str, parsed, unreleased_body: str) -> str:
    parts = [unreleased_body.strip()] if unreleased_body.strip() else []
    if channel == "stable":
        beta_history: list[tuple[str, str]] = []
        seen_unreleased = False
        for title, _, _, body in parsed:
            if title == "Unreleased":
                seen_unreleased = True
                continue
            if not seen_unreleased:
                continue
            version = _version_from_title(title)
            if version and STABLE.fullmatch(version):
                break
            if version and BETA.fullmatch(version) and body:
                beta_history.append((version, body))
        if beta_history:
            history = ["### Included beta release history"]
            for version, body in beta_history:
                history.extend((f"#### {version}", _nest_headings(body)))
            parts.append("\n\n".join(history))
    notes = "\n\n".join(parts).strip()
    if not notes:
        raise RuntimeError(
            "CHANGELOG Unreleased is empty and no beta history can be promoted"
        )
    return notes


def prepare_release(channel: str, source: str, target: str, version: str, release_date: str, *, root: Path = ROOT) -> str:
    validate_version(channel, version)
    if source.removeprefix("refs/heads/") != "develop":
        raise RuntimeError("release preparation must use develop as source")
    expected_target = "develop" if channel == "beta" else "main"
    if target.removeprefix("refs/heads/") != expected_target:
        raise RuntimeError(f"{channel} preparation must target {expected_target}")
    date.fromisoformat(release_date)
    changelog_path = root / "CHANGELOG.md"
    manifest_path = root / "custom_components" / "robbie_advanced_cc" / "manifest.json"
    text = changelog_path.read_text(encoding="utf-8")
    parsed = sections(text)
    unreleased = [item for item in parsed if item[0] == "Unreleased"]
    if len(unreleased) != 1:
        raise RuntimeError("CHANGELOG must contain exactly one Unreleased section")
    if any(title.split(" - ", 1)[0] == version for title, *_ in parsed):
        raise RuntimeError(f"CHANGELOG already contains {version}")
    _, start, end, unreleased_body = unreleased[0]
    if channel == "beta" and not unreleased_body:
        raise RuntimeError("CHANGELOG Unreleased section is empty")
    notes = _release_notes(channel, parsed, unreleased_body)
    updated = text[:start].rstrip() + f"\n\n## Unreleased\n\n\n## {version} - {release_date}\n\n{notes}\n"
    if text[end:].strip():
        updated += "\n" + text[end:].lstrip()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    changelog_path.write_text(updated, encoding="utf-8")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    for name in ("channel", "source-branch", "target-branch", "version", "date"):
        prepare.add_argument(f"--{name}", required=True)
    notes = commands.add_parser("notes")
    notes.add_argument("--version", required=True)
    notes.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare_release(args.channel, args.source_branch, args.target_branch, args.version, args.date)
        else:
            value = extract_release_notes((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), args.version)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(value.rstrip() + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"release changelog operation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
