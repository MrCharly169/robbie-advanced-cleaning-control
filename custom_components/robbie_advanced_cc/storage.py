"""Persistent planner storage."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION
from .models import CleaningMission


class PlannerStore:
    """Small versioned store for missions and one-shot state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}",
        )

    async def async_load(self) -> tuple[list[CleaningMission], dict[str, Any]]:
        raw = await self._store.async_load() or {}
        missions = [
            CleaningMission.from_dict(item)
            for item in raw.get("missions", [])
            if isinstance(item, dict)
        ]
        state = dict(raw.get("state") or {})
        return missions, state

    async def async_save(
        self, missions: list[CleaningMission], state: dict[str, Any]
    ) -> None:
        await self._store.async_save(
            {
                "missions": [mission.as_dict() for mission in missions],
                "state": state,
            }
        )
