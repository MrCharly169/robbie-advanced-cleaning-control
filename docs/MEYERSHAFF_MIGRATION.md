# MeyersHaff migration

The current Robbie setup is the reference migration, not a hard-coded product
default.

## Imported behavior

- Wednesday 07:30: vacuum, medium fan
- Friday 05:00: vacuum, low fan
- Sunday 05:00: vacuum and mop, medium water
- 24-hour announcement and skip-once
- `input_boolean.vacation_mode`
- `script.central_notification_router`
- logical notification-route helpers
- `todo.household`
- compatibility dashboard path `/haus1-et1-tablet/valentudo`

## Safe migration order

1. Install the integration and select `vacuum.valetudo_robbie_haus1_et1`.
2. Bind existing vacation, router, route and to-do entities.
3. Add the three missions from `examples/meyershaff-missions.yaml`.
4. Verify next mission, profile application, Skip and Vacation in dry operation.
5. Enable the planner.
6. Disable the old schedule automation only after verification.
7. Disable the old notification automation only after equivalent notifications
   have been observed.
8. Keep the old dashboard path as an alias until every notification and card
   reference has migrated.

No migration step deletes legacy helpers or automations automatically.
