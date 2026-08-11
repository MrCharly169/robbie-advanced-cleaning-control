# Changelog

## Unreleased

### Added

- Full HA 2026.8.1 Docker lifecycle lab with Valetudo and generic/cloud fixtures.
- Real config/options flow, mission, guard, Card and restart-persistence coverage.
- Four-step setup assistant with presence bindings and an optional starter mission.
- Per-robot dashboard badge with station state, next-run time, and Control Center navigation.
- Native Home Assistant Schedule helper triggers and persistent wait-until-empty execution.
- Local Home Assistant 2026.3+ brand icons and a reusable project logo.

### Fixed

- Avoid duplicate Valetudo fan commands when the sibling fan select is present.
- Expose config-entry ownership on all planner sensors for reliable Card discovery.
- Consume the HA frontend `hassApi` context for Card service actions.
- Wait for config-entry and vacuum area-mapping storage before restart tests.

## 2026.8.0b0 - 2026-08-10

### Added

- Initial vendor-neutral cleaning mission planner.
- Generic Home Assistant and enhanced Valetudo adapters.
- Persistent skip, postpone and explainable decision state.
- English/German config flow, entities and responsive Lovelace Card.
- SmartShading-derived CalVer, HACS, validation and release discipline.
