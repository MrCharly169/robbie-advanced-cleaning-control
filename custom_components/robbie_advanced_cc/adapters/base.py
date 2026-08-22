"""Adapter contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from homeassistant.components.vacuum import VacuumEntityFeature
from homeassistant.core import HomeAssistant

from ..models import CleaningMission


class VacuumAdapter(ABC):
    """Translate a portable mission into one installed HA integration."""

    kind = "generic"

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id

    @property
    def error(self) -> dict[str, Any] | None:
        """Return a normalized active robot error from the native vacuum."""
        state = self.hass.states.get(self.entity_id)
        if state is None or state.state != "error":
            return None
        message = next(
            (
                state.attributes.get(key)
                for key in ("error", "error_message", "message", "status")
                if state.attributes.get(key) not in (None, "")
            ),
            "Robot reported an error",
        )
        result: dict[str, Any] = {
            "entity_id": self.entity_id,
            "message": str(message),
        }
        if (code := state.attributes.get("error_code")) not in (None, ""):
            result["code"] = str(code)
        return result

    @property
    def available(self) -> bool:
        state = self.hass.states.get(self.entity_id)
        return (
            state is not None
            and state.state not in {"unknown", "unavailable", "error"}
            and self.error is None
        )

    @property
    def capabilities(self) -> set[str]:
        state = self.hass.states.get(self.entity_id)
        supported = int(state.attributes.get("supported_features", 0)) if state else 0
        mapping = {
            VacuumEntityFeature.START: "start",
            VacuumEntityFeature.PAUSE: "pause",
            VacuumEntityFeature.RETURN_HOME: "return_to_base",
            VacuumEntityFeature.LOCATE: "locate",
        }
        return {name for feature, name in mapping.items() if supported & feature}

    @abstractmethod
    async def async_start_mission(self, mission: CleaningMission) -> None:
        """Apply a mission and start cleaning."""

    async def async_pause(self) -> None:
        await self.hass.services.async_call(
            "vacuum", "pause", {"entity_id": self.entity_id}, blocking=True
        )

    async def async_return_to_base(self) -> None:
        await self.hass.services.async_call(
            "vacuum", "return_to_base", {"entity_id": self.entity_id}, blocking=True
        )

    def diagnostics(self) -> dict[str, Any]:
        return {
            "adapter": self.kind,
            "available": self.available,
            "error": self.error,
            "capabilities": sorted(self.capabilities),
        }

    @property
    def watched_entities(self) -> set[str]:
        """Return optional sibling entities that affect planner presentation."""
        return set()

    def maintenance(self) -> dict[str, Any]:
        """Return normalized maintenance items when an adapter exposes them."""
        return {}
