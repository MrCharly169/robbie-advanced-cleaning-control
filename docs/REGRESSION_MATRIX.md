# Regression matrix

| Area | Required behavior | Coverage |
|---|---|---|
| CalVer | Beta and stable formats remain branch-specific | `tests/test_package.py` |
| Mission parsing | Invalid time fails; passes are bounded; IDs are stable | `tests/test_models.py` |
| Scheduling | Weekdays and local next occurrence remain deterministic | `tests/test_models.py` |
| Presence wait | A due mission waits while a numeric Home counter is above zero and starts when it reaches zero | runtime E2E |
| Manual start | Card and native Play override only presence, consume a queued occurrence and preserve every safety guard | model/Card/runtime E2E |
| Planner disable | Presence changes cannot release queued missions while the Planner switch is off | runtime E2E |
| Schedule helper | `schedule.*` bindings survive mission serialization and trigger on activation | model/runtime E2E |
| Decision priority | Vacation precedes availability, mop and presence | `tests/test_models.py` |
| Explainability | Every result contains a stable reason and resolution | `tests/test_models.py` |
| Condition projection | Planner status exposes enabled/passed/resolution details for every mission guard | package/runtime E2E |
| Generic fallback | Area-less missions retain full-clean semantics | adapter/runtime E2E |
| Valetudo capability discovery | Missing siblings never produce controls | adapter/runtime E2E |
| Dynamic profile selectors | Setup and Advanced Card expose live room/mode/fan/water choices where discovered; absent room/fan/water controls are omitted and pass metadata remains bounded to 1–3 | runtime E2E, `tests/test_card_runtime.js` |
| Persistence | Missions, skip and postpone survive restart | runtime E2E |
| External ownership | Existing helpers are referenced, not created or removed | package/runtime E2E |
| UI languages | English and German translations expose the same keys | `tests/test_package.py` |
| Card runtime | Simple and Advanced modes register once and expose weekly runs and conditions | `tests/test_card_runtime.js` |
| Dashboard editing | The local lab persists its dashboard through Lovelace Storage mode | `tests/test_package.py`, runtime E2E |
| Card onboarding | The canonical module auto-registers once and the setup notification contains Card and Badge instructions | package/runtime E2E |
| Notification navigation | Routed and persistent notifications target the configured Cleaning Control Card path; optional bindings survive a path-only options update | navigation/unit + runtime E2E |
| Robot subview return | A separate robot UI uses Home Assistant's native `back_path` pointing to the Cleaning Control destination | documentation + live dashboard verification |
| Per-day profiles | Every weekday can open a preselected editor with independent room, mode, fan, water and passes | `tests/test_card_runtime.js`, runtime E2E |
| Badge runtime | Hybrid Custom Badge combines robot glyph, state marker and docked next run; mouse/keyboard delegate the native `tap_action` through `hass-action` | `tests/test_card_runtime.js` |
| Native error visibility | Generic vacuum and Valetudo sibling errors project Planner `failed` without an active run, outrank Vacation, expose details and clear back to the underlying state | model/runtime E2E, `tests/test_card_runtime.js` |
| Runtime priority | Direct native vacuum cleaning presents `running` even while an unrelated mission remains queued | `tests/test_models.py`, runtime observation |
| Badge simulation | Disposable lab can select every badge state and return to live robot state | package/runtime E2E, `tests/test_card_runtime.js` |
| Packaging | Manifest, HACS metadata, permanent resource and ZIP agree | `tests/test_package.py` |

Every production bug fix must add a regression row and automated test whenever
technically possible.
