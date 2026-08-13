# Legacy cleaning schedule migration

This neutral example describes how to migrate an existing cleaning automation
to Robbie without changing user-owned helpers or the robot connection.

## Example behavior

- Monday 09:00: one-room vacuum mission
- Wednesday 07:30: standard vacuum mission
- Friday 09:00: vacuum-and-mop mission
- optional advance announcement and skip-once
- existing vacation, notification-route and to-do helpers
- an existing dashboard path retained during transition

## Safe migration order

1. Install Robbie and select an already working `vacuum.example_robot` entity.
2. Bind existing vacation, notification and optional to-do entities.
3. Add and adapt the missions from `examples/legacy-migration-missions.yaml`.
4. Verify the next mission, profile application, Skip and Vacation behavior in
   the disposable lab or with the real robot prevented from starting.
5. Enable the Robbie planner.
6. Disable the old schedule automation only after verification.
7. Disable the old notification automation only after equivalent notifications
   have been observed.
8. Keep the previous dashboard path as an alias until all links have migrated.

No migration step deletes legacy helpers or automations automatically.
