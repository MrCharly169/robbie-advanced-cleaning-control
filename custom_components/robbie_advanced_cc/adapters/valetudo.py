"""Valetudo capability enhancer built on MQTT-discovered HA entities."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.helpers import entity_registry as er

from ..models import CleaningMission
from .generic import GenericVacuumAdapter


class ValetudoVacuumAdapter(GenericVacuumAdapter):
    """Apply Valetudo sibling selects before using the HA vacuum contract."""

    kind = "valetudo"
    _MAINTENANCE_SUFFIXES = (
        "main_brush",
        "right_brush",
        "main_filter",
        "mop",
        "sensor_cleaning",
        "dock_detergent",
    )
    _DOCK_COMPONENTS = {
        "water_tank_clean": ("freshwater", "Freshwater", {"empty", "missing"}),
        "water_tank_dirty": ("wastewater", "Wastewater", {"full", "missing"}),
        "dustbag": ("dustbag", "Dustbag", {"full", "missing"}),
        "detergent": ("detergent", "Detergent", {"empty", "missing"}),
    }

    def _sibling(self, domain: str, suffix: str) -> str | None:
        object_id = self.entity_id.split(".", 1)[1]
        candidate = f"{domain}.{object_id}_{suffix}"
        return candidate if self.hass.states.get(candidate) is not None else None

    def _related_entities(self) -> set[str]:
        """Return entities registered on the same HA device as the vacuum."""
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.entity_id)
        if entry is None or entry.device_id is None:
            return set()
        return {
            item.entity_id
            for item in registry.entities.values()
            if item.device_id == entry.device_id and item.entity_id != self.entity_id
        }

    def _dock_component_entities(self) -> dict[str, tuple[str, str, set[str]]]:
        """Discover Valetudo 2026.05+ dock component sensors."""
        result: dict[str, tuple[str, str, set[str]]] = {}
        related = self._related_entities()
        for suffix, definition in self._DOCK_COMPONENTS.items():
            candidates = [
                self._sibling("sensor", f"{suffix}_dock_component"),
                *(
                    entity_id
                    for entity_id in related
                    if entity_id.startswith("sensor.")
                    and suffix in entity_id.casefold()
                    and "dock_component" in entity_id.casefold()
                ),
            ]
            entity_id = next((item for item in candidates if item), None)
            if entity_id:
                result[entity_id] = definition
        return result

    def _events_entity(self) -> str | None:
        exact = self._sibling("sensor", "events")
        if exact:
            return exact
        return next(
            (
                entity_id
                for entity_id in self._related_entities()
                if entity_id.startswith("sensor.")
                and entity_id.casefold().endswith(("_events", "_valetudo_events"))
            ),
            None,
        )

    @property
    def capabilities(self) -> set[str]:
        result = set(super().capabilities)
        for domain, suffix, capability in (
            ("select", "mode", "mode"),
            ("select", "fan", "fan"),
            ("select", "water", "water"),
            ("binary_sensor", "mop_attachment", "mop_attachment"),
            ("sensor", "map_segments", "map_segments"),
            ("camera", "map_data", "map"),
            ("button", "play_locate_sound", "locate"),
            ("button", "trigger_auto_empty_dock", "auto_empty"),
        ):
            if self._sibling(domain, suffix):
                result.add(capability)
        return result

    async def _async_select(self, suffix: str, option: str | None) -> None:
        entity_id = self._sibling("select", suffix)
        if entity_id and option is not None:
            current = self.hass.states.get(entity_id)
            if current is None or current.state != option:
                await self.hass.services.async_call(
                    "select",
                    "select_option",
                    {"entity_id": entity_id, "option": option},
                    blocking=True,
                )

    async def async_start_mission(self, mission: CleaningMission) -> None:
        await self._async_select("mode", mission.profile.mode)
        await self._async_select("fan", mission.profile.fan)
        await self._async_select("water", mission.profile.water)
        # A Valetudo fan select is the authoritative control. Do not repeat the
        # same setting through vacuum.set_fan_speed when both are exposed.
        generic_mission = mission
        if self._sibling("select", "fan") and mission.profile.fan is not None:
            generic_mission = replace(
                mission, profile=replace(mission.profile, fan=None)
            )
        await super().async_start_mission(generic_mission)

    @property
    def error(self) -> dict[str, object] | None:
        """Return the detailed Valetudo error even if vacuum state lags."""
        entity_id = self._sibling("sensor", "error")
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is not None:
            message = str(state.state or "").strip()
            if message.casefold() not in {
                "",
                "0",
                "none",
                "no error",
                "ok",
                "unknown",
                "unavailable",
            }:
                return {"entity_id": entity_id, "message": message}
        return super().error

    def mop_attached(self) -> bool | None:
        entity_id = self._sibling("binary_sensor", "mop_attachment")
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None or state.state in {"unknown", "unavailable"}:
            return None
        return state.state == "on"

    @property
    def watched_entities(self) -> set[str]:
        result = {
            entity_id
            for suffix in self._MAINTENANCE_SUFFIXES
            if (entity_id := self._sibling("sensor", suffix))
        }
        if mop := self._sibling("binary_sensor", "mop_attachment"):
            result.add(mop)
        if error := self._sibling("sensor", "error"):
            result.add(error)
        result.update(self._dock_component_entities())
        if events := self._events_entity():
            result.add(events)
        for domain, suffix in (
            ("select", "mode"),
            ("select", "fan"),
            ("select", "water"),
            ("select", "passes"),
            ("sensor", "map_segments"),
        ):
            if entity_id := self._sibling(domain, suffix):
                result.add(entity_id)
        return result

    def maintenance(self) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        for suffix in self._MAINTENANCE_SUFFIXES:
            entity_id = self._sibling("sensor", suffix)
            state = self.hass.states.get(entity_id) if entity_id else None
            if state is None:
                continue
            try:
                value: object = float(state.state)
            except (TypeError, ValueError):
                value = state.state
            result[suffix] = {
                "entity_id": entity_id,
                "value": value,
                "unit": state.attributes.get("unit_of_measurement"),
                "attention": isinstance(value, (int, float)) and value <= 0,
            }
        for entity_id, (key, label, attention_states) in self._dock_component_entities().items():
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            value = str(state.state or "unknown").casefold()
            result[f"dock_{key}"] = {
                "entity_id": entity_id,
                "label": label,
                "value": value,
                "attention": value in attention_states,
            }
        events_entity = self._events_entity()
        events_state = self.hass.states.get(events_entity) if events_entity else None
        if events_state is not None:
            for event_id, event in events_state.attributes.items():
                if not isinstance(event, dict):
                    continue
                event_type = str(event.get("__class") or event.get("type") or "")
                if event_type != "DustBinFullValetudoEvent":
                    continue
                result[f"event_dustbin_full_{event_id}"] = {
                    "entity_id": events_entity,
                    "label": "Dustbin",
                    "value": "full",
                    "attention": True,
                    "event_id": str(event.get("id") or event_id),
                }
        return result

    def run_metrics(self) -> dict[str, dict[str, Any]]:
        """Return Valetudo's current cleaning time and area when available."""
        result: dict[str, dict[str, Any]] = {}
        for key, suffixes in {
            "duration": ("current_statistics_time", "current_cleaning_time"),
            "area": ("current_statistics_area", "current_cleaning_area"),
        }.items():
            entity_id = next(
                (
                    candidate
                    for suffix in suffixes
                    if (candidate := self._sibling("sensor", suffix))
                ),
                None,
            )
            state = self.hass.states.get(entity_id) if entity_id else None
            if state is None:
                continue
            try:
                value: object = float(state.state)
            except (TypeError, ValueError):
                value = state.state
            result[key] = {
                "entity_id": entity_id,
                "value": value,
                "unit": state.attributes.get("unit_of_measurement"),
            }
        return result
