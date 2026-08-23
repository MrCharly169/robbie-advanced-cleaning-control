"""Immediate planner controls."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .controller import CleaningPlanner
from .entity import PlannerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    planner: CleaningPlanner = entry.runtime_data
    async_add_entities(
        (RunNextButton(planner), SkipNextButton(planner), PostponeNextButton(planner))
    )


class RunNextButton(PlannerEntity, ButtonEntity):
    _attr_translation_key = "run_next"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "run_next")

    async def async_press(self) -> None:
        await self.planner.async_run(manual=True)


class SkipNextButton(PlannerEntity, ButtonEntity):
    _attr_translation_key = "skip_next"
    _attr_icon = "mdi:skip-next-circle-outline"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "skip_next")

    async def async_press(self) -> None:
        await self.planner.async_skip_next()


class PostponeNextButton(PlannerEntity, ButtonEntity):
    _attr_translation_key = "postpone_next"
    _attr_icon = "mdi:clock-plus-outline"

    def __init__(self, planner: CleaningPlanner) -> None:
        super().__init__(planner, "postpone_next")

    async def async_press(self) -> None:
        await self.planner.async_postpone()
