# Robbie Advanced Cleaning Control

<p align="right"><strong>English</strong> · <a href="docs/de/README.md">Deutsch</a></p>

<p align="center">
  <img src="docs/images/robbie-advanced-cc-logo.png" width="220" alt="Robbie Advanced Cleaning Control logo">
</p>

<p align="center">
  <a href="https://github.com/MrCharly169/robbie-advanced-cleaning-control/actions/workflows/validate.yml"><img alt="Validate status" src="https://img.shields.io/github/actions/workflow/status/MrCharly169/robbie-advanced-cleaning-control/validate.yml?branch=main&amp;style=flat-square&amp;label=Validate"></a>
  <a href="https://github.com/MrCharly169/robbie-advanced-cleaning-control/releases"><img alt="Current GitHub release including prereleases" src="https://img.shields.io/github/v/release/MrCharly169/robbie-advanced-cleaning-control?include_prereleases&amp;style=flat-square&amp;label=Release"></a>
  <a href="https://github.com/MrCharly169/robbie-advanced-cleaning-control/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/MrCharly169/robbie-advanced-cleaning-control?style=flat-square&amp;label=Stars"></a>
  <a href="https://github.com/MrCharly169/robbie-advanced-cleaning-control/releases"><img alt="GitHub release downloads" src="https://img.shields.io/github/downloads/MrCharly169/robbie-advanced-cleaning-control/total?style=flat-square&amp;label=Release%20downloads"></a>
  <a href="#hacs-custom-repository"><img alt="HACS Custom" src="https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square"></a>
  <a href="hacs.json"><img alt="Home Assistant 2026.6 or newer" src="https://img.shields.io/badge/Home%20Assistant-2026.6%2B-18BCF2?style=flat-square"></a>
  <a href="LICENSE"><img alt="License MIT" src="https://img.shields.io/badge/License-MIT-2ea44f?style=flat-square"></a>
</p>

**Plan cleaning missions locally for robot vacuums that already exist in Home Assistant.**

Robbie is not a new manufacturer-cloud connector. It is a local, vendor-neutral
mission planner and dashboard for existing `vacuum.*` entities. A mission says
*what* should be cleaned and under which conditions; an adapter translates that
intent into capabilities already exposed by Home Assistant.

> **Release status:** Robbie has a stable release and an actively developed beta
> line. Stable is the safer default. Beta releases contain the newest Card and
> planner changes and may still change. The manifest is the source of truth for
> the installed version; the release badge above includes prereleases.

## Who is it for?

Robbie is for Home Assistant users who:

- already have one or more robot vacuums working as Home Assistant entities;
- want weekly missions, presence/vacation rules, rooms and cleaning profiles in
  one place;
- may use different vendors or a mixture of local and cloud-backed integrations;
- prefer Home Assistant entities and services over another set of credentials or
  another cloud account.

It is not a replacement for the integration that connected your robot to Home
Assistant. If the robot is not available as a working `vacuum.*` entity first,
Robbie cannot connect it.

## What Robbie does — and what it does not do

| Robbie does | Robbie does not |
|---|---|
| Stores recurring cleaning missions and one-shot planner state in Home Assistant | Log in to a robot manufacturer cloud |
| Evaluates planner enabled, vacation, availability, mop and presence conditions | Replace Valetudo, MQTT or a vendor integration |
| Detects available rooms, fan and water choices where implemented and omits absent selectors | Promise room cleaning, mopping, water control or repeat passes that the active adapter does not execute |
| Uses Home Assistant entities and services as its public interface | Publish vendor topics, tokens or proprietary cloud payloads |
| Shows the current planner state, next run, conditions and last decision reason | Keep a permanent run-history database |

![Robbie architecture: schedules and conditions flow through the mission planner, capability detection and an adapter to the existing Home Assistant vacuum integration and robot](docs/images/architecture.svg)

Schedules and conditions decide *when* a mission is eligible. The Mission
Planner owns intent and decision reasons. Capability Detection discovers what
Home Assistant currently exposes. The adapter applies only supported choices,
then delegates device communication to the existing Home Assistant integration.

## Screenshots

