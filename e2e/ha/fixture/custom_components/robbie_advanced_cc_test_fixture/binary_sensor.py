"""Valetudo-style attachment state."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .store import FixtureStore, get_store


async def async_setup_platform(
    hass: HomeAssistant,
    _config: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    _discovery_info: dict[str, Any] | None = None,
) -> None:
    async_add_entities([FixtureMopSensor(get_store(hass))])


class FixtureMopSensor(BinarySensorEntity):
    _attr_name = "Valetudo Fixture Robot Mop Attachment"
    _attr_unique_id = "robbie_fixture_valetudo_mop_attachment"
    _attr_should_poll = False

    def __init__(self, store: FixtureStore) -> None:
        self._store = store
        self._on = True
        self._available = True

    @property
    def is_on(self) -> bool:
        return self._on

    @property
    def available(self) -> bool:
        return self._available

    async def async_added_to_hass(self) -> None:
        self._store.register(self)

    def set_fixture_state(
        self, state: Any, _attributes: dict[str, Any], available: bool
    ) -> None:
        self._available = available
        self._on = state in {True, 1, "1", "on", "true", "True"}
