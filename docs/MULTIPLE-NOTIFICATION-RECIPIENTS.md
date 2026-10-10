# Multiple notification recipients

Release: 2026.10.0b0. Scope: this integration; native Home Assistant configuration.

The notification route field accepts multiple input_text/input_select/select
helpers in setup and Connections. A previously stored scalar is displayed as a
single selected item and continues to work without migration or reconfiguration.
Selecting another helper preserves the existing recipient. Removing all selected
helpers retains the existing configured-router default behavior.

Each distinct resolved destination receives one call to the configured router,
with the same category, tag, message and navigation payload. A missing or
unavailable selected helper never redirects to another recipient. If every
selected route is unavailable, the message is retained as a Home Assistant
persistent notification. Runtime delivery deduplicates identical destinations.
The router remains responsible for transport and per-device language settings.
No real device notification is implied by a successful script invocation.

Native implementation reference:
https://www.home-assistant.io/docs/blueprint/selectors/
No custom device picker, registry, transport or recurring job is introduced.

Regression coverage:
- tests/test_controller_notifications.py: real controller fan-out, legacy scalar,
  empty selection, duplicate destinations and unavailable routes; native schema.
- Existing HTTP setup/options/restart lab preserves optional bindings.
- Native browser lab checks the actual Home Assistant form and selector.
- Run tests in the same HA Core/frontend as the target; release validation also
  exercises the existing stable/beta CI matrix. Hardware is simulated in the lab.

Maintenance must preserve the complete list when changing unrelated settings.
Never restore a single default recipient over an existing list. Scheduled tests
use controlled lab identities and do not add recipients or send physical pushes.
Existing cleaning schedules, execution and skip semantics remain unchanged.

Installation-specific recipients, acceptance receipts and backup references stay
in the private deployment workspace. Source publication and local tests do not
prove installation or handset delivery. Read back the installed version, route
list and unchanged mission configuration after deployment.
