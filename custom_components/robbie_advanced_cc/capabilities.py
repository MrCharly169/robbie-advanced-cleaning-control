"""Discover robot-specific mission choices from Home Assistant entities."""
from __future__ import annotations

from collections.abc import Iterable
import json
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from .adapters import adapter_for


def _choice(value: Any, label: Any | None = None) -> dict[str, str]:
    raw = "" if value is None else str(value)
    return {"value": raw, "label": str(label or raw).replace("_", " ").strip()}


def _unique(choices: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in choices:
        value = str(item.get("value", "")).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(_choice(value, item.get("label")))
    return result


def _state_options(state: State | None) -> list[dict[str, str]]:
    if state is None:
        return []
    raw = state.attributes.get("options") or []
    if isinstance(raw, dict):
        return _unique(_choice(key, value) for key, value in raw.items())
    if isinstance(raw, (list, tuple, set)):
        return _unique(
            _choice(
                item.get("value", item.get("id")),
                item.get("label", item.get("name")),
            )
            if isinstance(item, dict)
            else _choice(item)
            for item in raw
        )
    return []


def _segments(value: Any) -> list[dict[str, str]]:
    """Normalize the segment shapes exposed by MQTT and cloud integrations."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return []
    if isinstance(value, dict):
        return _unique(
            _choice(
                item.get("id", item.get("segment_id", key)),
                item.get("name", item.get("label", key)),
            )
            if isinstance(item, dict)
            else _choice(key, item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return _unique(
            _choice(
                item.get("id", item.get("segment_id", item.get("value"))),
                item.get("name", item.get("label")),
            )
            if isinstance(item, dict)
            else _choice(item)
            for item in value
        )
    return []


def _registry_areas(hass: HomeAssistant, entity_id: str) -> list[dict[str, str]]:
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None:
        return []
    vacuum_options = dict(entry.options or {}).get("vacuum", {})
    if not isinstance(vacuum_options, dict):
        return []
    mapping = vacuum_options.get("area_mapping") or {}
    if isinstance(mapping, dict) and mapping:
        areas = ar.async_get(hass)
        return _unique(
            _choice(
                area_id,
                area.name if (area := areas.async_get_area(str(area_id))) else area_id,
            )
            for area_id in mapping
        )
    return _segments(vacuum_options.get("last_seen_segments"))


def _related_entities(hass: HomeAssistant, entity_id: str) -> list[str]:
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.device_id is None:
        return []
    return sorted(
        item.entity_id
        for item in registry.entities.values()
        if item.device_id == entry.device_id and item.entity_id != entity_id
    )


def _select_for(
    hass: HomeAssistant,
    entity_id: str,
    related: list[str],
    keywords: tuple[str, ...],
    exact_suffixes: tuple[str, ...],
) -> tuple[str | None, list[dict[str, str]]]:
    object_id = entity_id.split(".", 1)[1]
    for suffix in exact_suffixes:
        candidate = f"select.{object_id}_{suffix}"
        options = _state_options(hass.states.get(candidate))
        if options:
            return candidate, options
    for candidate in related:
        if not candidate.startswith("select."):
            continue
        registry_entry = er.async_get(hass).async_get(candidate)
        state = hass.states.get(candidate)
        haystack = " ".join(
            str(item or "")
            for item in (
                candidate,
                getattr(registry_entry, "translation_key", None),
                getattr(registry_entry, "original_name", None),
                state.attributes.get("friendly_name") if state else None,
            )
        ).lower()
        if any(keyword in haystack for keyword in keywords):
            options = _state_options(state)
            if options:
                return candidate, options
    return None, []


def discover_profile_options(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Return live, JSON-safe mission choices for one selected vacuum."""
    state = hass.states.get(entity_id)
    related = _related_entities(hass, entity_id)
    mode_entity, modes = _select_for(
        hass,
        entity_id,
        related,
        ("cleaning_mode", "clean mode", "mode"),
        ("mode", "cleaning_mode"),
    )
    fan_entity, fan_speeds = _select_for(
        hass, entity_id, related, ("fan", "suction", "power"), ("fan", "fan_speed")
    )
    water_entity, water_levels = _select_for(
        hass,
        entity_id,
        related,
        ("water", "mop intensity", "mop_intensity"),
        ("water", "water_level"),
    )
    passes_entity, passes = _select_for(
        hass,
        entity_id,
        related,
        ("passes", "repeat", "repetition"),
        ("passes", "repeat"),
    )

    if not modes:
        modes = [_choice("vacuum", "Vacuum")]
        if water_levels:
            modes.extend(
                (_choice("mop", "Mop"), _choice("vacuum_and_mop", "Vacuum + Mop"))
            )
    if not fan_speeds and state is not None:
        fan_speeds = _segments(state.attributes.get("fan_speed_list"))
    if not passes:
        passes = [_choice(value) for value in (1, 2, 3)]

    areas = _registry_areas(hass, entity_id)
    area_entity: str | None = entity_id if areas else None
    if not areas:
        object_id = entity_id.split(".", 1)[1]
        candidates = [
            f"sensor.{object_id}_map_segments",
            f"select.{object_id}_segments",
            f"select.{object_id}_rooms",
        ]
        candidates.extend(
            item
            for item in related
            if any(token in item.lower() for token in ("segment", "room", "area"))
        )
        for candidate in dict.fromkeys(candidates):
            candidate_state = hass.states.get(candidate)
            if candidate_state is None:
                continue
            areas = _state_options(candidate_state)
            if not areas:
                for key in ("segments", "map_segments", "rooms", "room_list"):
                    areas = _segments(candidate_state.attributes.get(key))
                    if areas:
                        break
            if areas:
                area_entity = candidate
                break

    sources = {
        "vacuum": entity_id,
        "areas": area_entity,
        "mode": mode_entity,
        "fan": fan_entity or (entity_id if fan_speeds else None),
        "water": water_entity,
        "passes": passes_entity,
    }
    current = {
        "mode": (
            hass.states.get(mode_entity).state
            if mode_entity and hass.states.get(mode_entity)
            else modes[0]["value"]
        ),
        "fan": (
            hass.states.get(fan_entity).state
            if fan_entity and hass.states.get(fan_entity)
            else (state.attributes.get("fan_speed") if state else None)
        ),
        "water": (
            hass.states.get(water_entity).state
            if water_entity and hass.states.get(water_entity)
            else None
        ),
        "passes": (
            hass.states.get(passes_entity).state
            if passes_entity and hass.states.get(passes_entity)
            else "1"
        ),
    }
    return {
        "entity_id": entity_id,
        "adapter": adapter_for(hass, entity_id).kind,
        "areas": areas,
        "modes": _unique(modes),
        "fan_speeds": _unique(fan_speeds),
        "water_levels": _unique(water_levels),
        "passes": _unique(passes),
        "current": current,
        "sources": {key: value for key, value in sources.items() if value},
    }


def profile_source_entities(hass: HomeAssistant, entity_id: str) -> set[str]:
    """Return entities whose state can change the available mission choices."""
    return set(discover_profile_options(hass, entity_id)["sources"].values())
