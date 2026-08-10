"""Planner master switch."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .controller import CleaningPlanner
from .entity import PlannerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    async_add_entities((PlannerEnabledSwitch(entry.runtime_data),))


class PlannerEnabledSwitch(PlannerEntity, SwitchEntity):
    _attr_translation_key = "planner_enabled"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "planner_enabled")

    @property
    def is_on(self) -> bool:
        return self.planner.enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self.planner.async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.planner.async_set_enabled(False)
