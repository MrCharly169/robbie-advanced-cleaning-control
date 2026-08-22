"""Constants for Robbie Advanced Cleaning Control."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "robbie_advanced_cc"
NAME: Final = "Robbie Advanced Cleaning Control"
PLATFORMS: Final = ("binary_sensor", "button", "sensor", "switch")

CONF_VACUUMS: Final = "vacuums"
CONF_PRESENCE_ENTITIES: Final = "presence_entities"
CONF_VACATION_ENTITY: Final = "vacation_entity"
CONF_NOTIFICATION_SCRIPT: Final = "notification_script"
CONF_NOTIFICATION_ROUTE: Final = "notification_route"
CONF_TODO_ENTITY: Final = "todo_entity"
CONF_DASHBOARD_PATH: Final = "dashboard_path"
CONF_STARTER_MISSION: Final = "starter_mission"
CONF_FRONTEND_ONBOARDING_SENT: Final = "frontend_onboarding_sent"

DEFAULT_NAME: Final = "Cleaning Planner"
DEFAULT_DASHBOARD_PATH: Final = "/lovelace/cleaning"
DEFAULT_POSTPONE_MINUTES: Final = 60
DEFAULT_ANNOUNCEMENT_MINUTES: Final = 24 * 60
CARD_RESOURCE_URL: Final = f"/{DOMAIN}/cleaning-control.js"
CARD_TYPE: Final = "custom:robbie-advanced-cleaning-card"
BADGE_TYPE: Final = "custom:robbie-vacuum-badge"
STORAGE_VERSION: Final = 1

SERVICE_ADD_MISSION: Final = "add_mission"
SERVICE_REMOVE_MISSION: Final = "remove_mission"
SERVICE_RUN_NEXT: Final = "run_next"
SERVICE_SKIP_NEXT: Final = "skip_next"
SERVICE_POSTPONE_NEXT: Final = "postpone_next"

STATE_IDLE: Final = "idle"
STATE_ANNOUNCED: Final = "announced"
STATE_PREPARING: Final = "preparing"
STATE_RUNNING: Final = "running"
STATE_DOCK_SERVICE: Final = "dock_service"
STATE_COMPLETED: Final = "completed"
STATE_SKIPPED: Final = "skipped"
STATE_POSTPONED: Final = "postponed"
STATE_WAITING: Final = "waiting"
STATE_VACATION: Final = "vacation"
STATE_BLOCKED: Final = "blocked"
STATE_FAILED: Final = "failed"

PLANNER_STATUS_OPTIONS: Final = [
    STATE_IDLE,
    STATE_ANNOUNCED,
    STATE_PREPARING,
    STATE_RUNNING,
    STATE_DOCK_SERVICE,
    STATE_COMPLETED,
    STATE_SKIPPED,
    STATE_POSTPONED,
    STATE_WAITING,
    STATE_VACATION,
    STATE_BLOCKED,
    STATE_FAILED,
]


def planner_presentation_state(
    runtime_state: str,
    *,
    has_robot_error: bool,
    vacation_active: bool,
    has_pending_missions: bool,
    has_active_mission: bool,
) -> str:
    """Return the canonical status exposed to dashboards and automations."""
    if has_robot_error:
        return STATE_FAILED
    if vacation_active:
        return STATE_VACATION
    if has_active_mission or runtime_state in {STATE_BLOCKED, STATE_FAILED}:
        return runtime_state
    if has_pending_missions:
        return STATE_WAITING
    return runtime_state