The screenshots below come from the repository's disposable Home Assistant lab
and its real-Card browser regression fixture, using neutral test data. No
production Home Assistant instance, robot account or manufacturer cloud is
involved; the UI is rendered by the production Card resource.

| Simple Card | Advanced Card |
|---|---|
| ![Simple Robbie Card showing the next run and quick actions](docs/images/simple-card.png) | ![Advanced Robbie Card showing a weekly plan and condition results](docs/images/advanced-card.png) |
| Next run, readiness and Run/Skip/Postpone controls. | Seven-day overview, profiles and explainable conditions. |

| Mission editor | Per-robot badge |
|---|---|
| ![Robbie mission editor with neutral schedule and cleaning profile choices](docs/images/mission-editor.png) | ![Hybrid Home Assistant robot badge showing docked state and the next run](docs/images/robot-badge.png) |
| Edit timing, presence behavior, robot, rooms and supported profile choices. | A hybrid 36 px Custom Badge with native configuration, live state and optional next-run time. |

## Quick Start

1. Confirm that your robot already works as a `vacuum.*` entity in Home
   Assistant 2026.6 or newer.
2. [Add this repository to HACS](#hacs-custom-repository) as type
   **Integration**, install Robbie and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**, search for
   **Robbie Advanced Cleaning Control**, and complete the five setup steps.
4. Add the Card through the dashboard editor. In Storage mode, Robbie registers
   its frontend resource automatically.
5. Start with one neutral weekly mission, verify the detected rooms/profile
   choices, then enable presence or vacation behavior. For the Generic adapter,
   keep mode at Vacuum and passes at 1 unless its documented execution limits
   are acceptable to you.

Minimal Card:

```yaml
type: custom:robbie-advanced-cleaning-card
mode: simple
```

Minimal Custom Badge with native Home Assistant configuration:

```yaml
type: custom:robbie-vacuum-badge
entity: sensor.example_planner_status
tap_action:
  action: navigate
  navigation_path: /lovelace/cleaning
```

Select the planner status sensor created by this integration.

## Installation

### HACS custom repository

This project is currently installed as a **custom** HACS repository; the HACS
Custom badge is not a claim that Robbie is in the HACS default store.

1. In HACS, open the top-right menu and select **Custom repositories**.
2. Enter
   `https://github.com/MrCharly169/robbie-advanced-cleaning-control`.
3. Select **Integration** and choose **Add**.
4. Open **Robbie Advanced Cleaning Control**, choose a release and download it.
   Prefer the latest non-prerelease release unless you intentionally want beta.
5. Restart Home Assistant.

You can also open the HACS repository dialog through this
[Home Assistant link](https://my.home-assistant.io/redirect/hacs_repository/?owner=MrCharly169&repository=robbie-advanced-cleaning-control&category=integration).

HACS reads the integration from `custom_components/robbie_advanced_cc`. Release
assets are named `robbie-advanced-cc-v<VERSION>.zip`; **Release downloads** in
the badge row counts downloads of GitHub release assets, not HACS installations,
users or devices.

### Manual installation

1. Download a release asset named `robbie-advanced-cc-v<VERSION>.zip` from
   [GitHub Releases](https://github.com/MrCharly169/robbie-advanced-cleaning-control/releases).
2. Extract it so this file exists in your Home Assistant configuration:
   `custom_components/robbie_advanced_cc/manifest.json`.
3. Restart Home Assistant.
4. Add the integration under **Settings → Devices & services**.

Do not copy only the ZIP's repository root and do not rename the
`robbie_advanced_cc` integration directory.

## Set up the integration and frontend

The setup assistant creates one logical planner for an apartment, floor or
robot fleet. It asks for:

- one or more existing `vacuum.*` entities;
- optional presence entities (`person`, `device_tracker`, `binary_sensor`,
  `input_boolean`, `zone`, numeric sensors/helpers and counters);
- an optional vacation `input_boolean`;
- an optional first mission, weekly time or existing `schedule.*` helper;
- live room/profile choices for the first mission;
- optional notification router, route helper, to-do binding and dashboard path;
- completion and dock/maintenance notification switches, plus the policy for
  direct starts outside Robbie (`match_single_pending` by default or
  `keep_pending`).

The dashboard path is specifically the complete Home Assistant path of the view
that contains the Robbie Cleaning Control Card, for example
`/lovelace/cleaning`. Robbie notifications always open this control destination;
they never use a separate Valetudo or manufacturer UI as their target.

After setup, use **Settings → Devices & services → Robbie Advanced Cleaning
Control → Configure** to edit connections or persisted missions.

### Frontend resource

The canonical JavaScript module is always:

```text
/robbie_advanced_cc/cleaning-control.js
```

- **Storage-mode dashboards:** Robbie registers or migrates this resource
  automatically and shows a one-time dashboard setup notification.
- **YAML-mode resources:** add it manually as a JavaScript module:

  ```yaml
  lovelace:
    resources:
      - url: /robbie_advanced_cc/cleaning-control.js
        type: module
  ```

The legacy `/robbie_advanced_cc/robbie-advanced-card.js` URL is only a
compatibility loader. Use the canonical URL for new dashboards.

## Card and Badge

### Simple Card

The Simple Card is the daily view. It shows planner state, the next mission,
condition readiness and narrow actions to run now, skip once or postpone by 60
minutes. Its Advanced button opens the Control Center without changing the saved
dashboard configuration.

**Run now** is an intentional manual start. It may override a configured
presence wait, but it never overrides a disabled Planner, Vacation mode, robot
availability/errors or a required mop attachment. Scheduled runs and direct
service calls without `manual: true` continue to evaluate every condition.

### Advanced Card

The Advanced Card/Control Center adds:

- a seven-day run overview;
- per-mission condition chips and current values;
- create, edit, enable/disable and remove flows;
- robot-specific room/segment, mode, fan and water choices where exposed, plus
  mission pass metadata bounded to 1–3;
- immediate refresh when the selected robot changes.

Room, fan and water selectors are omitted when those choices are not detected.
Mode always has at least the portable `vacuum` default and passes always offers
1–3. Important current limitation: `passes` is stored/displayed but neither
adapter executes a repeat-pass command; the Generic adapter also does not apply
arbitrary related mode or water selects. The Card uses German labels when the
Home Assistant language starts with `de`; otherwise it uses English. Motion
respects the browser's reduced-motion setting.

To make Advanced the saved default:

```yaml
type: custom:robbie-advanced-cleaning-card
mode: advanced
```

### Hybrid planner Badge

Use Robbie's Custom Badge with the native planner status sensor. A future
`announced` mission remains planning context: the Badge shows the time only for
a run today, then tomorrow, a weekday or a date. The secondary marker is hidden
while this schedule label is visible. Only an actual native `waiting` state
receives the warning marker and color. Entity, navigation and conditional
display remain configured through Home Assistant's native entity selector,
Interactions tab and Visibility tab.

Any active error from a managed Home Assistant vacuum or Valetudo error sensor
has attention priority over idle, waiting and Vacation presentation. The native
Planner status becomes `failed` (shown as **Error**), exposes the normalized
error source/message and therefore satisfies an existing native Visibility rule
for `failed` even when no cleaning run is active.

The same Badge can be configured independently in two dashboard views. Omit
`visibility` in an Area view so it remains permanently visible. In a main
dashboard, use only Home Assistant's native Visibility tab and the Planner
status enum:

```yaml
# Area view
type: custom:robbie-vacuum-badge
entity: sensor.example_planner_status
tap_action:
  action: navigate
  navigation_path: /lovelace/cleaning
```

```yaml
# Main dashboard
type: custom:robbie-vacuum-badge
entity: sensor.example_planner_status
tap_action:
  action: navigate
  navigation_path: /lovelace/cleaning
visibility:
  - condition: or
    conditions:
      - condition: state
        entity: sensor.example_planner_status
        state: waiting
      - condition: state
        entity: sensor.example_planner_status
        state: running
      - condition: state
        entity: sensor.example_planner_status
        state: failed
```

Home Assistant's native state and Visibility dropdowns receive all values from
the enum sensor. The Badge editor has no Vacuum, navigation-path, Hidden or
state menu. Each Lovelace view still owns its own Badge instance; one instance
cannot move between views.

### Notification and robot-view navigation

Keep the two destinations separate:

- `dashboard_path` in Robbie's setup/options is the view containing the Cleaning
  Control Card and is the target of routed mobile and persistent notifications.
- The Badge's native `tap_action` may navigate to a separate Valetudo or cloud
  robot view.

If that robot view is a Home Assistant subview, give it the same fixed native
return destination. This also works when the subview is opened from a deep link
without useful browser history:

```yaml
title: Robot
path: robot
subview: true
back_path: /lovelace/cleaning
```

Robbie exposes the configured value as
`sensor.<planner>_planner_status` → `dashboard.navigation_path` so dashboard
builders can reuse it. Home Assistant owns the native subview back button and
Badge interaction; Robbie does not replace browser history.

## Missions, weekly schedules and conditions

A mission contains a name, target vacuum, recurrence, optional rooms/segments,
a portable cleaning profile, guards and an announcement lead time. Missions
describe desired cleaning; adapters translate only the profile fields for which
they have an implementation. Stored intent is not proof that every field was
sent to the robot.

Weekly weekdays plus a local start time are the portable default. A mission may
instead reference an existing Home Assistant `schedule.*` helper. Its off-to-on
transition triggers the mission, and its `next_event` supplies the next-run time.

The fixed decision order is:

1. mission enabled (the Planner Enabled switch separately controls automatic
   scheduling);
2. vacation;
3. vacuum availability;
4. required mop attachment, when detected;
5. presence behavior;
6. ready to run.

See [the neutral service examples](examples/missions.yaml) for the complete
mission object and service calls.

### Presence, vacation, waiting, skipping and postponing

| Situation | Behavior implemented by Robbie |
|---|---|
| Somebody is home + `wait` | The due mission remains pending and starts when every configured presence source reports an empty home. Pending mission IDs are persisted across restart. |
| Somebody is home + `allow` | The mission can start immediately. |
| Somebody is home + `skip` | That occurrence is consumed without starting the robot. |
| Presence is unknown/unavailable | Fail-safe: treated as occupied, so `wait` does not start merely because a source disappeared. Numeric `0` is empty; values above `0` are occupied. |
| Vacation is on | Global vacation state suppresses announcements and scheduled execution. When vacation ends, Robbie schedules the next eligible occurrence; it does not run a vacation backlog. |
| Vacuum unavailable | The default guard postpones the mission by 60 minutes. The decision reason remains visible. |
| Mop explicitly reported missing | Mop and vacuum-plus-mop missions use the configured mop guard (block by default). Unknown mop state is not treated as confirmed missing. |
| **Skip once** | Arms the next mission ID, persists it and consumes it on exactly one occurrence without a device command. |
| **Postpone** | Stores a replacement time. The Card uses 60 minutes; the service accepts 1–1440 minutes. |
| Direct start through the native vacuum/Valetudo UI | When exactly one due waiting mission targets that robot, the default policy associates and consumes that occurrence. `keep_pending` leaves it queued instead. Ambiguous matches are never guessed. |
| **Mark waiting run handled** | Removes only the due waiting occurrence and keeps the recurring weekly mission. The Advanced Card exposes this action on waiting missions. |
| Adapter command fails | Robbie sets a failed state/reason and raises the error; it does not report a successful start. |

Planner status, next-mission and last-decision entities keep the current outcome
inspectable. Waiting, postpone and skip-once state survive restart. Robbie does
**not** currently maintain a durable audit log of every old blocked or skipped
run; use Home Assistant history/automations if permanent run history is required.
When an already-waiting mission is edited, Robbie immediately checks whether
that same due weekday/time or native Schedule binding still exists. Removing
today, moving the due time, disabling the mission or changing its Schedule
binding discards only the stale waiting occurrence and recalculates the plan.

### Completion and dock attention notifications

When enabled, a real transition from cleaning to docked sends one completion
notification through the configured router (or Home Assistant persistent
notifications). Valetudo current-statistics sensors add duration and cleaned
area when available. The `completed` status remains visible for five minutes
before Robbie returns to idle or another genuine waiting occurrence.

Valetudo 2026.05+ Freshwater, Wastewater, Dustbag and Detergent dock-component
sensors are discovered when the robot/firmware exposes them. Robbie also reads
active `DustBinFullValetudoEvent` data from the Valetudo Events sensor. A new
empty/full/missing attention state sends one notification and remains persisted
to prevent duplicates after restart. Missing entities are reported as
unsupported; Robbie does not invent tank state from the generic dock status.
Models such as the Dreame L10S Ultra expose tank and dustbag problems only as
temporary Valetudo error states. Robbie translates those dock errors into the
same immediate, deduplicated maintenance notifications while retaining unknown
future dock messages verbatim.
After a mop run without readable Freshwater/Wastewater components, the
completion notification therefore includes a neutral reminder to check both
dock containers.

## Adapters and compatibility

![Comparison of Robbie's Generic adapter, Valetudo enhancement and an existing cloud integration, separating Robbie planning from delegated device communication](docs/images/adapter-comparison.svg)

| Path | Detection and mission execution | Directly handled by Robbie | Still handled elsewhere |
|---|---|---|---|
| **Generic Home Assistant adapter** | Used for any managed vacuum not detected as Valetudo. Reads standard `supported_features`, vacuum area mappings, fan presets and related same-device entities. Sets standard fan speed when supported, calls `vacuum.clean_area` for known areas, otherwise calls `vacuum.start`. It does not apply generic mode/water selects or repeat `passes`. | Planning, guards, capability projection and those standard HA service calls. | The installed vacuum integration transports commands and owns authentication. |
| **Valetudo enhancement** | Selected when the vacuum entity ID or friendly name contains `valetudo`. Adds sibling discovery for mode, fan, water, mop attachment, segments/maps, locate/auto-empty, current run statistics, dock components, events and maintenance sensors. Applies exact Valetudo-style mode/fan/water sibling selects before the Generic start/area action. It does not execute `passes`. | Enhanced discovery, implemented profile translation, completion metrics and dock/mop/maintenance projection. | Valetudo's existing MQTT-discovered HA entities and MQTT transport. Robbie does not connect to MQTT. |
| **Existing cloud integration** | Uses the Generic adapter. Same-device room/profile entities can be discovered for presentation when the installed integration exposes them, but only standard Generic actions above are executed. | The same vendor-neutral planner and HA service boundary. | Vendor cloud transport, account login, tokens, rate limits and supported robot features. |

Capability discovery does not manufacture support. Detected map, locate or
auto-empty capability signals are diagnostics/discovery information unless a
documented Robbie Card, entity or service actually exposes an action. The
currently public Robbie services are `add_mission`, `remove_mission`,
`resolve_pending`, `run_next`, `skip_next` and `postpone_next`.

## Updates and uninstalling

### Update

- **HACS:** open Robbie in HACS, choose **Update** or **Redownload**, select the
  intended stable/beta release, restart Home Assistant and refresh the dashboard.
- **Manual:** replace `custom_components/robbie_advanced_cc` with the directory
  from the new release asset, then restart Home Assistant.

The frontend resource URL remains unversioned across upgrades. Do not add a
`?v=` query manually.

### Uninstall

1. Remove Robbie Cards and Badges from dashboards.
2. Delete the Robbie config entry under **Settings → Devices & services**.
3. Remove Robbie through HACS, or delete only
   `custom_components/robbie_advanced_cc` for a manual installation.
4. Remove `/robbie_advanced_cc/cleaning-control.js` from dashboard resources if
   it remains (required for YAML resources and possibly after full removal).
5. Restart Home Assistant.

Robbie never deletes or renames the vacuum, presence, vacation, schedule,
notification, route or to-do entities you selected. The current integration has
no removal hook that deletes its `.storage/robbie_advanced_cc.<entry_id>` planner
file; do not hand-edit `.storage` while Home Assistant is running. Back up Home
Assistant before any manual storage cleanup.

## Local-first, credentials and privacy

- Robbie asks for entity IDs and service bindings, not manufacturer usernames,
  passwords, API keys or tokens.
- Manufacturer/cloud credentials remain inside the existing Home Assistant
  integration that owns the robot connection.
- Production code contains no vendor-cloud client, telemetry or analytics call.
  It serves the Card locally and calls Home Assistant services.
- Home Assistant storage holds mission definitions and planner one-shot state.
  Config entries hold selected entity IDs, notification bindings and dashboard
  path.
- Optional notification-router scripts can send messages wherever *your script*
  sends them; that external behavior is not controlled by Robbie.
- Downloaded diagnostics redact the configured notification script and route,
  but still include selected entity IDs and adapter capability information.
  Review diagnostics before sharing them.

## FAQ and troubleshooting

### Does Robbie connect directly to my robot or its cloud?

No. First install and configure the appropriate Home Assistant vacuum
integration (or Valetudo/MQTT). Robbie plans against the entities it exposes.

### Is manufacturer X supported?

There is no manufacturer whitelist. A working standard `vacuum.*` entity can use
the Generic adapter, but exact rooms and profile controls depend on what that
entity and its related Home Assistant entities expose. Only Valetudo has a
dedicated enhanced adapter today.

### Why is a room, fan, water or mop control missing?

Robbie omits room, fan and water selectors it cannot detect. Check the selected robot's
`supported_features`, Home Assistant vacuum area mapping, fan presets and
same-device select/sensor entities. A mission with no detected areas falls back
to a full `vacuum.start`; it does not pretend that room cleaning succeeded.

### Why did a scheduled run not start?

Check, in order: Planner Enabled, vacation input, vacuum availability, mop
attachment and presence sources. Then inspect the **Last decision** sensor and
the Advanced Card condition chips. Unknown presence is intentionally treated as
occupied.

### The Card or Badge is missing

1. Confirm Home Assistant 2026.6+ and restart after installation.
2. Open dashboard resources and verify exactly one JavaScript module at
   `/robbie_advanced_cc/cleaning-control.js`.
3. For YAML resource mode, add it manually.
4. Refresh the browser cache after confirming the resource.
5. Use `entry_id` or `status_entity` when several planners make discovery
   ambiguous.

### Where can I get useful diagnostics?

Open **Settings → Devices & services → Robbie → Download diagnostics**. Review
entity IDs before attaching the file. Never post Home Assistant access tokens,
manufacturer credentials, cookies, `.storage` auth files or full configuration
backups.

### Why did my selected mode, water level or passes not reach the robot?

The Valetudo adapter applies its exact mode/fan/water sibling selects. The
Generic adapter only applies standard Home Assistant fan speed, area cleaning
and start. Repeat passes are currently metadata only in both adapters. This is a
known functional boundary, not a successful device command.

## Support, security and contributing

- Search or open a [bug report](https://github.com/MrCharly169/robbie-advanced-cleaning-control/issues/new?template=bug_report.yml).
- Propose a [feature](https://github.com/MrCharly169/robbie-advanced-cleaning-control/issues/new?template=feature_request.yml).
- Read [Security](SECURITY.md) before reporting a vulnerability.
- Contributions are welcome under [CONTRIBUTING.md](CONTRIBUTING.md) and the
  [Code of Conduct](CODE_OF_CONDUCT.md).

Reports should include the adapter, an anonymized vacuum entity ID, Home
Assistant and Robbie versions, reproducible steps and reviewed diagnostics.
They must never include credentials.

## License and voluntary support

Robbie Advanced Cleaning Control is open source under the [MIT License](LICENSE).
Private and commercial use are permitted subject to the license, including its
copyright/notice and warranty terms. There is no separate commercial license.

Voluntary sponsorship is not a license fee. A verified sponsorship or Buy Me a
Coffee URL has not yet been provided, so no donation badge or payment link is
published. Once verified, voluntary support can help fund development, device
compatibility work, testing and documentation.

## Developer details

Home Assistant entities and services are the public runtime contract. The
manifest is the only version source, and release ZIPs preserve the existing HACS
layout. Runtime, adapter and planner behavior is documented in:

- [Architecture](docs/ARCHITECTURE.md)
- [Supported baseline](docs/BASELINE.md)
- [Development and disposable HA lab](docs/DEVELOPMENT.md)
- [Regression matrix](docs/REGRESSION_MATRIX.md)
- [Release history](CHANGELOG.md)
- [Suggested GitHub metadata and manual settings](docs/GITHUB_METADATA.md)
