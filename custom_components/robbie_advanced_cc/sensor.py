"""Planner sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .adapters import adapter_for
from .controller import CleaningPlanner
from .entity import PlannerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    planner: CleaningPlanner = entry.runtime_data
    async_add_entities(
        (
            PlannerStatusSensor(planner),
            NextMissionSensor(planner),
            LastDecisionSensor(planner),
            MaintenanceSensor(planner),
        )
    )


class PlannerStatusSensor(PlannerEntity, SensorEntity):
    _attr_translation_key = "planner_status"
    _attr_icon = "mdi:robot-vacuum"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "planner_status")

    @property
    def native_value(self) -> str:
        return self.planner.state

    @property
    def extra_state_attributes(self):
        return {
            "entry_id": self.planner.entry.entry_id,
            "active_mission_id": self.planner.active_mission_id,
            "managed_vacuums": self.planner.vacuums,
            "mission_count": len(self.planner.missions),
        }


class NextMissionSensor(PlannerEntity, SensorEntity):
    _attr_translation_key = "next_mission"
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = "timestamp"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "next_mission")

    @property
    def native_value(self):
        item = self.planner.next_mission()
        return item[1] if item else None

    @property
    def extra_state_attributes(self):
        item = self.planner.next_mission()
        if not item:
            return {
                "entry_id": self.planner.entry.entry_id,
                "mission": None,
            }
        mission, occurrence = item
        return {
            "entry_id": self.planner.entry.entry_id,
            "mission": mission.name,
            "mission_id": mission.id,
            "vacuum_entity_id": mission.vacuum_entity_id,
            "areas": list(mission.areas),
            "profile": mission.profile.as_dict(),
            "skip_armed": self.planner.skip_mission_id == mission.id,
            "scheduled": occurrence.isoformat(),
        }


class LastDecisionSensor(PlannerEntity, SensorEntity):
    _attr_translation_key = "last_decision"
    _attr_icon = "mdi:head-question-outline"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "last_decision")

    @property
    def native_value(self) -> str:
        return self.planner.last_reason

    @property
    def extra_state_attributes(self):
        decision = self.planner.last_decision
        return {
            "entry_id": self.planner.entry.entry_id,
            "allowed": decision.allowed if decision else None,
            "resolution": decision.resolution if decision else None,
        }


class MaintenanceSensor(PlannerEntity, SensorEntity):
    _attr_translation_key = "maintenance"
    _attr_icon = "mdi:tools"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "maintenance")

    def _items(self):
        return {
            entity_id: adapter_for(
                self.planner.hass, entity_id
            ).maintenance()
            for entity_id in self.planner.vacuums
        }

    @property
    def native_value(self) -> str:
        values = [
            item.get("value")
            for vacuum in self._items().values()
            for item in vacuum.values()
        ]
        if not values:
            return "not_supported"
        return "attention" if any(
            isinstance(value, (int, float)) and value <= 0 for value in values
        ) else "ok"

    @property
    def extra_state_attributes(self):
        return {
            "entry_id": self.planner.entry.entry_id,
            "items": self._items(),
        }
