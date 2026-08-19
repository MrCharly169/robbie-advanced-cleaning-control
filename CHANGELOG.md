# Changelog

## Unreleased


## 2026.8.0b12 - 2026-08-19

### Added

- Card status details now explain why a run is waiting or why an active run
  failed, with localized Home/presence, robot, Vacation and mop reasons.
- The native Robbie Badge supports `display_mode: attention` and configurable
  `visible_states`, allowing an always-on Area Badge and a main-dashboard Badge
  that only appears for actionable states.

### Changed

- Cleaning modes use explicit localized labels, and a new mission defaults to
  Vacuum even when the robot's current live mode is Mop or Vacuum + Mop.
- Card and Badge robot marks use centered, bounded state markers with corrected
  proportions.

### Fixed

- Idle robot `unavailable` events no longer mark an unrelated planned run as
  failed. Error state is now reserved for an active mission being prepared or
  executed.

### Documentation

- Reworked the public English README and added a complete German customer guide,
  verified product boundaries, installation/uninstall guidance, real lab
  screenshots, architecture/adapter visuals, community templates, security and
  repository metadata guidance.

## 2026.8.0b11 - 2026-08-13

### Changed

- The Advanced overview counts each condition type once across all runs, so two runs sharing five conditions show `4/5` instead of `8/10` when Vacation mode blocks both.
- An active Vacation condition is labelled `Vacation mode active` / `Urlaubsmodus aktiv` instead of incorrectly describing the required inactive state.
- The Advanced Control Center uses symmetric mobile dialog padding and a centered, width-constrained content shell.


## 2026.8.0b10 - 2026-08-13

### Changed

- The automatically managed Lovelace module now always uses the canonical URL `/robbie_advanced_cc/cleaning-control.js`, independent of the installed integration version.
- Existing versioned or fingerprinted Robbie resource entries are migrated to the canonical URL during Home Assistant setup.


## 2026.8.0b9 - 2026-08-13

### Fixed

- `Save run` now preserves the submit button's native form action instead of cancelling it in the generic Card button handler, so the Card performs exactly one `robbie_advanced_cc.add_mission` service call.
- The real Chromium regression now runs with touch input and verifies unchanged dashboard scroll and a stable `ha-card` root while opening Advanced, adding, editing, and saving a run.


## 2026.8.0b8 - 2026-08-13

### Changed

- The compact Card now opens its Advanced Control Center and mission editor in a native Home Assistant dialog, keeping the dashboard Card height stable.

### Fixed

- Card buttons, robot selectors, and mission forms now use idempotent native DOM handlers after every keyed patch instead of capture/delegation fallbacks that could be inactive in Home Assistant's nested Shadow DOM.
- Opening Advanced or `Add run` no longer inserts large inline content into the dashboard layout; the Card opts out of browser scroll anchoring and keeps its `ha-card` root stable.
- Top and bottom `Add run` controls now have distinct DOM keys, preventing the keyed patcher from moving or replacing the wrong button.
- A real Chromium regression test now verifies native clicks, one render per update frame, stable dashboard scroll, stable Card/form/input nodes, preserved focus, and preserved unsaved form input.


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
