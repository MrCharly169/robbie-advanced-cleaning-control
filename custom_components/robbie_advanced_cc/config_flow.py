"""Config and options flow."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DASHBOARD_PATH,
    CONF_NOTIFICATION_ROUTE,
    CONF_NOTIFICATION_SCRIPT,
    CONF_TODO_ENTITY,
    CONF_VACATION_ENTITY,
    CONF_VACUUMS,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_NAME,
    DOMAIN,
)


def _optional(key: str, value: Any = None) -> vol.Optional:
    if value in (None, "", []):
        return vol.Optional(key)
    return vol.Optional(key, description={"suggested_value": value})


def _schema(current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    return vol.Schema(
        {
            vol.Required(
                "name", default=current.get("name", DEFAULT_NAME)
            ): selector.TextSelector(),
            vol.Required(
                CONF_VACUUMS,
                default=current.get(CONF_VACUUMS, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="vacuum", multiple=True)
            ),
            _optional(
                CONF_VACATION_ENTITY, current.get(CONF_VACATION_ENTITY)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            _optional(
                CONF_NOTIFICATION_SCRIPT, current.get(CONF_NOTIFICATION_SCRIPT)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="script")
            ),
            _optional(
                CONF_NOTIFICATION_ROUTE, current.get(CONF_NOTIFICATION_ROUTE)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_text")
            ),
            _optional(CONF_TODO_ENTITY, current.get(CONF_TODO_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="todo")
            ),
            vol.Optional(
                CONF_DASHBOARD_PATH,
                default=current.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH),
            ): selector.TextSelector(),
        }
    )


class RobbieAdvancedCcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one cleaning planner fleet."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            vacuums = sorted(set(user_input[CONF_VACUUMS]))
            if not vacuums:
                return self.async_show_form(
                    step_id="user",
                    data_schema=_schema(user_input),
                    errors={"base": "no_vacuums"},
                )
            await self.async_set_unique_id("|".join(vacuums))
            self._abort_if_unique_id_configured()
            data = dict(user_input)
            title = str(data.pop("name"))
            data[CONF_VACUUMS] = vacuums
            return self.async_create_entry(title=title, data=data)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RobbieAdvancedCcOptionsFlow()


class RobbieAdvancedCcOptionsFlow(OptionsFlowWithReload):
    """Edit external bindings without touching missions."""

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        current = {
            **self.config_entry.data,
            **self.config_entry.options,
            "name": self.config_entry.title,
        }
        if user_input is not None:
            options = dict(user_input)
            if not options.get(CONF_VACUUMS):
                return self.async_show_form(
                    step_id="init",
                    data_schema=_schema(user_input),
                    errors={"base": "no_vacuums"},
                )
            title = str(options.pop("name", self.config_entry.title))
            for key in (
                CONF_VACATION_ENTITY,
                CONF_NOTIFICATION_SCRIPT,
                CONF_NOTIFICATION_ROUTE,
                CONF_TODO_ENTITY,
            ):
                options.setdefault(key, "")
            if title != self.config_entry.title:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, title=title
                )
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(step_id="init", data_schema=_schema(current))
