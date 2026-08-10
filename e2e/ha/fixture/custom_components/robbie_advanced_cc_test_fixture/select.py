"""Valetudo-style sibling selects."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .store import FixtureStore, get_store


async def async_setup_platform(
    hass: HomeAssistant,
    _config: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    _discovery_info: dict[str, Any] | None = None,
) -> None:
    store = get_store(hass)
    async_add_entities(
        [
            FixtureSelect(store, "Valetudo Fixture Robot Mode", "mode", ["vacuum", "mop", "vacuum_and_mop"], "vacuum"),
            FixtureSelect(store, "Valetudo Fixture Robot Fan", "fan", ["low", "medium", "high", "max"], "medium"),
            FixtureSelect(store, "Valetudo Fixture Robot Water", "water", ["low", "medium", "high"], "medium"),
        ]
    )


class FixtureSelect(SelectEntity):
    _attr_should_poll = False

    def __init__(
        self,
        store: FixtureStore,
        name: str,
        object_id: str,
        options: list[str],
        current: str,
    ) -> None:
        self._store = store
        self._attr_name = name
        self._attr_unique_id = f"robbie_fixture_valetudo_{object_id}"
        self._attr_options = options
        self._attr_current_option = current
        self._available = True

    @property
    def available(self) -> bool:
        return self._available

    async def async_added_to_hass(self) -> None:
        self._store.register(self)

    def set_fixture_state(
        self, state: Any, _attributes: dict[str, Any], available: bool
    ) -> None:
        self._available = available
        if state is not None:
            self._attr_current_option = str(state)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self._store.record(
            "select",
            "select_option",
            {"entity_id": self.entity_id, "option": option},
        )
        self.async_write_ha_state()
