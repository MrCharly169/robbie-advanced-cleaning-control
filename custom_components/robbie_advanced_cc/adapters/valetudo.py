"""Valetudo capability enhancer built on MQTT-discovered HA entities."""
from __future__ import annotations

from dataclasses import replace

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

    def _sibling(self, domain: str, suffix: str) -> str | None:
        object_id = self.entity_id.split(".", 1)[1]
        candidate = f"{domain}.{object_id}_{suffix}"
        return candidate if self.hass.states.get(candidate) is not None else None

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
            }
        return result
