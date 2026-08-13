# Architecture

## Boundary

Robbie Advanced Cleaning Control is a planner, not another device integration.
Installed Home Assistant integrations remain responsible for transport,
authentication and device entities.

```text
Home context -> Decision resolver -> Mission state machine -> Adapter -> HA vacuum
                         |                    |
                         +-> reason codes     +-> Card / notifications / history
```

## Mission contract

A mission owns recurrence, target vacuum, Home Assistant areas, portable
profile, guards and announcement time. Device topics, tokens and vendor service
payloads do not belong in the mission model.

## Decision priority

The resolver uses one fixed order:

1. mission enabled;
2. vacation;
3. vacuum availability;
4. required mop attachment;
5. presence policy;
6. ready.

Every result contains `allowed`, `resolution` and a stable `reason`. Adapters do
not override planner decisions.

## Runtime states

`idle -> announced -> preparing -> running -> completed`

Terminal or alternative states are `skipped`, `postponed`, `blocked` and
`failed`. `waiting` retains a due mission until configured presence entities
all report an empty home. Skip-once is consumed atomically by exactly one
mission occurrence.

Weekly recurrence remains the portable default. A mission may instead bind to
an existing `schedule.*` helper; its off-to-on transition becomes the start
signal while the helper's `next_event` attribute supplies the next badge time.

The planner-status sensor projects every mission together with its next
occurrence and a condition trace. Each condition carries a stable key,
enabled/passed state, resolution, contributing entity, current state and
friendly name. Numeric presence values use zero as empty and values above zero
as occupied; unknown values fail safe to occupied. This single
projection feeds the Simple readiness summary, the Advanced condition chips
and future notification explanations without duplicating guard logic in the
frontend.

## Adapters

The Generic adapter uses standard Home Assistant vacuum services. The Valetudo
adapter discovers optional MQTT-created sibling entities and translates mode,
fan and water profile values before delegating start/area cleaning to the
generic HA contract.

The Generic adapter does not apply arbitrary related mode or water selects.
`passes` is bounded mission metadata and is displayed by the current setup/Card,
but neither current adapter sends a repeat-pass command. Capability projection
must therefore not be confused with execution support.

`capabilities.py` projects Home Assistant vacuum area mappings, Valetudo-style
sibling selects and same-device cloud entities into one JSON-safe profile-choice
contract. The config flow and Planner Status sensor consume that same contract;
the Advanced Card therefore refreshes robot choices without duplicating vendor
heuristics in JavaScript.

Future vendor presets may translate additional capabilities but must never own
cloud credentials. A configurable service-hook adapter is preferred over a new
direct cloud client.

## External bindings

Presence, Home zone, vacation, Schedule, notification routing, dashboard paths,
and to-do lists are config-entry options. They remain user-owned entities.
Removing this integration must not remove or rename them.

The Card is served by the integration and idempotently registered in Lovelace
Storage resources. YAML resource mode remains user-owned and receives explicit
manual instructions instead. A one-time persistent notification contains the
Card, Badge and dashboard navigation examples after entry setup.
