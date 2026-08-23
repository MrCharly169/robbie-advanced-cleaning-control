from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "custom_components"
    / "robbie_advanced_cc"
    / "adapters"
    / "valetudo_errors.py"
)
SPEC = importlib.util.spec_from_file_location("robbie_valetudo_errors", MODULE_PATH)
assert SPEC and SPEC.loader
valetudo_errors = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = valetudo_errors
SPEC.loader.exec_module(valetudo_errors)


class ValetudoDockErrorTests(unittest.TestCase):
    def test_l10s_ultra_tank_and_dustbag_errors_are_specific(self):
        cases = {
            "Mop Dock Clean Water Tank empty": (
                "freshwater",
                "Freshwater",
                "empty",
            ),
            "Mop Dock Wastewater Tank not installed or full": (
                "wastewater",
                "Wastewater",
                "full_or_missing",
            ),
            "Auto-Empty Dock dust bag full or dust duct clogged": (
                "dustbag",
                "Dustbag",
                "full_or_blocked",
            ),
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                attention = valetudo_errors.normalize_valetudo_dock_error(
                    message, "dock"
                )
                self.assertIsNotNone(attention)
                self.assertEqual(
                    (attention.key, attention.label, attention.value), expected
                )

    def test_unknown_dock_error_is_preserved_and_other_errors_are_ignored(self):
        attention = valetudo_errors.normalize_valetudo_dock_error(
            "Future dock warning", "dock"
        )
        self.assertEqual(attention.key, "generic")
        self.assertEqual(attention.value, "Future dock warning")
        self.assertIsNone(
            valetudo_errors.normalize_valetudo_dock_error(
                "Robot stuck or trapped", "navigation"
            )
        )
        self.assertIsNone(
            valetudo_errors.normalize_valetudo_dock_error("No error", "none")
        )
