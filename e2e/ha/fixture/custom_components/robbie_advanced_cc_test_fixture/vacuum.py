"""Deterministic vacuum entities for generic and Valetudo adapter tests."""
from __future__ import annotations

from typing import Any

from homeassistant.components.vacuum import (
    Segment,
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
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
            FixtureVacuum(store, "Valetudo Fixture Robot", "valetudo_fixture_robot"),
            FixtureVacuum(store, "Cloud Fixture Robot", "cloud_fixture_robot"),
        ]
    )


class FixtureVacuum(StateVacuumEntity):
    _attr_should_poll = False
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.CLEAN_AREA
    )
    _attr_fan_speed_list = ["low", "medium", "high", "max"]

    def __init__(self, store: FixtureStore, name: str, object_id: str) -> None:
        self._store = store
        self._attr_name = name
        self._attr_unique_id = f"robbie_fixture_{object_id}"
        self._activity = VacuumActivity.DOCKED
        self._fan = "medium"
        self._available = True

    @property
    def activity(self) -> VacuumActivity:
        return self._activity

    @property
    def fan_speed(self) -> str:
        return self._fan

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
            self._activity = VacuumActivity(str(state))

    async def async_get_segments(self) -> list[Segment]:
        return [
            Segment("16", "Kitchen"),
            Segment("17", "Living room"),
            Segment("18", "Bathroom"),
        ]

    async def async_start(self) -> None:
        self._activity = VacuumActivity.CLEANING
        self._store.record("vacuum", "start", {"entity_id": self.entity_id})
        self.async_write_ha_state()

    async def async_pause(self) -> None:
        self._activity = VacuumActivity.PAUSED
        self._store.record("vacuum", "pause", {"entity_id": self.entity_id})
        self.async_write_ha_state()

    async def async_return_to_base(self) -> None:
        self._activity = VacuumActivity.RETURNING
        self._store.record(
            "vacuum", "return_to_base", {"entity_id": self.entity_id}
        )
        self.async_write_ha_state()

    async def async_set_fan_speed(self, fan_speed: str, **_kwargs: Any) -> None:
        self._fan = fan_speed
        self._store.record(
            "vacuum",
            "set_fan_speed",
            {"entity_id": self.entity_id, "fan_speed": fan_speed},
        )
        self.async_write_ha_state()

    async def async_clean_segments(
        self, segment_ids: list[str], **_kwargs: Any
    ) -> None:
        self._activity = VacuumActivity.CLEANING
        self._store.record(
            "vacuum",
            "clean_segments",
            {"entity_id": self.entity_id, "segment_ids": list(segment_ids)},
        )
        self.async_write_ha_state()
