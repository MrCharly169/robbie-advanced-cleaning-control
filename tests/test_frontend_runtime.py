from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MODULE = ROOT / "custom_components" / "robbie_advanced_cc" / "frontend.py"


def _load_registration_function():
    """Compile the production coroutine without importing Home Assistant."""
    tree = ast.parse(FRONTEND_MODULE.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "async_register_card_resource"
    )
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias("annotations")], level=0), function],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace = {
        "__file__": str(FRONTEND_MODULE),
        "Any": object,
        "HomeAssistant": object,
        "Path": Path,
        "StaticPathConfig": lambda *args: args,
        "LOVELACE_DATA": "lovelace",
        "MODE_STORAGE": "storage",
        "DOMAIN": "robbie_advanced_cc",
        "CARD_RESOURCE_URL": "/robbie_advanced_cc/cleaning-control.js",
        "CONF_URL": "url",
        "CONF_ID": "id",
        "_LOGGER": SimpleNamespace(info=lambda *args: None, warning=lambda *args: None),
    }
    exec(compile(module, str(FRONTEND_MODULE), "exec"), namespace)
    return namespace["async_register_card_resource"]


class Resources:
    def __init__(self):
        self.items = []
        self.creates = 0
        self.updates = 0

    async def async_get_info(self):
        return None

    def async_items(self):
        return list(self.items)

    async def async_create_item(self, item):
        self.creates += 1
        self.items.append({
            "id": "resource-1", "type": item["res_type"], "url": item["url"],
        })

    async def async_update_item(self, item_id, item):
        self.updates += 1
        current = next(value for value in self.items if value["id"] == item_id)
        current.update({"type": item["res_type"], "url": item["url"]})


class FakeHass:
    def __init__(self):
        self.resources = Resources()
        self.data = {
            "lovelace": SimpleNamespace(resource_mode="storage", resources=self.resources),
        }
        self.static_registrations = 0
        self.http = SimpleNamespace(async_register_static_paths=self._register_static_paths)

    async def _register_static_paths(self, _paths):
        self.static_registrations += 1

class FrontendRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stable_resource_url_and_registration_are_idempotent(self):
        register = _load_registration_function()
        hass = FakeHass()

        self.assertTrue(await register(hass))
        self.assertTrue(await register(hass))

        self.assertEqual(hass.static_registrations, 1)
        self.assertEqual(hass.resources.creates, 1)
        self.assertEqual(hass.resources.updates, 0)
        self.assertEqual(len(hass.resources.items), 1)
        self.assertEqual(
            hass.resources.items[0]["url"],
            "/robbie_advanced_cc/cleaning-control.js",
        )

    async def test_legacy_versioned_resource_is_migrated_to_stable_url(self):
        register = _load_registration_function()
        hass = FakeHass()
        hass.resources.items.append({
            "id": "resource-1",
            "type": "module",
            "url": "/robbie_advanced_cc/cleaning-control.js?v=2026.8.0b9-deadbeef00",
        })

        self.assertTrue(await register(hass))
        self.assertEqual(hass.resources.creates, 0)
        self.assertEqual(hass.resources.updates, 1)
        self.assertEqual(
            hass.resources.items[0]["url"],
            "/robbie_advanced_cc/cleaning-control.js",
        )


if __name__ == "__main__":
    unittest.main()
