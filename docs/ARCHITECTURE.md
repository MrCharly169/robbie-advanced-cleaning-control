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

## Adapters

The Generic adapter uses standard Home Assistant vacuum services. The Valetudo
adapter discovers optional MQTT-created sibling entities and translates mode,
fan and water profile values before delegating start/area cleaning to the
generic HA contract.

Future vendor presets may translate additional capabilities but must never own
cloud credentials. A configurable service-hook adapter is preferred over a new
direct cloud client.

## External bindings

Presence, Home zone, vacation, Schedule, notification routing, dashboard paths,
and to-do lists are config-entry options. They remain user-owned entities.
Removing this integration must not remove or rename them.
