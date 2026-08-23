"""Pure normalization of Valetudo dock errors into maintenance attention."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DockErrorAttention:
    """One normalized, user-facing dock attention condition."""

    key: str
    label: str
    value: str


_DOCK_ERROR_RULES: tuple[tuple[str, DockErrorAttention], ...] = (
    (
        "clean water tank not installed",
        DockErrorAttention("freshwater", "Freshwater", "missing"),
    ),
    (
        "clean water tank empty",
        DockErrorAttention("freshwater", "Freshwater", "empty"),
    ),
    (
        "wastewater tank not installed or full",
        DockErrorAttention("wastewater", "Wastewater", "full_or_missing"),
    ),
    (
        "dust bag full or dust duct clogged",
        DockErrorAttention("dustbag", "Dustbag", "full_or_blocked"),
    ),
    (
        "cover open or missing dust bag",
        DockErrorAttention("dustbag", "Dustbag", "open_or_missing"),
    ),
    (
        "wastewater pipe clogged",
        DockErrorAttention("wastewater_pipe", "Wastewater pipe", "clogged"),
    ),
    (
        "wastewater pump damaged",
        DockErrorAttention("wastewater_pump", "Wastewater pump", "damaged"),
    ),
    (
        "mop dock tray not installed",
        DockErrorAttention("tray", "Dock tray", "missing"),
    ),
    (
        "mop dock tray full of water",
        DockErrorAttention("tray", "Dock tray", "full"),
    ),
)


def normalize_valetudo_dock_error(
    message: str | None, subsystem: str | None
) -> DockErrorAttention | None:
    """Return dock attention for a Valetudo error, or None when unrelated."""
    text = str(message or "").strip()
    normalized = text.casefold()
    if normalized in {"", "0", "none", "no error", "ok", "unknown", "unavailable"}:
        return None
    for pattern, attention in _DOCK_ERROR_RULES:
        if pattern in normalized:
            return attention
    if str(subsystem or "").casefold() == "dock" or "dock" in normalized:
        return DockErrorAttention("generic", "Dock", text)
    return None
