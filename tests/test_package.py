from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

from scripts import build_release, release_changelog

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "robbie_advanced_cc"


def leaf_paths(value, prefix=""):
    result = set()
    if isinstance(value, dict):
        for key, child in value.items():
            result |= leaf_paths(child, f"{prefix}.{key}" if prefix else key)
    else:
        result.add(prefix)
    return result


class PackageTests(unittest.TestCase):
    def test_manifest_owns_the_august_calver(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["domain"], "robbie_advanced_cc")
        self.assertRegex(manifest["version"], r"^2026\.8\.\d+(?:b\d+)?$")

    def test_translations_have_identical_contract(self):
        english = json.loads((COMPONENT / "translations" / "en.json").read_text(encoding="utf-8"))
        german = json.loads((COMPONENT / "translations" / "de.json").read_text(encoding="utf-8"))
        self.assertEqual(leaf_paths(english), leaf_paths(german))

    def test_frontend_has_one_canonical_implementation(self):
        canonical = (COMPONENT / "frontend" / "cleaning-control.js").read_text(encoding="utf-8")
        legacy = (COMPONENT / "frontend" / "robbie-advanced-card.js").read_text(encoding="utf-8")
        self.assertIn('customElements.define("robbie-advanced-cleaning-card"', canonical)
        self.assertEqual(legacy.strip(), 'import "./cleaning-control.js";')
        self.assertNotRegex(canonical, r"2026\.\d+")

    def test_card_resource_and_numeric_presence_are_first_class(self):
        frontend = (COMPONENT / "frontend.py").read_text(encoding="utf-8")
        config_flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        controller = (COMPONENT / "controller.py").read_text(encoding="utf-8")
        self.assertIn("async_register_card_resource", frontend)
        self.assertIn('"res_type": "module"', frontend)
        self.assertIn("async_show_setup_notification", frontend)
        for domain in ("zone", "sensor", "number", "input_number", "counter"):
            self.assertIn(f'"{domain}"', config_flow)
        self.assertIn('float(state.state) > 0', controller)

    def test_release_package_is_installable(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "release.zip"
            version = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))["version"]
            build_release.build(output, f"v{version}")
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
        self.assertIn("custom_components/robbie_advanced_cc/manifest.json", names)
        self.assertIn("custom_components/robbie_advanced_cc/frontend/cleaning-control.js", names)
        self.assertIn("custom_components/robbie_advanced_cc/brand/icon.png", names)
        self.assertIn("hacs.json", names)

    def test_release_channels_are_unambiguous(self):
        self.assertEqual(release_changelog.validate_version("beta", "2026.8.1b2"), "2026.8.1b2")
        self.assertEqual(release_changelog.validate_version("stable", "2026.8.1"), "2026.8.1")
        for channel, version in (("beta", "2026.8.1"), ("stable", "2026.8.1b2"), ("beta", "v2026.8.1b2")):
            with self.subTest(channel=channel, version=version):
                with self.assertRaises(RuntimeError):
                    release_changelog.validate_version(channel, version)

    def test_release_workflow_rejects_crossed_branch_versions(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("main requires YYYY.M.PATCH", workflow)
        self.assertNotIn("Manifest synchronization is not a publishable", workflow)

    def test_stable_release_can_aggregate_beta_history(self):
        text = (
            "# Changelog\n\n## Unreleased\n\n"
            "## 2026.8.0b1 - 2026-08-09\n\n### Fixed\n\n- A fix.\n\n"
            "## 2026.7.0 - 2026-07-01\n\n- Previous stable.\n"
        )
        parsed = release_changelog.sections(text)
        notes = release_changelog._release_notes("stable", parsed, "")
        self.assertIn("Included beta release history", notes)
        self.assertIn("#### 2026.8.0b1", notes)
        self.assertIn("##### Fixed", notes)
        self.assertNotIn("Previous stable", notes)

    def test_language_policy_is_deliberate(self):
        policy = (ROOT / "docs" / "LANGUAGE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("English and German", policy)
        self.assertTrue((COMPONENT / "strings.json").is_file())

    def test_lab_dashboard_is_storage_editable(self):
        configuration = (ROOT / "e2e" / "ha" / "configuration.yaml").read_text(encoding="utf-8")
        dashboard_setup = (ROOT / "scripts" / "ha_e2e" / "configure_dashboard.mjs").read_text(encoding="utf-8")
        self.assertNotIn("mode: yaml", configuration)
        self.assertIn('call("lovelace/config/save"', dashboard_setup)
        self.assertIn('const cardMode = args["card-mode"] === "advanced" ? "advanced" : "simple"', dashboard_setup)
        self.assertIn("mode: cardMode", dashboard_setup)
        self.assertIn("input_select:\n  badge_state_simulator:", configuration)
        self.assertIn('state_override_entity: "input_select.badge_state_simulator"', dashboard_setup)
        self.assertIn("Badge Simulator · Lab only", dashboard_setup)
        self.assertIn("did not auto-register its canonical Card resource", dashboard_setup)


if __name__ == "__main__":
    unittest.main()
