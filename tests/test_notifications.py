from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "racc_notifications",
    ROOT / "custom_components" / "robbie_advanced_cc" / "notifications.py",
)
notifications = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(notifications)


class NotificationTests(unittest.TestCase):
    def test_default_announcement_is_previous_evening_not_24_hours_before(self):
        occurrence = datetime.fromisoformat("2026-08-26T06:00:00+02:00")
        self.assertEqual(
            notifications.mission_announcement_at(occurrence, 1440).isoformat(),
            "2026-08-25T20:00:00+02:00",
        )

    def test_custom_lead_time_and_disabled_announcement_remain_compatible(self):
        occurrence = datetime.fromisoformat("2026-08-26T06:00:00+02:00")
        self.assertEqual(
            notifications.mission_announcement_at(occurrence, 30).isoformat(),
            "2026-08-26T05:30:00+02:00",
        )
        self.assertIsNone(notifications.mission_announcement_at(occurrence, 0))

    def test_technical_mission_name_becomes_readable_humorous_copy(self):
        occurrence = datetime.fromisoformat("2026-08-26T06:00:00+02:00")
        title, message = notifications.mission_announcement_copy(
            robot="Robbie",
            mission_id="vac-only",
            mission_name="VacOnly",
            mode="vacuum",
            areas=["living_room", "kitchen"],
            occurrence=occurrence,
        )
        self.assertEqual(title, "Robbie's next mission will start")
        self.assertIn("Mission: Vacuum only.", message)
        self.assertIn("Start: tomorrow at 06:00.", message)
        self.assertIn("Area: living room, kitchen.", message)
        self.assertNotIn("VacOnly", message)

    def test_four_occurrences_rotate_through_four_stable_variants(self):
        messages = {
            notifications.mission_announcement_copy(
                robot="Robbie",
                mission_id="morning",
                mission_name="Morning clean",
                mode="vacuum",
                areas=[],
                occurrence=datetime.fromisoformat(
                    f"2026-08-{day:02d}T06:00:00+02:00"
                ),
            )[1]
            for day in range(26, 30)
        }
        self.assertEqual(len(messages), 4)

    def test_controller_uses_copy_timing_rooms_and_shared_navigation_sender(self):
        controller = (
            ROOT / "custom_components" / "robbie_advanced_cc" / "controller.py"
        ).read_text(encoding="utf-8")
        self.assertIn("mission_announcement_at(", controller)
        self.assertIn("mission_announcement_copy(", controller)
        self.assertIn("discover_profile_options(", controller)
        self.assertIn("await self._async_notify(", controller)
        self.assertNotIn('f"{mission.name}: next cleaning"', controller)

    def test_notification_copy_remains_english_and_deterministic(self):
        occurrence = datetime.fromisoformat("2026-08-26T06:00:00+02:00")
        kwargs = {
            "robot": "Robbie",
            "mission_id": "vac-mop",
            "mission_name": "Vac&Mop",
            "mode": "vacuum_and_mop",
            "areas": [],
            "occurrence": occurrence,
        }
        first = notifications.mission_announcement_copy(**kwargs)
        second = notifications.mission_announcement_copy(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first[0], "Robbie's next mission will start")
        self.assertIn("Mission: Vacuum and mop.", first[1])
        self.assertIn("Area: all areas.", first[1])
        self.assertNotIn("nächste", first[0])
        self.assertNotIn("Bereich", first[1])

    def test_default_robot_name_removes_only_generic_suffix(self):
        self.assertEqual(
            notifications.default_robot_display_name(
                "vacuum.robbie_robot", "Robbie Robot"
            ),
            "Robbie",
        )
        self.assertEqual(
            notifications.default_robot_display_name(
                "vacuum.downstairs", "Downstairs Tango"
            ),
            "Downstairs Tango",
        )

    def test_completion_title_uses_dynamic_robot_not_technical_mission(self):
        title, message = notifications.completion_notification_copy(
            robot="Robby-One",
            mission_name="VacOnly",
            mode="vacuum",
            metrics="1 h 47 min · 72.0 m²",
        )
        self.assertEqual(title, "🤖 Robby-One · Cleaning completed")
        self.assertNotIn("VacOnly", title)
        self.assertIn("Mission: Vacuum only.", message)
        self.assertIn("Result: 1 h 47 min · 72.0 m².", message)

    def test_config_card_and_badge_share_the_robot_name_mapping(self):
        config_flow = (
            ROOT / "custom_components" / "robbie_advanced_cc" / "config_flow.py"
        ).read_text(encoding="utf-8")
        sensor = (
            ROOT / "custom_components" / "robbie_advanced_cc" / "sensor.py"
        ).read_text(encoding="utf-8")
        frontend = (
            ROOT / "custom_components" / "robbie_advanced_cc" / "frontend"
            / "cleaning-control.js"
        ).read_text(encoding="utf-8")
        self.assertIn("async_step_robot_name", config_flow)
        self.assertIn("async_step_robot_names", config_flow)
        self.assertIn('"robot_names": {', sensor)
        self.assertIn("attributes?.robot_names?.[id]", frontend)
        self.assertIn("attributes?.robot_names?.[vacuumEntityId]", frontend)


if __name__ == "__main__":
    unittest.main()
