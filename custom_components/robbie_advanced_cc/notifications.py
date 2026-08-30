"""Deterministic, customer-facing mission announcement helpers."""
from __future__ import annotations

from datetime import datetime, time, timedelta
import re


DEFAULT_ANNOUNCEMENT_MINUTES = 24 * 60
DEFAULT_ANNOUNCEMENT_TIME = time(20, 0)


def mission_announcement_at(
    occurrence: datetime, lead_minutes: int
) -> datetime | None:
    """Return the notification time while preserving custom lead times.

    The historic default of 1440 minutes meant 24 hours before the run, which
    was much too early for morning missions. That default now deliberately
    means 20:00 on the previous calendar day. Explicit non-default values keep
    their exact minute-based behavior for backwards compatibility.
    """
    lead_minutes = max(0, int(lead_minutes))
    if lead_minutes == 0:
        return None
    if lead_minutes == DEFAULT_ANNOUNCEMENT_MINUTES:
        previous_day = occurrence.date() - timedelta(days=1)
        return datetime.combine(
            previous_day,
            DEFAULT_ANNOUNCEMENT_TIME,
            tzinfo=occurrence.tzinfo,
        )
    return occurrence - timedelta(minutes=lead_minutes)


def humanize_identifier(value: str) -> str:
    """Turn portable IDs and CamelCase labels into readable customer text."""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value or ""))
    text = re.sub(r"[_-]+", " ", text)
    return " ".join(text.split()).strip()


def default_robot_display_name(
    entity_id: str, friendly_name: str | None = None
) -> str:
    """Build a concise fallback name without overriding a configured alias."""
    source = friendly_name or str(entity_id or "").split(".", 1)[-1]
    robot = humanize_identifier(source) or "Robbie"
    for suffix in (" Robot", " Vacuum", " Saugroboter"):
        if robot.casefold().endswith(suffix.casefold()):
            robot = robot[: -len(suffix)].rstrip()
            break
    return robot or "Robbie"


def _mode_label(mode: str) -> str:
    labels = {
        "vacuum": "Vacuum only",
        "mop": "Mop only",
        "vacuum_and_mop": "Vacuum and mop",
    }
    return labels.get(
        str(mode),
        humanize_identifier(mode),
    )


def _mission_label(name: str, mode: str) -> str:
    """Replace common technical starter names without renaming the mission."""
    compact = re.sub(r"[^a-z0-9]", "", str(name).casefold())
    if compact in {
        "vaconly",
        "vacuumonly",
        "moponly",
        "vacmop",
        "vacuumandmop",
    }:
        return _mode_label(mode)
    return humanize_identifier(name) or _mode_label(mode)


def mission_announcement_copy(
    *,
    robot: str,
    mission_id: str,
    mission_name: str,
    mode: str,
    areas: list[str],
    occurrence: datetime,
) -> tuple[str, str]:
    """Build stable but varying English copy for one occurrence."""
    robot = str(robot or "").strip() or "Robbie"
    mission = _mission_label(mission_name, mode)
    readable_areas = [humanize_identifier(item) for item in areas if item]
    area = ", ".join(readable_areas) if readable_areas else "all areas"
    variant = (
        occurrence.date().toordinal() + sum(ord(char) for char in mission_id)
    ) % 4
    title = f"{robot}'s next mission will start"
    intros = (
        "Dust bunnies, enjoy your final free evening.",
        "The floor has booked a date with Robbie for tomorrow.",
        "A friendly warning: Robbie is going dust hunting tomorrow.",
        "Robbie is charging up tomorrow's cleaning superpowers.",
    )
    details = (
        f"Mission: {mission}. Start: tomorrow at {occurrence:%H:%M}. "
        f"Area: {area}."
    )
    return title, f"{intros[variant]} {details}"


def completion_notification_copy(
    *,
    robot: str,
    mission_name: str | None,
    mode: str | None,
    metrics: str = "",
    needs_aftercare: bool = False,
) -> tuple[str, str]:
    """Describe a completed run without exposing a technical mission label."""
    robot = str(robot or "").strip() or "Robbie"
    mission = (
        _mission_label(mission_name, mode or "vacuum")
        if mission_name
        else "Manual cleaning"
    )
    details = [f"Mission: {mission}."]
    if metrics:
        details.append(f"Result: {metrics}.")
    if needs_aftercare:
        details.append(
            "Home Assistant does not expose tank states; check the dock's "
            "freshwater and wastewater containers."
        )
    return f"🤖 {robot} · Cleaning completed", " ".join(details)


def error_notification_copy(*, robot: str, message: str) -> tuple[str, str]:
    """Describe one real robot error without leaking adapter terminology."""
    robot = str(robot or "").strip() or "Robbie"
    detail = humanize_identifier(message) or "Robot reported an error"
    return (
        f"🤖 {robot} · Cleaning error",
        f"{detail}. Check the robot and resume the mission when it is safe.",
    )
