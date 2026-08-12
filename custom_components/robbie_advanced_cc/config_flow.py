"""Config and options flow."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers import selector

from .capabilities import discover_profile_options
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
                    domain=[
                        "person",
                        "device_tracker",
                        "binary_sensor",
                        "input_boolean",
                        "zone",
                        "sensor",
                        "number",
                        "input_number",
                        "counter",
                    ],
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


def _profile_schema(options: dict[str, Any], current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    detected = options.get("current") or {}
    fields: dict[vol.Marker, Any] = {}
    if options.get("areas"):
        fields[vol.Optional("areas", default=current.get("areas", []))] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options["areas"], multiple=True, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    fields[vol.Required(
        "profile_mode", default=current.get("profile_mode", detected.get("mode") or "vacuum")
    )] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=options["modes"], mode=selector.SelectSelectorMode.DROPDOWN)
    )
    if options.get("fan_speeds"):
        fields[_optional("fan", current.get("fan", detected.get("fan")))] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=options["fan_speeds"], mode=selector.SelectSelectorMode.DROPDOWN)
        )
    if options.get("water_levels"):
        fields[_optional("water", current.get("water", detected.get("water")))] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=options["water_levels"], mode=selector.SelectSelectorMode.DROPDOWN)
        )
    fields[vol.Required(
        "passes", default=str(current.get("passes", detected.get("passes") or "1"))
    )] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=options["passes"], mode=selector.SelectSelectorMode.DROPDOWN)
    )
    return vol.Schema(fields)


def _services_schema(current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    return vol.Schema(
        {
            _optional(CONF_NOTIFICATION_SCRIPT, current.get(CONF_NOTIFICATION_SCRIPT)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="script")
            ),
            _optional(CONF_NOTIFICATION_ROUTE, current.get(CONF_NOTIFICATION_ROUTE)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["input_text", "input_select", "select"])
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


def _options_start_schema(missions, language: str = "en") -> vol.Schema:
    de = str(language).lower().startswith("de")
    choices = [
        {
            "value": "connections",
            "label": "Verbindungen & Bedingungen" if de else "Connections & conditions",
        },
        {"value": "new", "label": "+ Mission erstellen" if de else "+ Create mission"},
    ]
    choices.extend(
        {
            "value": mission.id,
            "label": f"{'Bearbeiten' if de else 'Edit'} · {mission.name}",
        }
        for mission in missions
    )
    return vol.Schema(
        {
            vol.Required("options_action", default="connections"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=choices,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def _mission_schedule_schema(
    vacuums: list[str], current: dict[str, Any], *, can_delete: bool
) -> vol.Schema:
    guards = current.get("guards") or {}
    fields: dict[vol.Marker, Any] = {
        vol.Required("mission_name", default=current.get("name", "Cleaning mission")): selector.TextSelector(),
        vol.Required(
            "vacuum_entity_id",
            default=current.get("vacuum_entity_id", vacuums[0]),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=vacuums, mode=selector.SelectSelectorMode.DROPDOWN
            )
        ),
        vol.Required("weekdays", default=current.get("weekdays", list(WEEKDAYS))): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(WEEKDAYS),
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required("start_time", default=current.get("start_time", "09:00")): selector.TimeSelector(),
        _optional("schedule_entity_id", current.get("schedule_entity_id")): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="schedule")
        ),
        vol.Required("people_home", default=guards.get("people_home", "wait")): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["wait", "allow", "skip"],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required("enabled", default=current.get("enabled", True)): selector.BooleanSelector(),
        vol.Required(
            "announce_before_minutes",
            default=current.get("announce_before_minutes", 1440),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=10080,
                step=5,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="min",
            )
        ),
    }
    if can_delete:
        fields[vol.Optional("delete_mission", default=False)] = selector.BooleanSelector()
    return vol.Schema(fields)


class RobbieAdvancedCcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one cleaning planner fleet with a guided setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._starter: dict[str, Any] = {}

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
            self._starter = dict(user_input)
            if not bool(self._starter.pop("create_starter_mission", True)):
                return await self.async_step_services()
            return await self.async_step_profile()
        return self.async_show_form(step_id="schedule", data_schema=_schedule_schema(self._data[CONF_VACUUMS]))

    async def async_step_profile(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        vacuum_entity_id = self._starter.get("vacuum_entity_id") or self._data[CONF_VACUUMS][0]
        options = discover_profile_options(self.hass, vacuum_entity_id)
        if user_input is not None:
            profile = dict(user_input)
            profile_mode = str(profile.get("profile_mode") or "vacuum")
            self._data[CONF_STARTER_MISSION] = {
                "id": "starter",
                "name": self._starter.get("mission_name") or "Daily clean",
                "vacuum_entity_id": vacuum_entity_id,
                "weekdays": self._starter.get("weekdays") or [],
                "start_time": str(self._starter.get("start_time") or "09:00")[:5],
                "schedule_entity_id": self._starter.get("schedule_entity_id") or None,
                "areas": list(profile.get("areas") or []),
                "profile": {
                    "mode": profile_mode,
                    "fan": profile.get("fan") or None,
                    "water": (
                        profile.get("water") or None
                        if profile_mode != "vacuum"
                        else None
                    ),
                    "passes": int(profile.get("passes") or 1),
                },
                "guards": {"people_home": self._starter.get("people_home") or "wait"},
            }
            return await self.async_step_services()
        return self.async_show_form(
            step_id="profile",
            data_schema=_profile_schema(options),
            description_placeholders={
                "vacuum": self.hass.states.get(vacuum_entity_id).attributes.get("friendly_name", vacuum_entity_id)
                if self.hass.states.get(vacuum_entity_id)
                else vacuum_entity_id,
                "adapter": str(options.get("adapter") or "home_assistant"),
            },
        )

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
    """Edit bindings and persistent missions after initial setup."""

    def __init__(self) -> None:
        self._mission: dict[str, Any] = {}
        self._mission_draft: dict[str, Any] = {}

    @property
    def _planner(self):
        return self.config_entry.runtime_data

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            action = str(user_input["options_action"])
            if action == "connections":
                return await self.async_step_connections()
            if action == "new":
                self._mission = {
                    "id": uuid4().hex,
                    "weekdays": list(WEEKDAYS),
                    "start_time": "09:00",
                    "guards": {"people_home": "wait"},
                    "profile": {"mode": "vacuum", "passes": 1},
                    "enabled": True,
                    "announce_before_minutes": 1440,
                }
            else:
                mission = self._planner.mission_by_id(action)
                if mission is None:
                    return self.async_show_form(
                        step_id="init",
                        data_schema=_options_start_schema(
                            self._planner.missions, self.hass.config.language
                        ),
                        errors={"base": "mission_not_found"},
                    )
                self._mission = mission.as_dict()
            return await self.async_step_mission_schedule()
        return self.async_show_form(
            step_id="init",
            data_schema=_options_start_schema(
                self._planner.missions, self.hass.config.language
            ),
        )

    async def async_step_connections(self, user_input=None) -> ConfigFlowResult:
        current = {**self.config_entry.data, **self.config_entry.options, "name": self.config_entry.title}
        if user_input is not None:
            options = dict(user_input)
            if not options.get(CONF_VACUUMS):
                return self.async_show_form(step_id="connections", data_schema=_options_schema(user_input), errors={"base": "no_vacuums"})
            title = str(options.pop("name", self.config_entry.title))
            for key in (CONF_PRESENCE_ENTITIES, CONF_VACATION_ENTITY, CONF_NOTIFICATION_SCRIPT, CONF_NOTIFICATION_ROUTE, CONF_TODO_ENTITY):
                options.setdefault(key, [] if key == CONF_PRESENCE_ENTITIES else "")
            if title != self.config_entry.title:
                self.hass.config_entries.async_update_entry(self.config_entry, title=title)
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(step_id="connections", data_schema=_options_schema(current))

    async def async_step_mission_schedule(self, user_input=None) -> ConfigFlowResult:
        vacuums = list(self._planner.vacuums)
        if user_input is not None:
            if user_input.get("delete_mission"):
                return await self.async_step_delete_mission()
            self._mission_draft = {
                **self._mission,
                "name": user_input["mission_name"],
                "vacuum_entity_id": user_input["vacuum_entity_id"],
                "weekdays": list(user_input.get("weekdays") or []),
                "start_time": str(user_input.get("start_time") or "09:00")[:5],
                "schedule_entity_id": user_input.get("schedule_entity_id") or None,
                "enabled": bool(user_input.get("enabled", True)),
                "announce_before_minutes": int(user_input.get("announce_before_minutes", 1440)),
                "guards": {
                    **(self._mission.get("guards") or {}),
                    "people_home": user_input.get("people_home") or "wait",
                },
            }
            return await self.async_step_mission_profile()
        return self.async_show_form(
            step_id="mission_schedule",
            data_schema=_mission_schedule_schema(
                vacuums,
                self._mission,
                can_delete=any(
                    mission.id == self._mission.get("id")
                    for mission in self._planner.missions
                ),
            ),
        )

    async def async_step_mission_profile(self, user_input=None) -> ConfigFlowResult:
        vacuum_entity_id = self._mission_draft["vacuum_entity_id"]
        profile = self._mission.get("profile") or {}
        current = {
            "areas": self._mission.get("areas") or [],
            "profile_mode": profile.get("mode") or "vacuum",
            "fan": profile.get("fan"),
            "water": profile.get("water"),
            "passes": profile.get("passes") or 1,
        }
        options = discover_profile_options(self.hass, vacuum_entity_id)
        if user_input is not None:
            mode = str(user_input.get("profile_mode") or "vacuum")
            mission = {
                **self._mission_draft,
                "areas": list(user_input.get("areas") or []),
                "profile": {
                    "mode": mode,
                    "fan": user_input.get("fan") or None,
                    "water": user_input.get("water") or None if mode != "vacuum" else None,
                    "passes": int(user_input.get("passes") or 1),
                },
            }
            await self._planner.async_add_mission(mission)
            return self.async_create_entry(title="", data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="mission_profile",
            data_schema=_profile_schema(options, current),
            description_placeholders={
                "vacuum": self.hass.states.get(vacuum_entity_id).attributes.get(
                    "friendly_name", vacuum_entity_id
                )
                if self.hass.states.get(vacuum_entity_id)
                else vacuum_entity_id,
                "adapter": str(options.get("adapter") or "home_assistant"),
            },
        )

    async def async_step_delete_mission(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            if user_input.get("confirm_delete"):
                await self._planner.async_remove_mission(str(self._mission["id"]))
                return self.async_create_entry(title="", data=dict(self.config_entry.options))
            return await self.async_step_mission_schedule()
        return self.async_show_form(
            step_id="delete_mission",
            data_schema=vol.Schema(
                {vol.Required("confirm_delete", default=False): selector.BooleanSelector()}
            ),
            description_placeholders={"mission": str(self._mission.get("name") or "")},
        )
