# Changelog

## Unreleased

## 2026.8.3b0 - 2026-08-22

- Keep iOS `url`, Android `clickAction` and the visible URI action aligned
  with the installation-specific Cleaning Control destination.
- Adopt ecosystem policy 1.5: native `back_path` stays on the destination
  Subview; Robbie does not add a Badge- or notification-route Back-path field.

## 2026.8.2b2 - 2026-08-22

- Route Robbie notifications to the configured Cleaning Control Card instead
  of a separate robot UI, publish that destination for dashboard builders and
  document Home Assistant's native `back_path` for reliable subview returns.
- Preserve untouched presence, vacation and notification bindings when only
  the dashboard destination is changed in the options flow.

- Extend the shared customer-documentation contract to private and MeyersHaff
  services with safe login guidance, Proxmox evidence and upstream monitoring.

- Join the shared living customer-documentation contract with one reusable
  capability description, four required languages, GitHub/version metadata and
  scheduled read-only inventory checks.

## 2026.8.2b1 - 2026-08-20

### Fixed

- Kept a future native `announced` mission as planning context instead of
  presenting it as active `waiting`; only the actual native `waiting` state now
  receives the warning treatment.
- Removed the secondary dock marker whenever the compact next-run label is
  visible, so weekday and date labels such as `Fr` remain unobstructed.
- Made the docked Badge's next-run label calendar-aware: it shows the time only
  for a run today, then tomorrow, the weekday or the date for later runs. The
  tooltip keeps the full localized date and time.
- Delegated native long-press and double-tap Badge interactions through Home
  Assistant's `hass-action` contract, including suppression of the synthetic
  click that follows a completed long press.
- Added Touch Events and the iOS context-menu gesture as long-press fallbacks,
  and stopped cancelling a valid hold merely because the pointer left the
  Badge's small visual bounds.
- Adopted Home Assistant ecosystem policy 1.2 for future planning semantics and
  collision-free hybrid Badge presentation.

## 2026.8.2b0 - 2026-08-19

### Hybrid native Custom Badge

- Restored the Robbie Custom Badge so robot logo, planner marker, next-run time,
  animation and semantic color remain available.
- Removed the Badge's own Vacuum, Planner-state and Navigation-path controls;
  the editor now uses Home Assistant's native entity selector.
- Delegated navigation through Home Assistant's `hass-action` contract and kept
  conditional display exclusively in the native Visibility tab.
- Adopted Home Assistant ecosystem policy 1.1 for the shared hybrid Badge contract.

### Home Assistant ecosystem governance

- Adopted the shared MeyersHaff Home Assistant ecosystem policy v1 and its
  repository guard, so HA-wide integration contracts remain documented and
  testable in this project.

## 2026.8.1b0 - 2026-08-19

### Native entity badges

- Switched recommended planner badges to Home Assistant's standard Entity Badge.
- Added a state-dependent icon to the native Planner enum for every lifecycle,
  including Waiting and Failed.
- Kept navigation in the native tap action and conditional display exclusively
  in Home Assistant's Visibility tab.
- Bounded future beta trains to `b0` through `b9`; a new completed scope
  increments the CalVer patch and restarts at `b0`.

## 2026.8.0b14 - 2026-08-19

### Fixed

- Restored `waiting` as the effective native Planner status after a restart whenever persisted missions are still waiting, so Home Assistant Visibility conditions recognize the state reliably.
- Removed the Badge state-override selector and ignored legacy override configuration; the Badge lifecycle now comes only from the native Planner status enum.
- Mapped every actionable Planner lifecycle directly to the Badge presentation, including Waiting, Preparing, Running, Dock service, Blocked and Failed.

## 2026.8.0b13 - 2026-08-19

### Native dashboard visibility

- The planner status sensor is now a native enum sensor, so every supported planner state is available in Home Assistant's state-condition dropdown.
- Robbie Badges no longer hide themselves through `display_mode` or `visible_states`; visibility is configured exclusively with Home Assistant's native Visibility tab.
- The Badge now uses the standard `entity` field for its planner status sensor while remaining compatible with existing `status_entity` configurations.
- Robbie's Badge geometry now matches the shared 36 px integration-badge style.

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
