"""Vacuum adapter selection."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .base import VacuumAdapter
from .generic import GenericVacuumAdapter
from .valetudo import ValetudoVacuumAdapter


def adapter_for(hass: HomeAssistant, entity_id: str) -> VacuumAdapter:
    """Select the deepest safe adapter without requiring cloud credentials."""
    state = hass.states.get(entity_id)
    name = " ".join(
        (
            entity_id,
            str(state.attributes.get("friendly_name", "")) if state else "",
        )
    ).lower()
    if "valetudo" in name:
        return ValetudoVacuumAdapter(hass, entity_id)
    return GenericVacuumAdapter(hass, entity_id)


__all__ = ["VacuumAdapter", "adapter_for"]
