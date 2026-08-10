"""Generic Home Assistant vacuum adapter."""
from __future__ import annotations

from homeassistant.components.vacuum import VacuumEntityFeature

from ..models import CleaningMission
from .base import VacuumAdapter


class GenericVacuumAdapter(VacuumAdapter):
    """Use only standard HA vacuum actions."""

    kind = "home_assistant"

    @property
    def capabilities(self) -> set[str]:
        result = set(super().capabilities)
        state = self.hass.states.get(self.entity_id)
        supported = int(state.attributes.get("supported_features", 0)) if state else 0
        if supported & VacuumEntityFeature.CLEAN_AREA:
            result.add("clean_area")
        if supported & VacuumEntityFeature.FAN_SPEED:
            result.add("fan")
        return result

    async def async_start_mission(self, mission: CleaningMission) -> None:
        if mission.profile.fan and "fan" in self.capabilities:
            await self.hass.services.async_call(
                "vacuum",
                "set_fan_speed",
                {
                    "entity_id": self.entity_id,
                    "fan_speed": mission.profile.fan,
                },
                blocking=True,
            )
        if mission.areas and "clean_area" in self.capabilities:
            await self.hass.services.async_call(
                "vacuum",
                "clean_area",
                {
                    "entity_id": self.entity_id,
                    "cleaning_area_id": list(mission.areas),
                },
                blocking=True,
            )
            return
        await self.hass.services.async_call(
            "vacuum", "start", {"entity_id": self.entity_id}, blocking=True
        )
