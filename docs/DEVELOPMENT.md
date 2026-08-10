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
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 start
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 logs
```

Open `http://127.0.0.1:8123`. The configuration below `.dev/` is disposable
and ignored. Stop it with `scripts/dev.ps1 stop`.

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

The checked-in smoke lab currently proves clean startup on stable and beta HA.
The release roadmap extends it with config flow, mission CRUD,
restart persistence, adapter capability changes, entity-ID stability, unload,
reload, deletion and reinstall. Card changes additionally require a real HA
browser run at desktop and mobile widths.

## Releases

Release preparation and publication are separate gates. Prepare from tested
`develop`, review the generated metadata PR, and let the release workflow create
the immutable `v<manifest-version>` tag and ZIP. Stable promotion targets
`main`; beta preparation and publication target `develop`.
