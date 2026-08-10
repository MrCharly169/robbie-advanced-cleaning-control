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


@dataclass(frozen=True, slots=True)
class PlannerContext:
    """Normalized context consumed by the decision resolver."""

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


def decide_mission(
    mission: CleaningMission, context: PlannerContext
) -> MissionDecision:
    """Resolve mission guards in one fixed, testable priority order."""
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
