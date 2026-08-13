# Changelog

## Unreleased


## 2026.8.0b7 - 2026-08-13

### Fixed

- Card controls, robot-profile changes, and mission submission now also bind directly to their stable DOM nodes, avoiding lost `Add run` clicks caused by Shadow DOM event retargeting in Safari and Home Assistant Mobile.

## 2026.8.0b6 - 2026-08-13

### Added

- A compact animated Robbie status mark for Card and Badge with cleaning, returning, waiting, vacation, idle, and error motion plus `prefers-reduced-motion` support.

### Fixed

- `Add run` now uses a capture-safe host interaction fallback and opens the mission editor beside the top or bottom control that was activated.

## 2026.8.0b5 - 2026-08-12

### Added

- A persistent post-setup mission editor under the integration's Configure action, including create, edit, enable/disable, live robot profile refresh, notification lead time, and confirmed deletion.
- A documented generic notification contract with zero-configuration Home Assistant notifications and an optional SmartShading-style central router script.

### Fixed

- Notification route helpers now pass their current state to the central router instead of passing the helper entity ID.
- Card resource fingerprinting now reads the JavaScript asset outside Home Assistant's event loop without changing the cache-buster contract.
- Card and Badge now coalesce Home Assistant state bursts to one render per animation frame and use narrow, visible-state signatures.
- Normal updates now morph stable Card and Badge DOM roots instead of replacing the Shadow DOM, preserving dashboard scroll, focus, open mission editing, unsaved form values, selected missions, and internal list scroll positions.
- A narrowly scoped startup recovery now rehydrates a Card that Home Assistant upgraded after a freshly fingerprinted resource finished loading.

## 2026.8.0b4 - 2026-08-12

### Changed

- Vacation Mode is now a global planner state with priority over robot idle, live badge overrides, announcements, native Schedule triggers, and queued timers.
- Card and Badge automatically discover the Planner and robot entities selected in the setup assistant; manual entity IDs are optional multi-robot overrides.

### Fixed

- Prevented continuous dashboard jumping by rebuilding the Card DOM only when planner-relevant data or local editor state actually changes.
- Added a dedicated purple Vacation presentation with palm-tree marker in both Card modes and the native-size Badge.

## 2026.8.0b3 - 2026-08-12

### Added

- Live robot capability discovery for Home Assistant area mappings, Valetudo MQTT selects, generic vacuum fan presets, and same-device cloud integration selects.
- A dedicated robot-profile step in the setup assistant with dynamic dropdowns for rooms, cleaning mode, fan strength, water level, and passes.

### Changed

- The Advanced Card now refreshes its profile dropdowns whenever a different robot is selected and hides unsupported controls.
- Planner status exposes normalized profile choices so setup and dashboard editing use the same robot-specific contract.
- Lovelace resource cache busting now includes a stable Card asset fingerprint in addition to the integration version.

### Fixed

- The Card now discovers the matching Planner Status sensor at runtime when `status_entity` is missing, stale, or renamed, instead of showing only a configuration warning.
- The HA E2E fixture now waits for Valetudo mode, fan, and water selects before validating dynamically generated setup fields.


## 2026.8.0b2 - 2026-08-12

### Added

- Numeric presence sources such as `zone.home`, `input_number`, `number`, `counter`, and numeric sensors; zero means empty and unknown values fail safe to occupied.
- Precise first-run fields in the setup assistant for rooms, vacuum/mop mode, fan strength, water level, and passes.
- Per-weekday add controls and independent day profiles in the Advanced Card, including an explicit Monday Hobby vacuum-only example.
- Automatic Lovelace Storage resource registration with release-aware cache busting and a one-time Card/Badge setup notification.

### Changed

- Advanced condition chips now name every configured presence entity and show its current value.
- Vacuum-only profiles always discard water settings before persistence.

## 2026.8.0b1 - 2026-08-12

### Added

- Full HA 2026.8.1 Docker lifecycle lab with Valetudo and generic/cloud fixtures.
- Real config/options flow, mission, guard, Card and restart-persistence coverage.
- Four-step setup assistant with presence bindings and an optional starter mission.
- SmartShading-style Simple and Advanced Card modes with a weekly run editor and visible per-run condition results.
- Native 36 px `ha-badge` per robot with station state, next-run time, and Control Center navigation.
- SmartShading-style composite badge symbol with a stable robot glyph, colored live-state marker, keyboard interaction, and render deduplication.
- Lab-only badge state simulator covering live, docked, idle, cleaning, returning, paused, waiting, error, and unavailable states.
- Editable Storage-mode Lovelace lab dashboard instead of a read-only YAML dashboard.
- Native Home Assistant Schedule helper triggers and persistent wait-until-empty execution.
- Local Home Assistant 2026.3+ brand icons and a reusable project logo.

### Fixed

- Let the Linux HA smoke lab clean up root-owned container files without turning successful tests red.
- Rely on successful HA API bootstrap/restart checks instead of a removed Home Assistant log phrase.
- Avoid duplicate Valetudo fan commands when the sibling fan select is present.
- Expose config-entry ownership on all planner sensors for reliable Card discovery.
- Consume the HA frontend `hassApi` context for Card service actions.
- Wait for config-entry and vacuum area-mapping storage before restart tests.
- Keep postponed Schedule-helper missions eligible for their replacement timer.

## 2026.8.0b0 - 2026-08-10

### Added

- Initial vendor-neutral cleaning mission planner.
- Generic Home Assistant and enhanced Valetudo adapters.
- Persistent skip, postpone and explainable decision state.
- English/German config flow, entities and responsive Lovelace Card.
- SmartShading-derived CalVer, HACS, validation and release discipline.
