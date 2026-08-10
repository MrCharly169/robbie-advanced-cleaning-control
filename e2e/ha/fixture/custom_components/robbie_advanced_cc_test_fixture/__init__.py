"""Controllable Valetudo/cloud fixtures used only by the E2E laboratory."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .store import DOMAIN, get_store


async def async_setup(hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    store = get_store(hass)

    async def async_set_state(call: ServiceCall) -> None:
        entity_id = str(call.data["entity_id"])
        entity = store.entities.get(entity_id)
        if entity is None:
            raise HomeAssistantError(f"Unknown fixture entity: {entity_id}")
        entity.set_fixture_state(
            call.data.get("state"),
            dict(call.data.get("attributes") or {}),
            bool(call.data.get("available", True)),
        )
        entity.async_write_ha_state()

    async def async_reset_calls(_call: ServiceCall) -> None:
        store.reset_calls()

    async def async_map_areas(call: ServiceCall) -> None:
        entity_id = str(call.data["entity_id"])
        registry = er.async_get(hass)
        if registry.async_get(entity_id) is None:
            raise HomeAssistantError(f"Entity is not registered: {entity_id}")
        mapping = {
            str(area_id): [str(segment) for segment in segments]
            for area_id, segments in dict(call.data["mapping"]).items()
        }
        registry.async_update_entity_options(
            entity_id,
            "vacuum",
            {
                "area_mapping": mapping,
                "last_seen_segments": [
                    {"id": "16", "name": "Kitchen", "group": None},
                    {"id": "17", "name": "Living room", "group": None},
                    {"id": "18", "name": "Bathroom", "group": None},
                ],
            },
        )

    hass.services.async_register(DOMAIN, "set_state", async_set_state)
    hass.services.async_register(DOMAIN, "reset_calls", async_reset_calls)
    hass.services.async_register(DOMAIN, "map_areas", async_map_areas)
    return True
