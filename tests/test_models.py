from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "racc_models",
    ROOT / "custom_components" / "robbie_advanced_cc" / "models.py",
)
models = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
import sys
sys.modules[SPEC.name] = models
SPEC.loader.exec_module(models)


class MissionModelTests(unittest.TestCase):
    def mission(self, **overrides):
        raw = {
            "id": "sunday",
            "name": "Sunday clean",
            "vacuum_entity_id": "vacuum.robot",
            "weekdays": ["sun"],
            "start_time": "05:00",
            "profile": {"mode": "vacuum_and_mop", "passes": 1},
        }
        raw.update(overrides)
        return models.CleaningMission.from_dict(raw)

    def test_next_occurrence_uses_local_weekday_and_time(self):
        mission = self.mission()
        now = datetime.fromisoformat("2026-08-10T12:00:00+02:00")
        self.assertEqual(
            mission.next_after(now).isoformat(), "2026-08-16T05:00:00+02:00"
        )

    def test_same_day_past_time_moves_to_next_week(self):
        mission = self.mission()
        now = datetime.fromisoformat("2026-08-16T06:00:00+02:00")
        self.assertEqual(
            mission.next_after(now).isoformat(), "2026-08-23T05:00:00+02:00"
        )

    def test_invalid_time_is_rejected(self):
        with self.assertRaises(ValueError):
            self.mission(start_time="25:00")

    def test_passes_are_bounded(self):
        self.assertEqual(self.mission(profile={"passes": 0}).profile.passes, 1)
        self.assertEqual(self.mission(profile={"passes": 99}).profile.passes, 3)

    def test_decision_priority_and_reasons_are_stable(self):
        mission = self.mission()
        cases = (
            (
                models.PlannerContext(vacation=True, vacuum_available=False, mop_attached=False),
                "vacation_active",
            ),
            (models.PlannerContext(vacuum_available=False), "vacuum_unavailable"),
            (models.PlannerContext(mop_attached=False), "mop_missing"),
            (models.PlannerContext(mop_attached=True), "ready"),
        )
        for context, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(models.decide_mission(mission, context).reason, reason)

    def test_presence_guard_is_explicit(self):
        mission = self.mission(guards={"people_home": "wait"})
        decision = models.decide_mission(
            mission, models.PlannerContext(mop_attached=True, people_home=True)
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.resolution, "wait")
        self.assertEqual(decision.reason, "people_home")

    def test_round_trip_retains_portable_contract(self):
        mission = self.mission(areas=["kitchen", "bathroom"])
        self.assertEqual(models.CleaningMission.from_dict(mission.as_dict()), mission)

    def test_schedule_helper_binding_survives_round_trip(self):
        mission = self.mission(schedule_entity_id="schedule.cleaning")
        self.assertEqual(mission.schedule_entity_id, "schedule.cleaning")
        self.assertEqual(models.CleaningMission.from_dict(mission.as_dict()), mission)


if __name__ == "__main__":
    unittest.main()
