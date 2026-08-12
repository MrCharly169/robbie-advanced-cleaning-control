# Changelog

## Unreleased


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
