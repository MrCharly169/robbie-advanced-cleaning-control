from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "robbie_advanced_cc"


def _load_dashboard_path_normalizer():
    source = COMPONENT / "config_flow.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_dashboard_path"
    )
    module = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"Any": object, "DEFAULT_DASHBOARD_PATH": "/lovelace/cleaning"}
    exec(compile(module, str(source), "exec"), namespace)
    return namespace["_dashboard_path"]


class NavigationTests(unittest.TestCase):
    def test_cleaning_control_path_is_absolute_and_local(self):
        normalize = _load_dashboard_path_normalizer()
        self.assertEqual(
            normalize(" /dashboard-home/utility-room "),
            "/dashboard-home/utility-room",
        )
        self.assertEqual(normalize(""), "/lovelace/cleaning")
        for invalid in (
            "dashboard-home/utility-room",
            "//other-host/path",
            "https://example.test/valetudo",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                normalize(invalid)

    def test_notifications_and_status_publish_the_control_destination(self):
        controller = (COMPONENT / "controller.py").read_text(encoding="utf-8")
        sensor = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        self.assertIn('"url": dashboard_path', controller)
        self.assertIn('"clickAction": dashboard_path', controller)
        self.assertIn('"action": "URI"', controller)
        self.assertIn('"uri": dashboard_path', controller)
        self.assertIn("[Open Cleaning Control]({dashboard_path})", controller)
        self.assertIn('"navigation_path": (', sensor)
        self.assertIn("self.planner.config.get(CONF_DASHBOARD_PATH)", sensor)

    def test_options_merge_preserves_untouched_optional_bindings(self):
        config_flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertIn("editable_keys = (", config_flow)
        self.assertIn("**{key: current[key] for key in editable_keys if key in current}", config_flow)
        self.assertIn('errors={CONF_DASHBOARD_PATH: "invalid_dashboard_path"}', config_flow)

    def test_native_subview_back_path_is_documented(self):
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        german = (ROOT / "docs" / "de" / "README.md").read_text(encoding="utf-8")
        self.assertIn("back_path", english)
        self.assertIn("back_path", german)


if __name__ == "__main__":
    unittest.main()
