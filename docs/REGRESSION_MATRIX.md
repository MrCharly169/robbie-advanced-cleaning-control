# Regression matrix

| Area | Required behavior | Coverage |
|---|---|---|
| CalVer | Beta and stable formats remain branch-specific | `tests/test_package.py` |
| Mission parsing | Invalid time fails; passes are bounded; IDs are stable | `tests/test_models.py` |
| Scheduling | Weekdays and local next occurrence remain deterministic | `tests/test_models.py` |
| Presence wait | A due mission waits while occupied and starts when the home becomes empty | runtime E2E |
| Schedule helper | `schedule.*` bindings survive mission serialization and trigger on activation | model/runtime E2E |
| Decision priority | Vacation precedes availability, mop and presence | `tests/test_models.py` |
| Explainability | Every result contains a stable reason and resolution | `tests/test_models.py` |
| Condition projection | Planner status exposes enabled/passed/resolution details for every mission guard | package/runtime E2E |
| Generic fallback | Area-less missions retain full-clean semantics | adapter/runtime E2E |
| Valetudo capability discovery | Missing siblings never produce controls | adapter/runtime E2E |
| Persistence | Missions, skip and postpone survive restart | runtime E2E |
| External ownership | Existing helpers are referenced, not created or removed | package/runtime E2E |
| UI languages | English and German translations expose the same keys | `tests/test_package.py` |
| Card runtime | Simple and Advanced modes register once and expose weekly runs and conditions | `tests/test_card_runtime.js` |
| Dashboard editing | The local lab persists its dashboard through Lovelace Storage mode | `tests/test_package.py`, runtime E2E |
| Badge runtime | Native 36 px `ha-badge` combines robot glyph, state marker and docked next run; mouse/keyboard open Cleaning Control | `tests/test_card_runtime.js` |
| Packaging | Manifest, HACS metadata, permanent resource and ZIP agree | `tests/test_package.py` |

Every production bug fix must add a regression row and automated test whenever
technically possible.
