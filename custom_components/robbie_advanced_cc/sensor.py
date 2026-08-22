"""Planner sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .adapters import adapter_for
from .capabilities import discover_profile_options
from .const import (
    CARD_RESOURCE_URL,
    CARD_TYPE,
    CONF_DASHBOARD_PATH,
    CONF_VACATION_ENTITY,
    DEFAULT_DASHBOARD_PATH,
    DOMAIN,
    PLANNER_STATUS_OPTIONS,
)
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
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PLANNER_STATUS_OPTIONS

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "planner_status")

    @property
    def native_value(self) -> str:
        return self.planner.effective_state

    @property
    def icon(self) -> str:
        return {
            "idle": "mdi:robot-vacuum-variant",
            "announced": "mdi:calendar-clock",
            "preparing": "mdi:progress-wrench",
            "running": "mdi:robot-vacuum",
            "dock_service": "mdi:home-wrench",
            "completed": "mdi:check-circle-outline",
            "skipped": "mdi:skip-next",
            "postponed": "mdi:clock-plus-outline",
            "waiting": "mdi:account-clock-outline",
            "vacation": "mdi:palm-tree",
            "blocked": "mdi:shield-alert-outline",
            "failed": "mdi:alert",
        }.get(self.native_value, "mdi:robot-vacuum")

    @property
    def extra_state_attributes(self):
        next_runs = {}
        missions = []
        for vacuum_entity_id in self.planner.vacuums:
            item = self.planner.next_mission_for(vacuum_entity_id)
            if item:
                mission, occurrence = item
                next_runs[vacuum_entity_id] = {
                    "mission": mission.name,
                    "mission_id": mission.id,
                    "scheduled": occurrence.isoformat(),
                }
        for mission in self.planner.missions:
            raw = mission.as_dict()
            occurrence = self.planner.next_occurrence_for(mission)
            raw["next_run"] = occurrence.isoformat() if occurrence else None
            raw["conditions"] = self.planner.conditions_for(mission)
            raw["all_conditions_met"] = all(
                not item["enabled"] or item["passed"]
                for item in raw["conditions"]
            )
            raw["waiting"] = mission.id in self.planner.pending_mission_ids
            missions.append(raw)
        return {
            "entry_id": self.planner.entry.entry_id,
            "vacation_active": self.planner.vacation_active,
            "vacation_entity_id": self.planner.config.get(CONF_VACATION_ENTITY),
            "active_mission_id": self.planner.active_mission_id,
            "last_reason": self.planner.last_reason,
            "last_resolution": (
                self.planner.last_decision.resolution
                if self.planner.last_decision
                else None
            ),
            "last_allowed": (
                self.planner.last_decision.allowed
                if self.planner.last_decision
                else None
            ),
            "managed_vacuums": self.planner.vacuums,
            "profile_options": {
                entity_id: discover_profile_options(self.planner.hass, entity_id)
                for entity_id in self.planner.vacuums
            },
            "mission_count": len(self.planner.missions),
            "waiting_mission_ids": list(self.planner.pending_mission_ids),
            "waiting_vacuums": [
                mission.vacuum_entity_id
                for mission in self.planner.missions
                if mission.id in self.planner.pending_mission_ids
            ],
            "next_runs": next_runs,
            "missions": missions,
            "dashboard": {
                "resource_url": CARD_RESOURCE_URL,
                "resource_registered": bool(
                    self.planner.hass.data.get(f"{DOMAIN}_resource_registered")
                ),
                "card_type": CARD_TYPE,
                "badge_type": "entity",
                "navigation_path": (
                    self.planner.config.get(CONF_DASHBOARD_PATH)
                    or DEFAULT_DASHBOARD_PATH
                ),
            },
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
