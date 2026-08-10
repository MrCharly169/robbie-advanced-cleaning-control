# Robbie Advanced Cleaning Control

Robbie Advanced Cleaning Control is a local-first, vendor-neutral mission
planner for robot vacuum cleaners in Home Assistant. Valetudo receives enhanced
capability discovery while cloud-connected robots remain behind their existing
Home Assistant integrations. The planner never stores vendor cloud credentials.

The integration is currently a beta. Its technical version is defined only in
`custom_components/robbie_advanced_cc/manifest.json`.

## Product principles

- Home Assistant areas, entities and services are the public contract.
- Missions describe intent; adapters translate device dialects.
- Every blocked, skipped or postponed run has a stable reason code.
- One-shot state and missions survive Home Assistant restarts.
- Existing vacation, notification-route and to-do entities are referenced,
  never silently replaced or renamed.
- Unsupported controls are hidden instead of being presented as broken.
- English is used for source, identifiers and repository documentation. The
  Home Assistant UI and Card are available in English and German.

## Supported adapters

| Adapter | Behavior |
|---|---|
| Generic Home Assistant | Start, pause, return, fan speed and `vacuum.clean_area` when available |
| Valetudo | Generic behavior plus automatic sibling discovery for mode, fan, water, mop, map, locate and dock capabilities |
| Cloud integrations | Supported through their existing HA vacuum entity; no vendor credentials are added here |

## Installation

### HACS custom repository

1. Add this repository to HACS as an Integration repository.
2. Install **Robbie Advanced Cleaning Control**.
3. Restart Home Assistant.
4. Add the integration under **Settings -> Devices & services**.
5. Add the permanent dashboard resource:

```text
/robbie_advanced_cc/cleaning-control.js
```

Use resource type **JavaScript Module**. Do not add a version query parameter.

### Manual installation

Copy `custom_components/robbie_advanced_cc` into Home Assistant's
`custom_components` directory and restart Home Assistant.

## Configuration

One config entry manages one logical fleet. Select:

- one or more existing `vacuum.*` entities;
- an optional vacation `input_boolean`;
- an optional central notification `script` and route `input_text`;
- an optional `todo.*` entity;
- the dashboard path opened by notifications.

The adapter is selected automatically per vacuum. A Valetudo device continues
to communicate through Valetudo's MQTT discovery; this integration adds
planning rather than duplicating the device connection.

## Disposable Home Assistant lab

With Docker Desktop running on Windows, build and verify a fresh isolated lab:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ha_e2e\run_lab.ps1 -Fresh
```

The tested HA 2026.8.1 instance remains available only on
`http://127.0.0.1:18123/lovelace/cleaning`. It contains deterministic Valetudo
and cloud fixtures and never connects to a production HA, MQTT broker or
vendor cloud. See `docs/DEVELOPMENT.md` for lifecycle and control commands.

## Card

```yaml
type: custom:robbie-advanced-cleaning-card
status_entity: sensor.cleaning_planner_planner_status
```

The Card discovers the matching next-mission and last-decision sensors through
the config-entry ID. It renders in German when the Home Assistant language
starts with `de`; otherwise it uses English.

The previous experimental resource remains a compatibility loader:

```text
/robbie_advanced_cc/robbie-advanced-card.js
```

New dashboards must use the canonical resource.

## Mission example

Missions are persisted by the integration. The initial service API deliberately
accepts a complete mission object so the Card, automations and future setup
wizard all use the same contract.

```yaml
action: robbie_advanced_cc.add_mission
data:
  entry_id: YOUR_CONFIG_ENTRY_ID
  mission:
    id: sunday_deep_clean
    name: Sunday deep clean
    vacuum_entity_id: vacuum.valetudo_robbie_haus1_et1
    weekdays: [sun]
    start_time: "05:00"
    areas: [kitchen, living_room, bathroom]
    profile:
      mode: vacuum_and_mop
      fan: low
      water: medium
      passes: 1
    guards:
      vacation: block
      mop_missing: block
      vacuum_unavailable: postpone
      people_home: allow
    announce_before_minutes: 1440
```

Additional examples, including the migrated MeyersHaff schedule, live under
`examples/`.

## Entities

- Planner status and active mission
- Next mission timestamp with rooms and profile
- Last decision with resolution and stable reason code
- Planner readiness and per-adapter diagnostics
- Planner enabled switch
- Run, skip-once and postpone buttons

## Services

- `robbie_advanced_cc.add_mission`
- `robbie_advanced_cc.remove_mission`
- `robbie_advanced_cc.run_next`
- `robbie_advanced_cc.skip_next`
- `robbie_advanced_cc.postpone_next`

## Development and release discipline

The repository follows the same delivery contract as Smart Shading:

- `main` contains reviewed stable releases;
- `develop` is the integration branch;
- beta versions use `YYYY.M.PATCHbN` and stable versions use `YYYY.M.PATCH`;
- tags add the `v` prefix;
- the manifest is the only technical version source;
- every user-visible change updates tests, documentation and `CHANGELOG.md`;
- release preparation and release publication are separate maintainer gates.

See [Development](docs/DEVELOPMENT.md), [Architecture](docs/ARCHITECTURE.md),
[Baseline](docs/BASELINE.md), and the [Regression matrix](docs/REGRESSION_MATRIX.md).

## License

MIT
