"""Shared planner entity."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, NAME
from .controller import CleaningPlanner


class PlannerEntity(Entity):
    """Base entity bound to one planner config entry."""

    _attr_has_entity_name = True

    def __init__(self, planner: CleaningPlanner, key: str) -> None:
        self.planner = planner
        self._attr_unique_id = f"{planner.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, planner.entry.entry_id)},
            name=planner.entry.title,
            manufacturer="Robbie Advanced CC",
            model="Advanced Cleaning Planner",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.planner.async_add_listener(self.async_write_ha_state)
        )
