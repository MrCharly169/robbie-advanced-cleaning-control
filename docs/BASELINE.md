# Supported baseline

## Compatibility contract

- Home Assistant 2026.6 or newer
- Integration domain `robbie_advanced_cc`
- Config-entry schema version 1
- Canonical resource `/robbie_advanced_cc/cleaning-control.js`
- Legacy loader `/robbie_advanced_cc/robbie-advanced-card.js`
- English repository documentation and bilingual English/German HA UI

## Behavior contract

- Mission intent remains independent of vendor transport.
- Missing room, fan and water choices are omitted and device commands are never
  simulated as successful. Portable mode/pass metadata can still exist without
  an execution mapping; the Generic adapter does not apply arbitrary mode/water
  selects, and neither current adapter executes repeat passes.
- Vacation, unavailable vacuum and missing mop guards remain deterministic.
- Skip-once, postponements and missions survive restarts.
- Generic vacuums retain full-clean support even without areas or profile
  controls.
- Valetudo uses its existing MQTT-discovered Home Assistant entities.
- Card controls call narrow integration services and never vendor topics.
- Existing user helpers, notification routes and to-do entities remain owned by
  the user.
- Every non-run decision remains inspectable through a stable reason code.

The executable baseline is maintained in `tests/` and documented by the
regression matrix.
