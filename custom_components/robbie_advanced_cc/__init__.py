"""Robbie Advanced Cleaning Control integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_MISSION,
    SERVICE_POSTPONE_NEXT,
    SERVICE_REMOVE_MISSION,
    SERVICE_RESOLVE_PENDING,
    SERVICE_RUN_NEXT,
    SERVICE_SKIP_NEXT,
)
from .controller import CleaningPlanner
from .frontend import async_register_card_resource, async_show_setup_notification

type RobbieConfigEntry = ConfigEntry[CleaningPlanner]

_REGISTRY = f"{DOMAIN}_planners"


def _planner(hass: HomeAssistant, entry_id: str) -> CleaningPlanner:
    planner = hass.data.get(_REGISTRY, {}).get(entry_id)
    if planner is None:
        raise vol.Invalid(f"No loaded {DOMAIN} entry matches {entry_id!r}")
    return planner


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the permanent card resource and narrow planner services."""
    hass.data[f"{DOMAIN}_resource_registered"] = await async_register_card_resource(hass)

    if hass.services.has_service(DOMAIN, SERVICE_RUN_NEXT):
        return True

    async def add_mission(call: ServiceCall) -> None:
        await _planner(hass, call.data["entry_id"]).async_add_mission(
            dict(call.data["mission"])
        )

    async def remove_mission(call: ServiceCall) -> None:
        await _planner(hass, call.data["entry_id"]).async_remove_mission(
            call.data["mission_id"]
        )

    async def run_next(call: ServiceCall) -> None:
        await _planner(hass, call.data["entry_id"]).async_run(
            call.data.get("mission_id"), manual=call.data.get("manual", False)
        )

    async def resolve_pending(call: ServiceCall) -> None:
        await _planner(hass, call.data["entry_id"]).async_resolve_pending(
            call.data["mission_id"]
        )

    async def skip_next(call: ServiceCall) -> None:
        await _planner(hass, call.data["entry_id"]).async_skip_next()

    async def postpone_next(call: ServiceCall) -> None:
        await _planner(hass, call.data["entry_id"]).async_postpone(
            call.data.get("mission_id"), call.data.get("minutes", 60)
        )

    entry_schema = vol.Schema({vol.Required("entry_id"): str})
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_MISSION,
        add_mission,
        schema=vol.Schema(
            {vol.Required("entry_id"): str, vol.Required("mission"): dict}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_MISSION,
        remove_mission,
        schema=vol.Schema(
            {vol.Required("entry_id"): str, vol.Required("mission_id"): str}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESOLVE_PENDING,
        resolve_pending,
        schema=vol.Schema(
            {vol.Required("entry_id"): str, vol.Required("mission_id"): str}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_NEXT,
        run_next,
        schema=vol.Schema(
            {
                vol.Required("entry_id"): str,
                vol.Optional("mission_id"): str,
                vol.Optional("manual", default=False): bool,
            }
        ),
    )
    hass.services.async_register(DOMAIN, SERVICE_SKIP_NEXT, skip_next, schema=entry_schema)
    hass.services.async_register(
        DOMAIN,
        SERVICE_POSTPONE_NEXT,
        postpone_next,
        schema=vol.Schema(
            {
                vol.Required("entry_id"): str,
                vol.Optional("mission_id"): str,
                vol.Optional("minutes", default=60): vol.All(int, vol.Range(min=1, max=1440)),
            }
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RobbieConfigEntry) -> bool:
    planner = CleaningPlanner(hass, entry)
    await planner.async_setup()
    entry.runtime_data = planner
    hass.data.setdefault(_REGISTRY, {})[entry.entry_id] = planner
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_show_setup_notification(
        hass,
        entry,
        bool(hass.data.get(f"{DOMAIN}_resource_registered")),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RobbieConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
        hass.data.get(_REGISTRY, {}).pop(entry.entry_id, None)
    return unloaded
