from __future__ import annotations

import ast
import asyncio
import hashlib
from pathlib import Path
import threading
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
        "Path": RecordingPath,
        "StaticPathConfig": lambda *args: args,
        "LOVELACE_DATA": "lovelace",
        "MODE_STORAGE": "storage",
        "DOMAIN": "robbie_advanced_cc",
        "CARD_RESOURCE_URL": "/robbie_advanced_cc/cleaning-control.js",
        "CONF_URL": "url",
        "CONF_ID": "id",
        "hashlib": hashlib,
        "_LOGGER": SimpleNamespace(info=lambda *args: None, warning=lambda *args: None),
        "async_get_integration": _get_integration,
    }
    exec(compile(module, str(FRONTEND_MODULE), "exec"), namespace)
    return namespace["async_register_card_resource"]


async def _get_integration(_hass, _domain):
    return SimpleNamespace(version="2026.8.0b4")


class RecordingPath:
    read_threads: list[int] = []

    def __init__(self, value):
        self.value = str(value)

    @property
    def parent(self):
        return self

    def __truediv__(self, child):
        return RecordingPath(f"{self.value}/{child}")

    def __str__(self):
        return self.value

    def read_bytes(self):
        self.read_threads.append(threading.get_ident())
        return b"stable frontend asset"


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
        self.executor_calls = 0
        self.http = SimpleNamespace(async_register_static_paths=self._register_static_paths)

    async def _register_static_paths(self, _paths):
        self.static_registrations += 1

    async def async_add_executor_job(self, target):
        self.executor_calls += 1
        return await asyncio.to_thread(target)


class FrontendRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_asset_hash_io_uses_executor_and_registration_is_idempotent(self):
        register = _load_registration_function()
        hass = FakeHass()
        event_loop_thread = threading.get_ident()
        RecordingPath.read_threads.clear()

        self.assertTrue(await register(hass))
        self.assertTrue(await register(hass))

        self.assertEqual(hass.executor_calls, 2)
        self.assertEqual(hass.static_registrations, 1)
        self.assertEqual(hass.resources.creates, 1)
        self.assertEqual(hass.resources.updates, 0)
        self.assertEqual(len(hass.resources.items), 1)
        self.assertTrue(RecordingPath.read_threads)
        self.assertTrue(all(thread != event_loop_thread for thread in RecordingPath.read_threads))
        self.assertRegex(hass.resources.items[0]["url"], r"\?v=2026\.8\.0b4-[0-9a-f]{10}$")


if __name__ == "__main__":
    unittest.main()
