# Development

## Local validation

Run from the repository root:

```bash
python -m unittest discover -s tests -v
python scripts/check_source_syntax.py
node tests/test_card_runtime.js
python scripts/build_release.py --check
python scripts/build_release.py
```

The fast suite contains no production Home Assistant URL or credentials.

For a persistent Windows development instance with Docker Desktop:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ha_e2e\run_lab.ps1 -Fresh
```

The command creates and tests a fresh HA 2026.8.1 instance, then leaves it
running at `http://127.0.0.1:18123/lovelace/cleaning`. The loopback-only lab
allows trusted-network browser access and also creates the disposable login
`e2e-owner` / `e2e-only-disposable-password`.

Use `scripts/dev.ps1 logs`, `scripts/dev.ps1 restart`, and
`scripts/dev.ps1 stop` for the running instance. Everything below `.dev/` and
`artifacts/ha-e2e/` is disposable and ignored by Git.

## Source of truth

- Version: `custom_components/robbie_advanced_cc/manifest.json`
- Development changes: `CHANGELOG.md -> Unreleased`
- Canonical frontend: `frontend/cleaning-control.js`
- Canonical resource: `/robbie_advanced_cc/cleaning-control.js`

## Real Home Assistant laboratory

Runtime, migration or registry work must additionally run in a disposable Home
Assistant container. The lab must use virtual vacuum and Valetudo-like fixture
entities, a loopback-only port and a temporary HA configuration. It must never
contact production Home Assistant, a production MQTT broker or vendor cloud.

The checked-in lab drives real HA onboarding, config flow and options flow. It
then verifies Valetudo and generic/cloud area cleaning, profile translation,
Mop and Vacation guards, mission CRUD, Skip/Postpone, maintenance discovery,
Card delivery and config-entry/mission/area-mapping persistence across an HA
restart. The CI shell runner executes the same lifecycle against stable and
beta images. Card layout or interaction changes additionally require a real HA
browser run.

The lab writes its default Lovelace dashboard through the Storage API, so it
remains editable in Home Assistant. It starts with the Simple Card and hybrid
Custom Badges; `configure_dashboard.mjs --card-mode advanced` is available for direct
visual inspection of the weekly planner.

The lab badges read their lifecycle from the real native Planner status enum,
delegate interactions through `hass-action`, and use native Lovelace Visibility.
No simulator, state override, navigation field or Badge-owned visibility menu
is involved.

## Releases

Release preparation and publication are separate gates. Prepare from tested
`develop`, review the generated metadata PR, and let the release workflow create
the immutable `v<manifest-version>` tag and ZIP. Stable promotion targets
`main`; beta preparation and publication target `develop`.
