# Contributing

## Change discipline

Keep pull requests focused. For every user-visible change:

1. add or update regression tests;
2. add a concise entry under `CHANGELOG.md -> Unreleased`;
3. update README or detailed documentation when installation, configuration,
   entities, adapters, Card behavior or workflows change;
4. describe migration impact in the pull request.

Do not remove a regression test merely to make a change pass.

## Language discipline

Source code, identifiers, logs, reason codes, repository documentation and
release notes are English. Every customer-facing Home Assistant string and Card
label must be present in English and German. Machine identifiers are never
translated.

## Version discipline

`custom_components/robbie_advanced_cc/manifest.json` is the only technical
version source. The canonical frontend is
`custom_components/robbie_advanced_cc/frontend/cleaning-control.js`; its
permanent resource URL is `/robbie_advanced_cc/cleaning-control.js`.

Do not place versions in resource URLs, README headings or frontend source.

## Required validation

```bash
python -m unittest discover -s tests -v
python scripts/check_source_syntax.py
node tests/test_card_runtime.js
python scripts/build_release.py --check
```

## Branches and releases

- `main`: reviewed stable releases
- `develop`: tested integration branch and beta releases
- `feature/<topic>` and `fix/<topic>`: focused work

Beta versions match `YYYY.M.PATCHbN`; stable versions match `YYYY.M.PATCH`.
`PATCH` identifies one coherent customer outcome or problem bundle. A new
bundle increments `PATCH` and starts at `b0`; only corrections to that same
bundle increment `N`. Promote a completed bundle to `YYYY.M.PATCH` before
starting the next one. Beta candidates are capped at `b9`; reaching the cap
requires closing or rescoping the bundle instead of creating `b10`. A new
calendar month starts at patch `.0b0`.
This is a hard branch invariant: a beta manifest on `main` or a stable manifest
on `develop` fails the release workflow instead of being silently ignored.
Release preparation opens a draft PR. Merging reviewed metadata on `develop`
publishes a beta; merging it on `main` publishes a stable release. Tags and
GitHub releases are immutable and must be created by the release workflow.
