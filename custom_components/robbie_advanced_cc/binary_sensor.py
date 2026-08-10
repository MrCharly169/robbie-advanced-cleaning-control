"""Planner readiness sensor."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .adapters import adapter_for
from .controller import CleaningPlanner
from .entity import PlannerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    async_add_entities((PlannerReadySensor(entry.runtime_data),))


class PlannerReadySensor(PlannerEntity, BinarySensorEntity):
    _attr_translation_key = "planner_ready"
    _attr_icon = "mdi:check-decagram-outline"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "planner_ready")

    @property
    def is_on(self) -> bool:
        return bool(self.planner.vacuums) and all(
            adapter_for(self.planner.hass, entity_id).available
            for entity_id in self.planner.vacuums
        )

    @property
    def extra_state_attributes(self):
        return {
            entity_id: adapter_for(self.planner.hass, entity_id).diagnostics()
            for entity_id in self.planner.vacuums
        }
