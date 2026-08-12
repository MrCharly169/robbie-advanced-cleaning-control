"""Dashboard resource registration and first-run guidance."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    BADGE_TYPE,
    CARD_RESOURCE_URL,
    CARD_TYPE,
    CONF_DASHBOARD_PATH,
    CONF_FRONTEND_ONBOARDING_SENT,
    DEFAULT_DASHBOARD_PATH,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_register_card_resource(hass: HomeAssistant) -> bool:
    """Serve the Card and add its module to Storage-mode dashboards once."""
    if not hass.data.get(f"{DOMAIN}_frontend_registered"):
        frontend = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(f"/{DOMAIN}", str(frontend), False)]
        )
        hass.data[f"{DOMAIN}_frontend_registered"] = True

    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        _LOGGER.warning("Lovelace is unavailable; Card resource was not registered")
        return False
    if lovelace.resource_mode != MODE_STORAGE:
        _LOGGER.info(
            "Lovelace resources use YAML mode; add %s as a module manually",
            CARD_RESOURCE_URL,
        )
        return False

    resources = lovelace.resources
    await resources.async_get_info()
    integration = await async_get_integration(hass, DOMAIN)
    resource_url = f"{CARD_RESOURCE_URL}?v={integration.version}"
    matching: list[dict[str, Any]] = [
        item
        for item in resources.async_items()
        if str(item.get(CONF_URL, "")).split("?", 1)[0] == CARD_RESOURCE_URL
    ]
    if not matching:
        await resources.async_create_item({"res_type": "module", CONF_URL: resource_url})
        _LOGGER.info("Registered Robbie dashboard module %s", resource_url)
        return True

    primary = matching[0]
    if primary.get(CONF_URL) != resource_url or primary.get("type") != "module":
        await resources.async_update_item(
            str(primary[CONF_ID]),
            {"res_type": "module", CONF_URL: resource_url},
        )
    return True


async def async_show_setup_notification(
    hass: HomeAssistant, entry: ConfigEntry, resource_registered: bool
) -> None:
    """Show Card and Badge instructions once after successful entry setup."""
    if entry.data.get(CONF_FRONTEND_ONBOARDING_SENT):
        return

    dashboard_path = str(entry.data.get(CONF_DASHBOARD_PATH) or DEFAULT_DASHBOARD_PATH)
    resource_note = (
        f"The JavaScript module `{CARD_RESOURCE_URL}` was registered automatically."
        if resource_registered
        else (
            "Your dashboard resources use YAML mode. Add "
            f"`url: {CARD_RESOURCE_URL}` with `type: module` first."
        )
    )
    message = f"""Setup is complete. {resource_note}

Add the Card through **Edit dashboard → Add card → Robbie Advanced Cleaning Control** or use:

```yaml
type: {CARD_TYPE}
status_entity: sensor.YOUR_PLANNER_planner_status
mode: simple
```

Add the native-size robot Badge at the top of the view with:

```yaml
type: {BADGE_TYPE}
vacuum_entity: vacuum.YOUR_ROBOT
status_entity: sensor.YOUR_PLANNER_planner_status
navigation_path: {dashboard_path}
```

Open the [Cleaning Control dashboard]({dashboard_path}). Switch the Card to **Advanced** to create a separate run for each weekday, room, vacuum/mop mode, fan strength, water level and number of passes.
"""
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": f"{entry.title} · Dashboard setup",
            "message": message,
            "notification_id": f"{DOMAIN}_setup_{entry.entry_id}",
        },
        blocking=True,
    )
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_FRONTEND_ONBOARDING_SENT: True},
    )
