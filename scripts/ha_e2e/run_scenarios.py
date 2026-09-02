#!/usr/bin/env python3
"""Exercise Robbie Advanced CC through a real Home Assistant HTTP API."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


VACUUM_VALETUDO = "vacuum.valetudo_fixture_robot"
VACUUM_CLOUD = "vacuum.cloud_fixture_robot"
VALETUDO_MODE = "select.valetudo_fixture_robot_mode"
VALETUDO_FAN = "select.valetudo_fixture_robot_fan"
VALETUDO_WATER = "select.valetudo_fixture_robot_water"
MOP_SENSOR = "binary_sensor.valetudo_fixture_robot_mop_attachment"
ERROR_SENSOR = "sensor.valetudo_fixture_robot_error"
DOCK_STATUS_SENSOR = "sensor.valetudo_fixture_robot_dock_status"
STATUS_FLAG_SENSOR = "sensor.valetudo_fixture_robot_status_flag"
FRESHWATER_SENSOR = "sensor.valetudo_fixture_robot_water_tank_clean_dock_component"
WASTEWATER_SENSOR = "sensor.valetudo_fixture_robot_water_tank_dirty_dock_component"
EVENTS_SENSOR = "sensor.valetudo_fixture_robot_events"
CALL_SENSOR = "sensor.robbie_fixture_service_calls"
DOMAIN = "robbie_advanced_cc"
FIXTURE = "robbie_advanced_cc_test_fixture"


@dataclass
class ApiError(RuntimeError):
    method: str
    path: str
    status: int
    body: str

    def __str__(self) -> str:
        return f"{self.method} {self.path} failed with HTTP {self.status}: {self.body}"


class HomeAssistantApi:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        *,
        form: bool = False,
        authenticated: bool = True,
        raw: bool = False,
    ) -> Any:
        headers: dict[str, str] = {}
        payload = None
        if data is not None:
            if form:
                payload = urlencode(data).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                payload = json.dumps(data).encode()
                headers["Content-Type"] = "application/json"
        if authenticated and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(
            f"{self.base_url}{path}", data=payload, headers=headers, method=method
        )
        try:
            with urlopen(request, timeout=20) as response:
                body = response.read().decode()
                return body if raw else (json.loads(body) if body else None)
        except HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise ApiError(method, path, exc.code, body) from exc

    def get(self, path: str, *, authenticated: bool = True, raw: bool = False) -> Any:
        return self.request("GET", path, authenticated=authenticated, raw=raw)

    def post(
        self,
        path: str,
        data: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
    ) -> Any:
        return self.request("POST", path, data or {}, authenticated=authenticated)

    def call_service(self, domain: str, service: str, data: dict[str, Any]) -> Any:
        return self.post(f"/api/services/{domain}/{service}", data)


def wait_for_home_assistant(api: HomeAssistantApi, timeout: int = 240) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            path = "/api/config" if api.token else "/api/onboarding"
            api.get(path, authenticated=bool(api.token))
            return
        except (URLError, ApiError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"Home Assistant did not become ready: {last_error}")


def onboard(api: HomeAssistantApi) -> str:
    client_id = f"{api.base_url}/"
    user = api.post(
        "/api/onboarding/users",
        {
            "client_id": client_id,
            "name": "Robbie Advanced CC E2E",
            "username": "e2e-owner",
            "password": "e2e-only-disposable-password",
            "language": "en",
        },
        authenticated=False,
    )
    token = api.request(
        "POST",
        "/auth/token",
        {
            "grant_type": "authorization_code",
            "code": user["auth_code"],
            "client_id": client_id,
        },
        form=True,
        authenticated=False,
    )
    api.token = str(token["access_token"])
    onboarding = api.get("/api/onboarding", authenticated=False)
    done = {str(item.get("step")) for item in onboarding if item.get("done")}
    available = {str(item.get("step")) for item in onboarding}
    if "core_config" in available and "core_config" not in done:
        api.post(
            "/api/onboarding/core_config",
            {
                "latitude": 49.6116,
                "longitude": 6.1319,
                "elevation": 300,
                "unit_system": "metric",
                "location_name": "Robbie Advanced CC Lab",
                "time_zone": "Europe/Luxembourg",
                "currency": "EUR",
            },
        )
    if "integration" in available and "integration" not in done:
        api.post(
            "/api/onboarding/integration",
            {
                "client_id": client_id,
                "redirect_uri": f"{api.base_url}/onboarding.html?auth_callback=1",
            },
        )
    if "analytics" in available and "analytics" not in done:
        api.post("/api/onboarding/analytics", {})
    remaining = [item for item in api.get("/api/onboarding", authenticated=False) if not item.get("done")]
    if remaining:
        raise AssertionError(f"Home Assistant onboarding remains incomplete: {remaining}")
    return api.token


def wait_for_state(api: HomeAssistantApi, entity_id: str, predicate=lambda _x: True, timeout: int = 60) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        try:
            last = api.get(f"/api/states/{entity_id}")
            if predicate(last):
                return last
        except ApiError as exc:
            if exc.status != 404:
                raise
        time.sleep(1)
    raise AssertionError(f"Timed out waiting for {entity_id}; last state: {last}")


def entries(api: HomeAssistantApi) -> list[dict[str, Any]]:
    return [
        item
        for item in api.get("/api/config/config_entries/entry")
        if item.get("domain") == DOMAIN
    ]


def wait_for_entry(api: HomeAssistantApi, entry_id: str, timeout: int = 60) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = next((item for item in entries(api) if item.get("entry_id") == entry_id), None)
        if last and last.get("state") == "loaded":
            return last
        time.sleep(1)
    raise AssertionError(f"Entry {entry_id} was not loaded: {last}")


def planner_states(api: HomeAssistantApi, entry_id: str) -> list[dict[str, Any]]:
    return [
        state
        for state in api.get("/api/states")
        if str(state.get("attributes", {}).get("entry_id", "")) == entry_id
    ]


def planner_status(api: HomeAssistantApi, entry_id: str) -> dict[str, Any]:
    matches = [
        state
        for state in planner_states(api, entry_id)
        if "managed_vacuums" in state.get("attributes", {})
    ]
    if len(matches) != 1:
        raise AssertionError(f"Expected one planner status sensor, got {matches}")
    return matches[0]


def wait_for_mission_count(api: HomeAssistantApi, entry_id: str, count: int) -> dict[str, Any]:
    deadline = time.monotonic() + 60
    last = None
    while time.monotonic() < deadline:
        last = planner_status(api, entry_id)
        if last.get("attributes", {}).get("mission_count") == count:
            return last
        time.sleep(1)
    raise AssertionError(f"Mission count did not become {count}: {last}")


def wait_for_completed(api: HomeAssistantApi, entry_id: str) -> dict[str, Any]:
    """Wait for the delayed final-docking confirmation."""
    status = planner_status(api, entry_id)
    return wait_for_state(
        api,
        status["entity_id"],
        lambda state: state["state"] == "completed"
        and state.get("attributes", {}).get("active_vacuum_entity_id") is None,
    )


def fixture_calls(api: HomeAssistantApi) -> list[dict[str, Any]]:
    return list(wait_for_state(api, CALL_SENSOR).get("attributes", {}).get("calls") or [])


def reset_calls(api: HomeAssistantApi) -> None:
    api.call_service(FIXTURE, "reset_calls", {})
    wait_for_state(api, CALL_SENSOR, lambda state: state["state"] == "0")


def set_fixture(
    api: HomeAssistantApi,
    entity_id: str,
    state: Any,
    *,
    attributes: dict[str, Any] | None = None,
    available: bool = True,
) -> None:
    api.call_service(
        FIXTURE,
        "set_state",
        {
            "entity_id": entity_id,
            "state": state,
            "attributes": attributes or {},
            "available": available,
        },
    )
    expected = "unavailable" if not available else str(state).lower()
    wait_for_state(api, entity_id, lambda item: item["state"].lower() == expected)


def add_mission(api: HomeAssistantApi, entry_id: str, mission: dict[str, Any]) -> None:
    api.call_service(DOMAIN, "add_mission", {"entry_id": entry_id, "mission": mission})


def assert_last_reason(api: HomeAssistantApi, entry_id: str, reason: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    last = None
    while time.monotonic() < deadline:
        matches = [
            state
            for state in api.get("/api/states")
            if state["entity_id"].startswith("sensor.")
            and state.get("attributes", {}).get("resolution") is not None
        ]
        matching = [state for state in matches if state["state"] == reason]
        if matching:
            return matching[0]
        last = matches
        time.sleep(1)
    raise AssertionError(f"Decision reason did not become {reason}: {last}")


def create_entry(api: HomeAssistantApi) -> str:
    result = api.post(
        "/api/config/config_entries/flow",
        {"handler": DOMAIN, "show_advanced_options": True},
    )
    if result.get("step_id") != "user":
        raise AssertionError(f"Unexpected config-flow start: {result}")
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {
            "name": "Robbie E2E Planner",
            "vacuums": [VACUUM_VALETUDO, VACUUM_CLOUD],
        },
    )
    configured_names = {
        VACUUM_VALETUDO: "Robby Lab",
        VACUUM_CLOUD: "Cloudy Lab",
    }
    for _ in configured_names:
        if result.get("step_id") != "robot_name":
            raise AssertionError(f"Robot name wizard step failed: {result}")
        entity_id = result.get("description_placeholders", {}).get("entity_id")
        if entity_id not in configured_names:
            raise AssertionError(f"Robot name step exposed an unknown robot: {result}")
        result = api.post(
            f"/api/config/config_entries/flow/{result['flow_id']}",
            {"robot_name": configured_names[entity_id]},
        )
    if result.get("step_id") != "presence":
        raise AssertionError(f"Presence wizard step failed: {result}")
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {
            "presence_entities": ["input_number.home_occupants"],
            "vacation_entity": "input_boolean.vacation_mode",
        },
    )
    if result.get("step_id") != "schedule":
        raise AssertionError(f"Schedule wizard step failed: {result}")
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {"create_starter_mission": False},
    )
    if result.get("step_id") != "services":
        raise AssertionError(f"Services wizard step failed: {result}")
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {
            "notification_script": "script.robbie_notification_router_test",
            "notification_route": "input_text.notify_route_test",
            "dashboard_path": "/lovelace/cleaning",
        },
    )
    if result.get("type") != "create_entry":
        raise AssertionError(f"Config flow failed: {result}")
    entry_id = result.get("result", {}).get("entry_id")
    if not entry_id:
        raise AssertionError(f"Config flow did not return an entry ID: {result}")
    return str(entry_id)


def validate_dynamic_profile_flow(api: HomeAssistantApi) -> None:
    """Prove the assistant builds robot-specific selectors before entry creation."""
    result = api.post(
        "/api/config/config_entries/flow",
        {"handler": DOMAIN, "show_advanced_options": True},
    )
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {"name": "Dynamic profile probe", "vacuums": [VACUUM_VALETUDO]},
    )
    if result.get("step_id") != "robot_name":
        raise AssertionError(f"Dynamic robot name step failed: {result}")
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {"robot_name": "Selector Robby"},
    )
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {"presence_entities": ["input_number.home_occupants"]},
    )
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {
            "create_starter_mission": True,
            "mission_name": "Selector probe",
            "vacuum_entity_id": VACUUM_VALETUDO,
            "weekdays": ["mon"],
            "start_time": "09:00:00",
            "people_home": "wait",
        },
    )
    if result.get("step_id") != "profile":
        raise AssertionError(f"Dynamic profile wizard step failed: {result}")
    schema = json.dumps(result.get("data_schema", []), sort_keys=True)
    for expected in ("areas", "Kitchen", "profile_mode", "fan", "max", "water", "passes"):
        if expected not in schema:
            raise AssertionError(f"Profile selector is missing {expected}: {result}")
    result = api.post(
        f"/api/config/config_entries/flow/{result['flow_id']}",
        {
            "areas": ["kitchen"],
            "profile_mode": "vacuum_and_mop",
            "fan": "high",
            "water": "medium",
            "passes": "2",
        },
    )
    if result.get("step_id") != "services":
        raise AssertionError(f"Dynamic profile selection failed: {result}")


def test_options_flow(api: HomeAssistantApi, entry_id: str) -> None:
    result = api.post("/api/config/config_entries/options/flow", {"handler": entry_id})
    if result.get("step_id") != "init":
        raise AssertionError(f"Options flow did not start: {result}")
    result = api.post(
        f"/api/config/config_entries/options/flow/{result['flow_id']}",
        {"options_action": "connections"},
    )
    if result.get("step_id") != "connections":
        raise AssertionError(f"Connections options step failed: {result}")
    result = api.post(
        f"/api/config/config_entries/options/flow/{result['flow_id']}",
        {
            "name": "Robbie E2E Planner",
            "vacuums": [VACUUM_VALETUDO, VACUUM_CLOUD],
            "presence_entities": ["input_number.home_occupants"],
            "vacation_entity": "input_boolean.vacation_mode",
            "notification_script": "script.robbie_notification_router_test",
            "notification_route": "input_text.notify_route_test",
            "dashboard_path": "/lovelace/cleaning",
        },
    )
    if result.get("type") != "create_entry":
        raise AssertionError(f"Options flow failed: {result}")
    wait_for_entry(api, entry_id)

    # A path-only client must not erase optional bindings merely because HA
    # represented their current values as suggestions instead of defaults.
    result = api.post("/api/config/config_entries/options/flow", {"handler": entry_id})
    flow_id = result["flow_id"]
    result = api.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        {"options_action": "connections"},
    )
    result = api.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        {
            "name": "Robbie E2E Planner",
            "vacuums": [VACUUM_VALETUDO, VACUUM_CLOUD],
            "dashboard_path": "/lovelace/cleaning",
        },
    )
    if result.get("type") != "create_entry":
        raise AssertionError(f"Path-only options update failed: {result}")
    wait_for_entry(api, entry_id)

    result = api.post("/api/config/config_entries/options/flow", {"handler": entry_id})
    flow_id = result["flow_id"]
    result = api.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        {"options_action": "connections"},
    )
    values = {
        field["name"]: (
            field["default"]
            if "default" in field
            else (field.get("description") or {}).get("suggested_value")
        )
        for field in result.get("data_schema", [])
    }
    expected = {
        "presence_entities": ["input_number.home_occupants"],
        "vacation_entity": "input_boolean.vacation_mode",
        "notification_script": "script.robbie_notification_router_test",
        "notification_route": "input_text.notify_route_test",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise AssertionError(f"Path-only update lost {key}: {values}")
    api.request(
        "DELETE",
        f"/api/config/config_entries/options/flow/{flow_id}",
    )

    result = api.post("/api/config/config_entries/options/flow", {"handler": entry_id})
    flow_id = result["flow_id"]
    result = api.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        {"options_action": "robots"},
    )
    configured_names = {
        VACUUM_VALETUDO: "Robby Options",
        VACUUM_CLOUD: "Cloudy Options",
    }
    for _ in configured_names:
        if result.get("step_id") != "robot_names":
            raise AssertionError(f"Robot name options step failed: {result}")
        entity_id = result.get("description_placeholders", {}).get("entity_id")
        result = api.post(
            f"/api/config/config_entries/options/flow/{flow_id}",
            {"robot_name": configured_names[entity_id]},
        )
    if result.get("type") != "create_entry":
        raise AssertionError(f"Robot names were not saved: {result}")
    wait_for_entry(api, entry_id)
    status = planner_status(api, entry_id)
    if status.get("attributes", {}).get("robot_names") != configured_names:
        raise AssertionError(
            f"Robot names were not projected consistently: {status}"
        )


def edit_mission_options_flow(api: HomeAssistantApi, entry_id: str, mission_id: str) -> None:
    """Prove every persisted mission remains editable after initial setup."""
    result = api.post("/api/config/config_entries/options/flow", {"handler": entry_id})
    flow_id = result["flow_id"]
    result = api.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        {"options_action": mission_id},
    )
    if result.get("step_id") != "mission_schedule":
        raise AssertionError(f"Mission schedule editor did not open: {result}")
    result = api.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        {
            "mission_name": "Valetudo area clean",
            "vacuum_entity_id": VACUUM_VALETUDO,
            "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_time": "23:59:00",
            "people_home": "wait",
            "enabled": True,
            "announce_before_minutes": 30,
            "delete_mission": False,
        },
    )
    if result.get("step_id") != "mission_profile":
        raise AssertionError(f"Mission profile editor did not open: {result}")
    result = api.post(
        f"/api/config/config_entries/options/flow/{flow_id}",
        {
            "areas": ["kitchen", "living_room"],
            "profile_mode": "vacuum_and_mop",
            "fan": "high",
            "water": "high",
            "passes": "1",
        },
    )
    if result.get("type") != "create_entry":
        raise AssertionError(f"Mission edit was not saved: {result}")
    wait_for_entry(api, entry_id)
    status = planner_status(api, entry_id)
    mission = next(
        (item for item in status.get("attributes", {}).get("missions", []) if item.get("id") == mission_id),
        None,
    )
    if mission is None or mission.get("announce_before_minutes") != 30:
        raise AssertionError(f"Mission edit did not persist: {mission}")


def assert_command(calls: list[dict[str, Any]], service: str, **data: Any) -> None:
    for call in calls:
        if call.get("service") == service and all(call.get("data", {}).get(key) == value for key, value in data.items()):
            return
    raise AssertionError(f"Missing fixture command {service} {data}: {calls}")


def set_notification_sentinel(api: HomeAssistantApi, token: str) -> None:
    """Mark both routed notification fields before an expected silent action."""
    for entity_id in (
        "input_text.notify_title_capture",
        "input_text.notify_message_capture",
    ):
        api.call_service(
            "input_text",
            "set_value",
            {"entity_id": entity_id, "value": token},
        )


def assert_notification_silent(api: HomeAssistantApi, token: str) -> None:
    """Prove that expected planner control flow did not emit a push."""
    time.sleep(1)
    for entity_id in (
        "input_text.notify_title_capture",
        "input_text.notify_message_capture",
    ):
        value = api.get(f"/api/states/{entity_id}")["state"]
        if value != token:
            raise AssertionError(
                f"Expected silent planner decision changed {entity_id}: {value}"
            )


def run_bootstrap(api: HomeAssistantApi, state_file: Path, output_dir: Path) -> None:
    token = onboard(api)
    for entity_id in (
        VACUUM_VALETUDO,
        VACUUM_CLOUD,
        VALETUDO_MODE,
        VALETUDO_FAN,
        VALETUDO_WATER,
        MOP_SENSOR,
        CALL_SENSOR,
        DOCK_STATUS_SENSOR,
        STATUS_FLAG_SENSOR,
    ):
        wait_for_state(api, entity_id)

    mapping = {"kitchen": ["16"], "living_room": ["17"], "bathroom": ["18"]}
    for vacuum in (VACUUM_VALETUDO, VACUUM_CLOUD):
        api.call_service(FIXTURE, "map_areas", {"entity_id": vacuum, "mapping": mapping})

    validate_dynamic_profile_flow(api)
    entry_id = create_entry(api)
    wait_for_entry(api, entry_id)
    initial_status = wait_for_mission_count(api, entry_id, 0)
    profile_options = initial_status.get("attributes", {}).get("profile_options", {})
    valetudo_profile = profile_options.get(VACUUM_VALETUDO, {})
    cloud_profile = profile_options.get(VACUUM_CLOUD, {})
    if [item.get("value") for item in valetudo_profile.get("areas", [])] != [
        "kitchen", "living_room", "bathroom"
    ]:
        raise AssertionError(f"Valetudo room choices were not discovered: {valetudo_profile}")
    if [item.get("value") for item in valetudo_profile.get("fan_speeds", [])] != [
        "low", "medium", "high", "max"
    ]:
        raise AssertionError(f"Valetudo fan choices were not discovered: {valetudo_profile}")
    if [item.get("value") for item in valetudo_profile.get("water_levels", [])] != [
        "low", "medium", "high"
    ]:
        raise AssertionError(f"Valetudo water choices were not discovered: {valetudo_profile}")
    if cloud_profile.get("water_levels"):
        raise AssertionError(f"Unsupported cloud water choices must stay hidden: {cloud_profile}")
    initial_planner_sensors = planner_states(api, entry_id)
    if len(initial_planner_sensors) != 4:
        raise AssertionError(
            "Every planner sensor must expose its owning entry_id: "
            f"{initial_planner_sensors}"
        )

    # Hardware errors are native planner attention states even while no run is
    # active, so a Dashboard Visibility condition on ``failed`` can reveal the
    # Robbie Badge. Valetudo's detailed sibling is authoritative even if the
    # vacuum entity itself has not switched state yet.
    set_fixture(api, ERROR_SENSOR, "Auto-empty dock is blocked")
    detailed_error = wait_for_state(
        api,
        initial_status["entity_id"],
        lambda state: state["state"] == "failed"
        and state.get("attributes", {}).get("has_robot_error") is True,
    )
    error_details = detailed_error.get("attributes", {}).get("robot_errors", {})
    if error_details.get(VACUUM_VALETUDO, {}).get("message") != "Auto-empty dock is blocked":
        raise AssertionError(f"Valetudo error was not projected: {detailed_error}")
    wait_for_state(
        api,
        "input_text.notify_message_capture",
        lambda state: "Auto empty dock is blocked" in state["state"],
    )
    set_fixture(api, ERROR_SENSOR, "No error")
    wait_for_state(
        api,
        initial_status["entity_id"],
        lambda state: state["state"] != "failed"
        and state.get("attributes", {}).get("has_robot_error") is False,
    )

    # Generic/cloud vacuums use Home Assistant's standard error activity.
    set_fixture(api, VACUUM_CLOUD, "error")
    generic_error = wait_for_state(
        api,
        initial_status["entity_id"],
        lambda state: state["state"] == "failed"
        and state.get("attributes", {}).get("has_robot_error") is True,
    )
    if VACUUM_CLOUD not in generic_error.get("attributes", {}).get("robot_errors", {}):
        raise AssertionError(f"Generic vacuum error was not projected: {generic_error}")
    wait_for_state(
        api,
        "input_text.notify_message_capture",
        lambda state: "Robot reported an error" in state["state"],
    )
    set_fixture(api, VACUUM_CLOUD, "docked")
    wait_for_state(
        api,
        initial_status["entity_id"],
        lambda state: state["state"] != "failed"
        and state.get("attributes", {}).get("has_robot_error") is False,
    )
    card = api.get(f"/{DOMAIN}/cleaning-control.js", authenticated=False, raw=True)
    if "customElements.define" not in card or "robbie-advanced-cleaning-card" not in card or "robbie-vacuum-badge" not in card:
        raise AssertionError("Frontend resource did not return the expected card module")
    valetudo = {
        "id": "valetudo_area",
        "name": "Valetudo area clean",
        "vacuum_entity_id": VACUUM_VALETUDO,
        "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "start_time": "23:59",
        "areas": ["kitchen", "living_room"],
        "profile": {"mode": "vacuum_and_mop", "fan": "high", "water": "high", "passes": 1},
        "guards": {"vacation": "block", "mop_missing": "block", "vacuum_unavailable": "postpone", "people_home": "wait"},
        "announce_before_minutes": 1440,
    }
    add_mission(api, entry_id, valetudo)
    projected = wait_for_mission_count(api, entry_id, 1)
    projected_missions = projected.get("attributes", {}).get("missions", [])
    if len(projected_missions) != 1 or projected_missions[0].get("id") != valetudo["id"]:
        raise AssertionError(f"Planner status did not project its mission: {projected_missions}")
    conditions = projected_missions[0].get("conditions", [])
    if not conditions or not all({"key", "enabled", "passed", "resolution", "entities"} <= item.keys() for item in conditions):
        raise AssertionError(f"Planner status condition trace is incomplete: {conditions}")
    reset_calls(api)
    api.call_service(
        DOMAIN,
        "run_next",
        {"entry_id": entry_id, "mission_id": valetudo["id"], "manual": True},
    )
    calls = fixture_calls(api)
    assert_command(calls, "select_option", option="vacuum_and_mop")
    assert_command(calls, "select_option", option="high")
    assert_command(calls, "clean_segments", segment_ids=["16", "17"])
    if any(call.get("service") == "set_fan_speed" for call in calls):
        raise AssertionError(f"Valetudo fan profile was sent twice: {calls}")
    set_fixture(api, VACUUM_VALETUDO, "docked")
    wait_for_completed(api, entry_id)

    cloud = {
        **valetudo,
        "id": "cloud_area",
        "name": "Cloud area clean",
        "vacuum_entity_id": VACUUM_CLOUD,
        "areas": ["bathroom"],
        "profile": {"mode": "vacuum", "fan": "max", "passes": 1},
    }
    add_mission(api, entry_id, cloud)
    wait_for_mission_count(api, entry_id, 2)
    reset_calls(api)
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": cloud["id"]})
    calls = fixture_calls(api)
    assert_command(calls, "set_fan_speed", fan_speed="max")
    assert_command(calls, "clean_segments", segment_ids=["18"])
    set_fixture(api, VACUUM_CLOUD, "docked")
    wait_for_completed(api, entry_id)

    set_fixture(api, MOP_SENSOR, "off")
    set_notification_sentinel(api, "Silent mop guard")
    reset_calls(api)
    api.call_service(
        DOMAIN,
        "run_next",
        {"entry_id": entry_id, "mission_id": valetudo["id"], "manual": True},
    )
    assert_last_reason(api, entry_id, "mop_missing")
    assert_notification_silent(api, "Silent mop guard")
    if fixture_calls(api):
        raise AssertionError("Mop guard allowed a device command")
    set_fixture(api, MOP_SENSOR, "on")

    presence_wait = {
        **valetudo,
        "id": "presence_wait",
        "name": "VacOnly",
        "profile": {"mode": "vacuum", "passes": 1},
        "guards": {"people_home": "wait"},
    }
    add_mission(api, entry_id, presence_wait)
    wait_for_mission_count(api, entry_id, 3)
    api.call_service("input_number", "set_value", {"entity_id": "input_number.home_occupants", "value": 2})
    set_notification_sentinel(api, "Silent presence wait")
    reset_calls(api)
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": presence_wait["id"]})
    assert_last_reason(api, entry_id, "people_home")
    assert_notification_silent(api, "Silent presence wait")
    waiting = planner_status(api, entry_id)
    if presence_wait["id"] not in waiting.get("attributes", {}).get("waiting_mission_ids", []):
        raise AssertionError(f"Presence wait was not armed: {waiting}")
    reset_calls(api)
    api.call_service(
        DOMAIN,
        "run_next",
        {"entry_id": entry_id, "mission_id": presence_wait["id"], "manual": True},
    )
    assert_command(fixture_calls(api), "clean_segments", segment_ids=["16", "17"])
    manual_status = planner_status(api, entry_id)
    if presence_wait["id"] in manual_status.get("attributes", {}).get("waiting_mission_ids", []):
        raise AssertionError(f"Manual start did not consume the waiting mission: {manual_status}")
    if manual_status.get("state") != "running":
        raise AssertionError(f"Manual start did not present running: {manual_status}")
    if manual_status.get("attributes", {}).get("last_allowed") is not True:
        raise AssertionError(f"Manual start was not recorded as allowed: {manual_status}")
    set_fixture(api, VACUUM_VALETUDO, "docked")
    wait_for_completed(api, entry_id)

    # A scheduled/service evaluation without the explicit manual flag still
    # honors presence and arms the mission again.
    api.call_service("input_number", "set_value", {"entity_id": "input_number.home_occupants", "value": 2})
    reset_calls(api)
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": presence_wait["id"]})
    assert_last_reason(api, entry_id, "people_home")
    waiting = planner_status(api, entry_id)
    if presence_wait["id"] not in waiting.get("attributes", {}).get("waiting_mission_ids", []):
        raise AssertionError(f"Presence wait was not re-armed: {waiting}")

    # Editing the weekly schedule invalidates only the already-due occurrence
    # when today/time no longer match. The recurring mission remains editable
    # and future days are recalculated immediately.
    add_mission(api, entry_id, {**presence_wait, "weekdays": []})
    schedule_recomputed = wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state["state"] == "idle"
        and state.get("attributes", {}).get("last_reason")
        == "pending_schedule_changed"
        and presence_wait["id"]
        not in state.get("attributes", {}).get("waiting_mission_ids", []),
    )
    if schedule_recomputed.get("attributes", {}).get("mission_count") != 3:
        raise AssertionError(
            f"Schedule edit removed the recurring mission: {schedule_recomputed}"
        )
    add_mission(api, entry_id, presence_wait)
    api.call_service(
        DOMAIN,
        "run_next",
        {"entry_id": entry_id, "mission_id": presence_wait["id"]},
    )
    wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: presence_wait["id"]
        in state.get("attributes", {}).get("waiting_mission_ids", []),
    )

    # A direct native vacuum start can safely own the single waiting occurrence
    # for that same robot. This prevents a completed physical run from being
    # presented and executed again as stale waiting work.
    reset_calls(api)
    api.call_service("vacuum", "start", {"entity_id": VACUUM_VALETUDO})
    direct_running = wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state["state"] == "running",
    )
    if presence_wait["id"] in direct_running.get("attributes", {}).get("waiting_mission_ids", []):
        raise AssertionError(f"Direct vacuum start did not own queued work: {direct_running}")

    # Valetudo reports a short docked interval while washing the mop. Its
    # resumable status must keep the same physical run alive and must not emit
    # a completion notification.
    api.call_service(
        "input_text",
        "set_value",
        {
            "entity_id": "input_text.notify_title_capture",
            "value": "No intermediate completion",
        },
    )
    set_fixture(api, DOCK_STATUS_SENSOR, "cleaning")
    set_fixture(api, STATUS_FLAG_SENSOR, "resumable")
    set_fixture(api, VACUUM_VALETUDO, "docked")
    wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state["state"] == "dock_service",
    )
    time.sleep(6)
    if planner_status(api, entry_id)["state"] != "dock_service":
        raise AssertionError("Resumable mop wash was reported as completed")
    if api.get("/api/states/input_text.notify_title_capture")["state"] != "No intermediate completion":
        raise AssertionError("Resumable mop wash emitted a completion notification")

    set_fixture(api, VACUUM_VALETUDO, "cleaning")
    set_fixture(api, STATUS_FLAG_SENSOR, "none")
    set_fixture(api, DOCK_STATUS_SENSOR, "idle")
    wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state["state"] == "running",
    )
    set_fixture(api, VACUUM_VALETUDO, "docked")
    completed = wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state["state"] == "completed"
        and state.get("attributes", {}).get("last_reason") == "mission_completed",
    )
    if completed.get("attributes", {}).get("waiting_mission_ids"):
        raise AssertionError(f"Completed run retained stale waiting work: {completed}")
    wait_for_state(
        api,
        "input_text.notify_title_capture",
        lambda state: state["state"] == "🤖 Robby Lab · Cleaning completed",
    )
    wait_for_state(
        api,
        "input_text.notify_message_capture",
        lambda state: "Mission: Vacuum only." in state["state"]
        and "VacOnly" not in state["state"]
        and "64.0 m²" in state["state"]
        and "1 h 22 min" in state["state"],
    )

    # Valetudo 2026.05+ dock component states and active ValetudoEvents are
    # projected as maintenance attention and routed exactly once per change.
    set_fixture(api, WASTEWATER_SENSOR, "full")
    wait_for_state(
        api,
        "input_text.notify_message_capture",
        lambda state: "Wastewater is full" in state["state"],
    )
    maintenance_attention = next(
        state
        for state in api.get("/api/states")
        if state["entity_id"].startswith("sensor.")
        and "items" in state.get("attributes", {})
    )
    wait_for_state(
        api,
        maintenance_attention["entity_id"],
        lambda state: state["state"] == "attention",
    )
    set_fixture(api, WASTEWATER_SENSOR, "ok")
    set_fixture(
        api,
        EVENTS_SENSOR,
        1,
        attributes={
            "dust-event": {
                "id": "dust-event",
                "__class": "DustBinFullValetudoEvent",
                "processed": False,
            }
        },
    )
    wait_for_state(
        api,
        "input_text.notify_message_capture",
        lambda state: "Dustbin is full" in state["state"],
    )
    set_fixture(api, EVENTS_SENSOR, 0, attributes={})
    wait_for_state(
        api,
        maintenance_attention["entity_id"],
        lambda state: state["state"] == "ok",
    )
    set_fixture(
        api,
        ERROR_SENSOR,
        "Mop Dock Clean Water Tank empty",
        attributes={
            "subsystem": "dock",
            "severity": {"kind": "permanent", "level": "warning"},
        },
    )
    wait_for_state(
        api,
        "input_text.notify_message_capture",
        lambda state: "Mop Dock Clean Water Tank empty" in state["state"],
    )
    wait_for_state(
        api,
        maintenance_attention["entity_id"],
        lambda state: state["state"] == "attention"
        and any(
            item.get("source") == "valetudo_error"
            and item.get("value") == "empty"
            for vacuum_items in state.get("attributes", {})
            .get("items", {})
            .values()
            for item in vacuum_items.values()
        ),
    )
    set_fixture(
        api,
        ERROR_SENSOR,
        "No error",
        attributes={"subsystem": "none"},
    )
    wait_for_state(
        api,
        maintenance_attention["entity_id"],
        lambda state: state["state"] == "ok",
    )

    # The explicit resolve action dismisses one due occurrence without deleting
    # its recurring mission definition.
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": presence_wait["id"]})
    wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: presence_wait["id"] in state.get("attributes", {}).get("waiting_mission_ids", []),
    )
    api.call_service(
        DOMAIN,
        "resolve_pending",
        {"entry_id": entry_id, "mission_id": presence_wait["id"]},
    )
    resolved = wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state.get("attributes", {}).get("last_reason") == "pending_mission_resolved",
    )
    if presence_wait["id"] in resolved.get("attributes", {}).get("waiting_mission_ids", []):
        raise AssertionError(f"Resolved occurrence remained queued: {resolved}")

    # Re-arm the occurrence for the Planner-disable release regression below.
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": presence_wait["id"]})
    wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: presence_wait["id"] in state.get("attributes", {}).get("waiting_mission_ids", []),
    )
    reset_calls(api)

    planner_switch = next(
        state for state in api.get("/api/states")
        if state["entity_id"].startswith("switch.")
        and state["entity_id"].endswith("_planner_enabled")
    )
    api.call_service("switch", "turn_off", {"entity_id": planner_switch["entity_id"]})
    wait_for_state(api, planner_switch["entity_id"], lambda state: state["state"] == "off")
    api.call_service("input_number", "set_value", {"entity_id": "input_number.home_occupants", "value": 0})
    time.sleep(2)
    if fixture_calls(api):
        raise AssertionError("Disabled Planner released a waiting mission")
    disabled_status = planner_status(api, entry_id)
    if presence_wait["id"] not in disabled_status.get("attributes", {}).get("waiting_mission_ids", []):
        raise AssertionError(f"Disabled Planner lost its waiting mission: {disabled_status}")
    api.call_service("switch", "turn_on", {"entity_id": planner_switch["entity_id"]})
    wait_for_state(api, planner_switch["entity_id"], lambda state: state["state"] == "on")
    api.call_service("input_number", "set_value", {"entity_id": "input_number.home_occupants", "value": 1})
    api.call_service("input_number", "set_value", {"entity_id": "input_number.home_occupants", "value": 0})
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not fixture_calls(api):
        time.sleep(1)
    assert_command(fixture_calls(api), "clean_segments", segment_ids=["16", "17"])
    set_fixture(api, VACUUM_VALETUDO, "docked")
    wait_for_completed(api, entry_id)
    api.call_service(DOMAIN, "remove_mission", {"entry_id": entry_id, "mission_id": presence_wait["id"]})
    wait_for_mission_count(api, entry_id, 2)

    schedule_mission = {
        "id": "schedule_helper",
        "name": "Schedule helper clean",
        "vacuum_entity_id": VACUUM_CLOUD,
        "weekdays": [],
        "start_time": "09:00",
        "schedule_entity_id": "input_boolean.schedule_trigger",
        "profile": {"mode": "vacuum", "passes": 1},
    }
    add_mission(api, entry_id, schedule_mission)
    wait_for_mission_count(api, entry_id, 3)
    reset_calls(api)
    api.call_service("input_boolean", "turn_on", {"entity_id": "input_boolean.schedule_trigger"})
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not fixture_calls(api):
        time.sleep(1)
    assert_command(fixture_calls(api), "start")
    set_fixture(api, VACUUM_CLOUD, "docked")
    wait_for_completed(api, entry_id)
    api.call_service("input_boolean", "turn_off", {"entity_id": "input_boolean.schedule_trigger"})

    api.call_service("input_boolean", "turn_on", {"entity_id": "input_boolean.vacation_mode"})
    vacation_status = wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state["state"] == "vacation"
        and state.get("attributes", {}).get("vacation_active") is True,
    )
    if vacation_status.get("attributes", {}).get("vacation_entity_id") != "input_boolean.vacation_mode":
        raise AssertionError(f"Vacation source was not projected: {vacation_status}")
    # A native schedule transition must be completely inert while the global
    # vacation lock is active.
    reset_calls(api)
    api.call_service("input_boolean", "turn_on", {"entity_id": "input_boolean.schedule_trigger"})
    time.sleep(2)
    if fixture_calls(api):
        raise AssertionError("Vacation lock allowed a native schedule command")
    api.call_service("input_boolean", "turn_off", {"entity_id": "input_boolean.schedule_trigger"})
    set_notification_sentinel(api, "Silent vacation guard")
    reset_calls(api)
    api.call_service(
        DOMAIN,
        "run_next",
        {"entry_id": entry_id, "mission_id": valetudo["id"], "manual": True},
    )
    assert_last_reason(api, entry_id, "vacation_active")
    assert_notification_silent(api, "Silent vacation guard")
    if fixture_calls(api):
        raise AssertionError("Vacation guard allowed a device command")
    api.call_service("input_boolean", "turn_off", {"entity_id": "input_boolean.vacation_mode"})
    wait_for_state(
        api,
        planner_status(api, entry_id)["entity_id"],
        lambda state: state["state"] != "vacation"
        and state.get("attributes", {}).get("vacation_active") is False,
    )
    api.call_service(DOMAIN, "remove_mission", {"entry_id": entry_id, "mission_id": schedule_mission["id"]})
    wait_for_mission_count(api, entry_id, 2)

    api.call_service(DOMAIN, "remove_mission", {"entry_id": entry_id, "mission_id": cloud["id"]})
    wait_for_mission_count(api, entry_id, 1)
    api.call_service(DOMAIN, "postpone_next", {"entry_id": entry_id, "minutes": 37})
    api.call_service(DOMAIN, "skip_next", {"entry_id": entry_id})
    test_options_flow(api, entry_id)
    wait_for_mission_count(api, entry_id, 1)
    edit_mission_options_flow(api, entry_id, valetudo["id"])
    wait_for_mission_count(api, entry_id, 1)

    snapshot = {
        "phase": "bootstrap",
        "entry": wait_for_entry(api, entry_id),
        "planner_states": planner_states(api, entry_id),
        "fixture_calls": calls,
        "ha": api.get("/api/config"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "snapshot-bootstrap.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"token": token, "entry_id": entry_id}), encoding="utf-8")


def run_restart(api: HomeAssistantApi, saved: dict[str, Any], output_dir: Path) -> None:
    entry_id = str(saved["entry_id"])
    wait_for_entry(api, entry_id)
    wait_for_state(api, VACUUM_VALETUDO)
    wait_for_mission_count(api, entry_id, 1)
    next_states = [state for state in planner_states(api, entry_id) if "skip_armed" in state.get("attributes", {})]
    if len(next_states) != 1 or next_states[0]["attributes"].get("skip_armed") is not True:
        raise AssertionError(f"Skip-once state did not survive restart: {next_states}")
    reset_calls(api)
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id})
    assert_last_reason(api, entry_id, "skip_once_consumed")
    if fixture_calls(api):
        raise AssertionError("Consumed skip-once triggered device commands")
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": "valetudo_area"})
    calls = fixture_calls(api)
    assert_command(calls, "clean_segments", segment_ids=["16", "17"])
    if any(call.get("service") == "set_fan_speed" for call in calls):
        raise AssertionError(f"Valetudo fan profile was sent twice after restart: {calls}")

    maintenance = [state for state in api.get("/api/states") if state["entity_id"].startswith("sensor.") and "items" in state.get("attributes", {})]
    if len(maintenance) != 1 or maintenance[0]["state"] != "ok":
        raise AssertionError(f"Maintenance normalization failed: {maintenance}")
    snapshot = {
        "phase": "restart",
        "entry": wait_for_entry(api, entry_id),
        "planner_states": planner_states(api, entry_id),
        "fixture_calls": calls,
        "maintenance": maintenance,
        "ha": api.get("/api/config"),
    }
    (output_dir / "snapshot-restart.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18123")
    parser.add_argument("--phase", choices=("bootstrap", "restart"), required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    saved = json.loads(args.state_file.read_text(encoding="utf-8")) if args.phase == "restart" else {}
    api = HomeAssistantApi(args.base_url, saved.get("token"))
    wait_for_home_assistant(api)
    started = time.monotonic()
    try:
        if args.phase == "bootstrap":
            run_bootstrap(api, args.state_file, args.output_dir)
        else:
            run_restart(api, saved, args.output_dir)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        result = {"phase": args.phase, "passed": False, "error": f"{type(exc).__name__}: {exc}"}
        (args.output_dir / f"result-{args.phase}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(result["error"])
        return 1
    duration = time.monotonic() - started
    result = {"phase": args.phase, "passed": True, "duration_seconds": round(duration, 2)}
    (args.output_dir / f"result-{args.phase}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"PASS {args.phase} ({duration:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
