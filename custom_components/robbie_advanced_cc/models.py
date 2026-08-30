"""Vendor-neutral mission and decision models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta
from typing import Any
from uuid import uuid4


WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True, slots=True)
class CleaningProfile:
    """Portable settings which adapters translate to device controls."""

    mode: str = "vacuum"
    fan: str | None = None
    water: str | None = None
    passes: int = 1

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "CleaningProfile":
        raw = raw or {}
        return cls(
            mode=str(raw.get("mode") or "vacuum"),
            fan=str(raw["fan"]) if raw.get("fan") is not None else None,
            water=str(raw["water"]) if raw.get("water") is not None else None,
            passes=max(1, min(3, int(raw.get("passes", 1)))),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MissionGuards:
    """Deterministic context rules evaluated before a mission runs."""

    vacation: str = "block"
    mop_missing: str = "block"
    vacuum_unavailable: str = "postpone"
    people_home: str = "allow"

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "MissionGuards":
        raw = raw or {}
        return cls(
            vacation=str(raw.get("vacation") or "block"),
            mop_missing=str(raw.get("mop_missing") or "block"),
            vacuum_unavailable=str(raw.get("vacuum_unavailable") or "postpone"),
            people_home=str(raw.get("people_home") or "allow"),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CleaningMission:
    """One repeatable cleaning mission."""

    id: str
    name: str
    vacuum_entity_id: str
    weekdays: tuple[str, ...]
    start_time: str
    schedule_entity_id: str | None = None
    areas: tuple[str, ...] = ()
    profile: CleaningProfile = field(default_factory=CleaningProfile)
    guards: MissionGuards = field(default_factory=MissionGuards)
    announce_before_minutes: int = 1440
    enabled: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CleaningMission":
        weekdays = tuple(
            day for day in raw.get("weekdays", ()) if str(day) in WEEKDAYS
        )
        start_time = str(raw.get("start_time") or "09:00")
        time.fromisoformat(start_time)
        return cls(
            id=str(raw.get("id") or uuid4().hex),
            name=str(raw.get("name") or "Cleaning mission"),
            vacuum_entity_id=str(raw["vacuum_entity_id"]),
            weekdays=weekdays,
            start_time=start_time,
            schedule_entity_id=(
                str(raw["schedule_entity_id"])
                if raw.get("schedule_entity_id")
                else None
            ),
            areas=tuple(str(area) for area in raw.get("areas", ())),
            profile=CleaningProfile.from_dict(raw.get("profile")),
            guards=MissionGuards.from_dict(raw.get("guards")),
            announce_before_minutes=max(
                0, int(raw.get("announce_before_minutes", 1440))
            ),
            enabled=bool(raw.get("enabled", True)),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def next_after(self, now: datetime) -> datetime | None:
        """Return the next local occurrence strictly after now."""
        if not self.enabled or not self.weekdays:
            return None
        planned_time = time.fromisoformat(self.start_time)
        for offset in range(8):
            day = now.date() + timedelta(days=offset)
            if WEEKDAYS[day.weekday()] not in self.weekdays:
                continue
            candidate = datetime.combine(day, planned_time, tzinfo=now.tzinfo)
            if candidate > now:
                return candidate
        return None

    def matches_internal_occurrence(self, occurrence: datetime) -> bool:
        """Return whether an existing weekly occurrence survives an edit."""
        if not self.enabled or self.schedule_entity_id or not self.weekdays:
            return False
        planned_time = time.fromisoformat(self.start_time)
        return (
            WEEKDAYS[occurrence.weekday()] in self.weekdays
            and occurrence.hour == planned_time.hour
            and occurrence.minute == planned_time.minute
        )


@dataclass(frozen=True, slots=True)
class PlannerContext:
    """Normalized context consumed by the decision resolver."""

    planner_enabled: bool = True
    vacation: bool = False
    vacuum_available: bool = True
    mop_attached: bool | None = None
    people_home: bool | None = None


@dataclass(frozen=True, slots=True)
class MissionDecision:
    """Explainable decision with a stable machine-readable reason."""

    allowed: bool
    resolution: str
    reason: str


def vacuum_runtime_transition(
    planner_state: str,
    vacuum_state: str,
    active_mission_id: str | None,
    *,
    dock_visit_resumable: bool = False,
) -> tuple[str, str, bool] | None:
    """Return a planner transition for a robot state change.

    A robot can briefly be unavailable during startup, MQTT reconnects, or a
    Home Assistant reload.  That is not a failed cleaning run unless a mission
    is actually being prepared or executed.
    """
    if vacuum_state == "cleaning":
        return ("running", "vacuum_cleaning", False)
    if (
        vacuum_state == "docked"
        and planner_state in {"running", "dock_service"}
        and dock_visit_resumable
    ):
        return ("dock_service", "dock_visit_resumable", False)
    if vacuum_state == "docked" and planner_state in {"running", "dock_service"}:
        return ("completed", "mission_completed", True)
    if vacuum_state in {"error", "unavailable"} and active_mission_id is not None:
        return ("failed", f"vacuum_{vacuum_state}", False)
    return None


def decide_mission(
    mission: CleaningMission, context: PlannerContext
) -> MissionDecision:
    """Resolve mission guards in one fixed, testable priority order."""
    if not context.planner_enabled:
        return MissionDecision(False, "blocked", "planner_disabled")
    if not mission.enabled:
        return MissionDecision(False, "blocked", "mission_disabled")
    if context.vacation and mission.guards.vacation != "allow":
        return MissionDecision(False, mission.guards.vacation, "vacation_active")
    if not context.vacuum_available:
        return MissionDecision(
            False,
            mission.guards.vacuum_unavailable,
            "vacuum_unavailable",
        )
    if mission.profile.mode in {"mop", "vacuum_and_mop"} and context.mop_attached is False:
        return MissionDecision(False, mission.guards.mop_missing, "mop_missing")
    if context.people_home and mission.guards.people_home != "allow":
        return MissionDecision(False, mission.guards.people_home, "people_home")
    return MissionDecision(True, "run", "ready")


def needs_dock_aftercare_reminder(
    profile_mode: str | None, maintenance_keys: set[str]
) -> bool:
    """Return whether a mop run needs a truthful tank-check fallback."""
    if profile_mode not in {"mop", "vacuum_and_mop"}:
        return False
    return not {"dock_freshwater", "dock_wastewater"}.issubset(
        maintenance_keys
    )
