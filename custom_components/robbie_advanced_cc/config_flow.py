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
    CONF_PRESENCE_ENTITIES,
    CONF_STARTER_MISSION,
    CONF_TODO_ENTITY,
    CONF_VACATION_ENTITY,
    CONF_VACUUMS,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_NAME,
    DOMAIN,
)
from .models import WEEKDAYS


def _optional(key: str, value: Any = None) -> vol.Optional:
    if value in (None, "", []):
        return vol.Optional(key)
    return vol.Optional(key, description={"suggested_value": value})


def _basics_schema(current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    return vol.Schema(
        {
            vol.Required("name", default=current.get("name", DEFAULT_NAME)): selector.TextSelector(),
            vol.Required(CONF_VACUUMS, default=current.get(CONF_VACUUMS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="vacuum", multiple=True)
            ),
        }
    )


def _presence_schema(current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    return vol.Schema(
        {
            _optional(CONF_PRESENCE_ENTITIES, current.get(CONF_PRESENCE_ENTITIES)): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["person", "device_tracker", "binary_sensor", "input_boolean", "zone"],
                    multiple=True,
                )
            ),
            _optional(CONF_VACATION_ENTITY, current.get(CONF_VACATION_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
        }
    )


def _schedule_schema(vacuums: list[str], current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    return vol.Schema(
        {
            vol.Required("create_starter_mission", default=current.get("create_starter_mission", True)): selector.BooleanSelector(),
            vol.Optional("mission_name", default=current.get("mission_name", "Daily clean")): selector.TextSelector(),
            vol.Optional("vacuum_entity_id", default=current.get("vacuum_entity_id", vacuums[0])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=vacuums, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional("weekdays", default=current.get("weekdays", list(WEEKDAYS))): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(WEEKDAYS), multiple=True, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional("start_time", default=current.get("start_time", "09:00:00")): selector.TimeSelector(),
            _optional("schedule_entity_id", current.get("schedule_entity_id")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="schedule")
            ),
            vol.Optional("people_home", default=current.get("people_home", "wait")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["wait", "allow", "skip"], mode=selector.SelectSelectorMode.DROPDOWN)
            ),
        }
    )


def _services_schema(current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    return vol.Schema(
        {
            _optional(CONF_NOTIFICATION_SCRIPT, current.get(CONF_NOTIFICATION_SCRIPT)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="script")
            ),
            _optional(CONF_NOTIFICATION_ROUTE, current.get(CONF_NOTIFICATION_ROUTE)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_text")
            ),
            _optional(CONF_TODO_ENTITY, current.get(CONF_TODO_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="todo")
            ),
            vol.Optional(CONF_DASHBOARD_PATH, default=current.get(CONF_DASHBOARD_PATH, DEFAULT_DASHBOARD_PATH)): selector.TextSelector(),
        }
    )


def _options_schema(current: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name", default=current.get("name", DEFAULT_NAME)): selector.TextSelector(),
            vol.Required(CONF_VACUUMS, default=current.get(CONF_VACUUMS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="vacuum", multiple=True)
            ),
            **_presence_schema(current).schema,
            **_services_schema(current).schema,
        }
    )


class RobbieAdvancedCcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one cleaning planner fleet with a guided setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            vacuums = sorted(set(user_input[CONF_VACUUMS]))
            if not vacuums:
                return self.async_show_form(step_id="user", data_schema=_basics_schema(user_input), errors={"base": "no_vacuums"})
            await self.async_set_unique_id("|".join(vacuums))
            self._abort_if_unique_id_configured()
            self._data = dict(user_input)
            self._data[CONF_VACUUMS] = vacuums
            return await self.async_step_presence()
        return self.async_show_form(step_id="user", data_schema=_basics_schema())

    async def async_step_presence(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            self._data.setdefault(CONF_PRESENCE_ENTITIES, [])
            return await self.async_step_schedule()
        return self.async_show_form(step_id="presence", data_schema=_presence_schema())

    async def async_step_schedule(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            starter = dict(user_input)
            enabled = bool(starter.pop("create_starter_mission", True))
            if enabled:
                start_time = str(starter.get("start_time") or "09:00")[:5]
                self._data[CONF_STARTER_MISSION] = {
                    "id": "starter",
                    "name": starter.get("mission_name") or "Daily clean",
                    "vacuum_entity_id": starter.get("vacuum_entity_id") or self._data[CONF_VACUUMS][0],
                    "weekdays": starter.get("weekdays") or [],
                    "start_time": start_time,
                    "schedule_entity_id": starter.get("schedule_entity_id") or None,
                    "guards": {"people_home": starter.get("people_home") or "wait"},
                }
            return await self.async_step_services()
        return self.async_show_form(step_id="schedule", data_schema=_schedule_schema(self._data[CONF_VACUUMS]))

    async def async_step_services(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            title = str(self._data.pop("name"))
            return self.async_create_entry(title=title, data=self._data)
        return self.async_show_form(step_id="services", data_schema=_services_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RobbieAdvancedCcOptionsFlow()


class RobbieAdvancedCcOptionsFlow(OptionsFlowWithReload):
    """Edit external bindings without touching missions."""

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options, "name": self.config_entry.title}
        if user_input is not None:
            options = dict(user_input)
            if not options.get(CONF_VACUUMS):
                return self.async_show_form(step_id="init", data_schema=_options_schema(user_input), errors={"base": "no_vacuums"})
            title = str(options.pop("name", self.config_entry.title))
            for key in (CONF_PRESENCE_ENTITIES, CONF_VACATION_ENTITY, CONF_NOTIFICATION_SCRIPT, CONF_NOTIFICATION_ROUTE, CONF_TODO_ENTITY):
                options.setdefault(key, [] if key == CONF_PRESENCE_ENTITIES else "")
            if title != self.config_entry.title:
                self.hass.config_entries.async_update_entry(self.config_entry, title=title)
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(step_id="init", data_schema=_options_schema(current))
