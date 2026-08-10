"""Privacy-safe diagnostics."""
from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .adapters import adapter_for
from .const import CONF_NOTIFICATION_ROUTE, CONF_NOTIFICATION_SCRIPT

TO_REDACT = {CONF_NOTIFICATION_ROUTE, CONF_NOTIFICATION_SCRIPT}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    planner = entry.runtime_data
    next_item = planner.next_mission()
    return {
        "config": async_redact_data({**entry.data, **entry.options}, TO_REDACT),
        "state": planner.state,
        "last_reason": planner.last_reason,
        "mission_count": len(planner.missions),
        "next_mission_id": next_item[0].id if next_item else None,
        "adapters": {
            entity_id: adapter_for(hass, entity_id).diagnostics()
            for entity_id in planner.vacuums
        },
    }
