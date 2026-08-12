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


def fixture_calls(api: HomeAssistantApi) -> list[dict[str, Any]]:
    return list(wait_for_state(api, CALL_SENSOR).get("attributes", {}).get("calls") or [])


def reset_calls(api: HomeAssistantApi) -> None:
    api.call_service(FIXTURE, "reset_calls", {})
    wait_for_state(api, CALL_SENSOR, lambda state: state["state"] == "0")


def set_fixture(api: HomeAssistantApi, entity_id: str, state: Any, *, available: bool = True) -> None:
    api.call_service(
        FIXTURE,
        "set_state",
        {"entity_id": entity_id, "state": state, "available": available},
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
        {
            "name": "Robbie E2E Planner",
            "vacuums": [VACUUM_VALETUDO, VACUUM_CLOUD],
            "presence_entities": ["input_number.home_occupants"],
            "vacation_entity": "input_boolean.vacation_mode",
            "notification_route": "input_text.notify_route_test",
            "dashboard_path": "/lovelace/cleaning",
        },
    )
    if result.get("type") != "create_entry":
        raise AssertionError(f"Options flow failed: {result}")
    wait_for_entry(api, entry_id)


def assert_command(calls: list[dict[str, Any]], service: str, **data: Any) -> None:
    for call in calls:
        if call.get("service") == service and all(call.get("data", {}).get(key) == value for key, value in data.items()):
            return
    raise AssertionError(f"Missing fixture command {service} {data}: {calls}")


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
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": valetudo["id"]})
    calls = fixture_calls(api)
    assert_command(calls, "select_option", option="vacuum_and_mop")
    assert_command(calls, "select_option", option="high")
    assert_command(calls, "clean_segments", segment_ids=["16", "17"])
    if any(call.get("service") == "set_fan_speed" for call in calls):
        raise AssertionError(f"Valetudo fan profile was sent twice: {calls}")
    set_fixture(api, VACUUM_VALETUDO, "docked")

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

    set_fixture(api, MOP_SENSOR, "off")
    reset_calls(api)
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": valetudo["id"]})
    assert_last_reason(api, entry_id, "mop_missing")
    if fixture_calls(api):
        raise AssertionError("Mop guard allowed a device command")
    set_fixture(api, MOP_SENSOR, "on")

    presence_wait = {
        **valetudo,
        "id": "presence_wait",
        "name": "Wait until empty",
        "profile": {"mode": "vacuum", "passes": 1},
        "guards": {"people_home": "wait"},
    }
    add_mission(api, entry_id, presence_wait)
    wait_for_mission_count(api, entry_id, 3)
    api.call_service("input_number", "set_value", {"entity_id": "input_number.home_occupants", "value": 2})
    reset_calls(api)
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": presence_wait["id"]})
    assert_last_reason(api, entry_id, "people_home")
    waiting = planner_status(api, entry_id)
    if presence_wait["id"] not in waiting.get("attributes", {}).get("waiting_mission_ids", []):
        raise AssertionError(f"Presence wait was not armed: {waiting}")
    api.call_service("input_number", "set_value", {"entity_id": "input_number.home_occupants", "value": 0})
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not fixture_calls(api):
        time.sleep(1)
    assert_command(fixture_calls(api), "clean_segments", segment_ids=["16", "17"])
    set_fixture(api, VACUUM_VALETUDO, "docked")
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
    api.call_service("input_boolean", "turn_off", {"entity_id": "input_boolean.schedule_trigger"})
    api.call_service(DOMAIN, "remove_mission", {"entry_id": entry_id, "mission_id": schedule_mission["id"]})
    wait_for_mission_count(api, entry_id, 2)

    api.call_service("input_boolean", "turn_on", {"entity_id": "input_boolean.vacation_mode"})
    reset_calls(api)
    api.call_service(DOMAIN, "run_next", {"entry_id": entry_id, "mission_id": valetudo["id"]})
    assert_last_reason(api, entry_id, "vacation_active")
    if fixture_calls(api):
        raise AssertionError("Vacation guard allowed a device command")
    api.call_service("input_boolean", "turn_off", {"entity_id": "input_boolean.vacation_mode"})

    api.call_service(DOMAIN, "remove_mission", {"entry_id": entry_id, "mission_id": cloud["id"]})
    wait_for_mission_count(api, entry_id, 1)
    api.call_service(DOMAIN, "postpone_next", {"entry_id": entry_id, "minutes": 37})
    api.call_service(DOMAIN, "skip_next", {"entry_id": entry_id})
    test_options_flow(api, entry_id)
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
