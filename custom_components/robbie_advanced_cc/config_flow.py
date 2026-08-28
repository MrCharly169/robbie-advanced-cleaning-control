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
    CONF_EXTERNAL_START_POLICY,
    CONF_NOTIFY_COMPLETION,
    CONF_NOTIFY_MAINTENANCE,
    CONF_NOTIFICATION_ROUTE,
    CONF_NOTIFICATION_SCRIPT,
    CONF_PRESENCE_ENTITIES,
    CONF_ROBOT_NAMES,
    CONF_STARTER_MISSION,
    CONF_TODO_ENTITY,
    CONF_VACATION_ENTITY,
    CONF_VACUUMS,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_EXTERNAL_START_POLICY,
    DEFAULT_NAME,
    DOMAIN,
)
from .models import WEEKDAYS
from .notifications import default_robot_display_name


def _optional(key: str, value: Any = None) -> vol.Optional:
    if value in (None, "", []):
        return vol.Optional(key)
    return vol.Optional(key, description={"suggested_value": value})


def _dashboard_path(value: Any) -> str:
    """Return a safe Home Assistant path for the Cleaning Control Card."""
    path = str(value or DEFAULT_DASHBOARD_PATH).strip()
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        raise ValueError("dashboard_path must be an absolute Home Assistant path")
    return path


def _robot_default(hass, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    return default_robot_display_name(
        entity_id,
        str(state.attributes.get("friendly_name") or "") if state else None,
    )


def _robot_name_schema(current: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("robot_name", default=current): selector.TextSelector()
        }
    )


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
            vol.Required(
                CONF_NOTIFY_COMPLETION,
                default=current.get(CONF_NOTIFY_COMPLETION, True),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_NOTIFY_MAINTENANCE,
                default=current.get(CONF_NOTIFY_MAINTENANCE, True),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_EXTERNAL_START_POLICY,
                default=current.get(
                    CONF_EXTERNAL_START_POLICY, DEFAULT_EXTERNAL_START_POLICY
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["match_single_pending", "keep_pending"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
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
        {
            "value": "robots",
            "label": "Roboternamen" if de else "Robot names",
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
        self._robot_name_index = 0

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            vacuums = sorted(set(user_input[CONF_VACUUMS]))
            if not vacuums:
                return self.async_show_form(step_id="user", data_schema=_basics_schema(user_input), errors={"base": "no_vacuums"})
            await self.async_set_unique_id("|".join(vacuums))
            self._abort_if_unique_id_configured()
            self._data = dict(user_input)
            self._data[CONF_VACUUMS] = vacuums
            self._data[CONF_ROBOT_NAMES] = {}
            self._robot_name_index = 0
            return await self.async_step_robot_name()
        return self.async_show_form(step_id="user", data_schema=_basics_schema())

    async def async_step_robot_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        vacuums = self._data[CONF_VACUUMS]
        entity_id = vacuums[self._robot_name_index]
        fallback = _robot_default(self.hass, entity_id)
        names = self._data.setdefault(CONF_ROBOT_NAMES, {})
        if user_input is not None:
            names[entity_id] = str(user_input.get("robot_name") or "").strip() or fallback
            self._robot_name_index += 1
            if self._robot_name_index >= len(vacuums):
                return await self.async_step_presence()
            entity_id = vacuums[self._robot_name_index]
            fallback = _robot_default(self.hass, entity_id)
        state = self.hass.states.get(entity_id)
        return self.async_show_form(
            step_id="robot_name",
            data_schema=_robot_name_schema(str(names.get(entity_id) or fallback)),
            description_placeholders={
                "vacuum": str(state.attributes.get("friendly_name") or entity_id)
                if state
                else entity_id,
                "entity_id": entity_id,
            },
        )

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
            try:
                user_input[CONF_DASHBOARD_PATH] = _dashboard_path(
                    user_input.get(CONF_DASHBOARD_PATH)
                )
            except ValueError:
                return self.async_show_form(
                    step_id="services",
                    data_schema=_services_schema(user_input),
                    errors={CONF_DASHBOARD_PATH: "invalid_dashboard_path"},
                )
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
        self._robot_names: dict[str, str] = {}
        self._robot_name_index = 0

    @property
    def _planner(self):
        return self.config_entry.runtime_data

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            action = str(user_input["options_action"])
            if action == "connections":
                return await self.async_step_connections()
            if action == "robots":
                configured = self._planner.config.get(CONF_ROBOT_NAMES) or {}
                self._robot_names = (
                    dict(configured) if isinstance(configured, dict) else {}
                )
                self._robot_name_index = 0
                return await self.async_step_robot_names()
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
            # Home Assistant normally submits cleared optional selectors as
            # ``None``.  Other flow clients may omit untouched suggested values
            # entirely, so merge with the current entry before normalizing. This
            # keeps presence, vacation and routing bindings intact when only the
            # Cleaning Control destination is changed.
            editable_keys = (
                "name",
                CONF_VACUUMS,
                CONF_ROBOT_NAMES,
                CONF_PRESENCE_ENTITIES,
                CONF_VACATION_ENTITY,
                CONF_NOTIFICATION_SCRIPT,
                CONF_NOTIFICATION_ROUTE,
                CONF_TODO_ENTITY,
                CONF_NOTIFY_COMPLETION,
                CONF_NOTIFY_MAINTENANCE,
                CONF_EXTERNAL_START_POLICY,
                CONF_DASHBOARD_PATH,
            )
            options = {
                **{key: current[key] for key in editable_keys if key in current},
                **user_input,
            }
            if not options.get(CONF_VACUUMS):
                return self.async_show_form(step_id="connections", data_schema=_options_schema(user_input), errors={"base": "no_vacuums"})
            try:
                options[CONF_DASHBOARD_PATH] = _dashboard_path(
                    options.get(CONF_DASHBOARD_PATH)
                )
            except ValueError:
                return self.async_show_form(
                    step_id="connections",
                    data_schema=_options_schema(options),
                    errors={CONF_DASHBOARD_PATH: "invalid_dashboard_path"},
                )
            title = str(options.pop("name", self.config_entry.title))
            configured_names = options.get(CONF_ROBOT_NAMES) or {}
            if not isinstance(configured_names, dict):
                configured_names = {}
            options[CONF_ROBOT_NAMES] = {
                entity_id: str(configured_names.get(entity_id) or "").strip()
                or _robot_default(self.hass, entity_id)
                for entity_id in options[CONF_VACUUMS]
            }
            for key in (CONF_PRESENCE_ENTITIES, CONF_VACATION_ENTITY, CONF_NOTIFICATION_SCRIPT, CONF_NOTIFICATION_ROUTE, CONF_TODO_ENTITY):
                if options.get(key) is None:
                    options[key] = [] if key == CONF_PRESENCE_ENTITIES else ""
            if title != self.config_entry.title:
                self.hass.config_entries.async_update_entry(self.config_entry, title=title)
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(step_id="connections", data_schema=_options_schema(current))

    async def async_step_robot_names(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        vacuums = list(self._planner.vacuums)
        if not vacuums:
            return self.async_create_entry(
                title="", data=dict(self.config_entry.options)
            )
        entity_id = vacuums[self._robot_name_index]
        fallback = _robot_default(self.hass, entity_id)
        if user_input is not None:
            self._robot_names[entity_id] = (
                str(user_input.get("robot_name") or "").strip() or fallback
            )
            self._robot_name_index += 1
            if self._robot_name_index >= len(vacuums):
                options = dict(self.config_entry.options)
                options[CONF_ROBOT_NAMES] = {
                    item: self._robot_names[item] for item in vacuums
                }
                return self.async_create_entry(title="", data=options)
            entity_id = vacuums[self._robot_name_index]
            fallback = _robot_default(self.hass, entity_id)
        state = self.hass.states.get(entity_id)
        return self.async_show_form(
            step_id="robot_names",
            data_schema=_robot_name_schema(
                str(self._robot_names.get(entity_id) or fallback)
            ),
            description_placeholders={
                "vacuum": str(state.attributes.get("friendly_name") or entity_id)
                if state
                else entity_id,
                "entity_id": entity_id,
            },
        )

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
