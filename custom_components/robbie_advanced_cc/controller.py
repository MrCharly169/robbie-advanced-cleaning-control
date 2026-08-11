"""Persistent, explainable cleaning planner runtime."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .adapters import adapter_for
from .const import (
    CONF_DASHBOARD_PATH,
    CONF_NOTIFICATION_ROUTE,
    CONF_NOTIFICATION_SCRIPT,
    CONF_PRESENCE_ENTITIES,
    CONF_STARTER_MISSION,
    CONF_VACATION_ENTITY,
    CONF_VACUUMS,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_POSTPONE_MINUTES,
    STATE_ANNOUNCED,
    STATE_BLOCKED,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_IDLE,
    STATE_POSTPONED,
    STATE_PREPARING,
    STATE_RUNNING,
    STATE_SKIPPED,
    STATE_WAITING,
)
from .models import CleaningMission, MissionDecision, PlannerContext, decide_mission
from .storage import PlannerStore

_LOGGER = logging.getLogger(__name__)


class CleaningPlanner:
    """Own mission scheduling; adapters only own device dialects."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = PlannerStore(hass, entry.entry_id)
        self.missions: list[CleaningMission] = []
        self.state = STATE_IDLE
        self.last_reason = "not_evaluated"
        self.last_decision: MissionDecision | None = None
        self.active_mission_id: str | None = None
        self.skip_mission_id: str | None = None
        self.postponed: dict[str, datetime] = {}
        self.pending_mission_ids: list[str] = []
        self.enabled = True
        self._listeners: list[Callable[[], None]] = []
        self._next_cancel: Callable[[], None] | None = None
        self._state_unsubscribe: Callable[[], None] | None = None

    @property
    def config(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    @property
    def vacuums(self) -> list[str]:
        return list(self.config.get(CONF_VACUUMS, []))

    @property
    def presence_entities(self) -> list[str]:
        return list(self.config.get(CONF_PRESENCE_ENTITIES, []))

    async def async_setup(self) -> None:
        self.missions, persisted = await self.store.async_load()
        self.skip_mission_id = persisted.get("skip_mission_id")
        self.pending_mission_ids = [
            mission_id
            for mission_id in persisted.get("pending_mission_ids", [])
            if self.mission_by_id(str(mission_id)) is not None
        ]
        self.enabled = bool(persisted.get("enabled", True))
        for mission_id, value in dict(persisted.get("postponed") or {}).items():
            try:
                self.postponed[mission_id] = datetime.fromisoformat(value)
            except (TypeError, ValueError):
                continue
        if not persisted.get("starter_seeded"):
            starter = self.config.get(CONF_STARTER_MISSION)
            if isinstance(starter, dict):
                self.missions.append(CleaningMission.from_dict(starter))
            persisted["starter_seeded"] = True
            await self._async_persist(starter_seeded=True)
        self._refresh_state_listener()
        self._schedule_next()

    @callback
    def _refresh_state_listener(self) -> None:
        if self._state_unsubscribe:
            self._state_unsubscribe()
            self._state_unsubscribe = None
        watched = list(self.vacuums)
        for entity_id in self.vacuums:
            watched.extend(adapter_for(self.hass, entity_id).watched_entities)
        watched.extend(self.presence_entities)
        watched.extend(
            mission.schedule_entity_id
            for mission in self.missions
            if mission.schedule_entity_id
        )
        if vacation := self.config.get(CONF_VACATION_ENTITY):
            watched.append(vacation)
        if watched:
            self._state_unsubscribe = async_track_state_change_event(
                hass=self.hass,
                entity_ids=sorted(set(watched)),
                action=self._async_state_changed,
            )

    async def async_unload(self) -> None:
        if self._next_cancel:
            self._next_cancel()
            self._next_cancel = None
        if self._state_unsubscribe:
            self._state_unsubscribe()
            self._state_unsubscribe = None

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        @callback
        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def _mission_occurrence(self, mission: CleaningMission, now: datetime) -> datetime | None:
        if not mission.schedule_entity_id:
            return mission.next_after(now)
        schedule_state = self.hass.states.get(mission.schedule_entity_id)
        if schedule_state is None or schedule_state.state == "on":
            return None
        value = schedule_state.attributes.get("next_event")
        occurrence = dt_util.parse_datetime(str(value)) if value else None
        return dt_util.as_local(occurrence) if occurrence else None

    def next_mission(
        self,
        now: datetime | None = None,
        *,
        vacuum_entity_id: str | None = None,
        for_timer: bool = False,
    ) -> tuple[CleaningMission, datetime] | None:
        now = now or dt_util.now()
        candidates: list[tuple[CleaningMission, datetime]] = []
        for mission in self.missions:
            if vacuum_entity_id and mission.vacuum_entity_id != vacuum_entity_id:
                continue
            if mission.id in self.postponed and self.postponed[mission.id] > now:
                candidates.append((mission, self.postponed[mission.id]))
                continue
            if for_timer and mission.schedule_entity_id:
                continue
            occurrence = self._mission_occurrence(mission, now)
            if occurrence:
                candidates.append((mission, occurrence))
        return min(candidates, key=lambda item: item[1]) if candidates else None

    def next_mission_for(self, vacuum_entity_id: str) -> tuple[CleaningMission, datetime] | None:
        return self.next_mission(vacuum_entity_id=vacuum_entity_id)

    def _schedule_next(self) -> None:
        if self._next_cancel:
            self._next_cancel()
            self._next_cancel = None
        if not self.enabled:
            self._notify_listeners()
            return
        next_item = self.next_mission(for_timer=True)
        if not next_item:
            self._notify_listeners()
            return
        mission, occurrence = next_item
        announce_at = occurrence - timedelta(minutes=mission.announce_before_minutes)
        wake_at = announce_at if announce_at > dt_util.now() else occurrence

        async def scheduled_wakeup(now: datetime) -> None:
            await self._async_scheduled_wakeup(mission.id, occurrence, now)

        self._next_cancel = async_track_point_in_time(
            self.hass,
            scheduled_wakeup,
            wake_at,
        )
        self._notify_listeners()

    async def _async_scheduled_wakeup(
        self, mission_id: str, occurrence: datetime, now: datetime
    ) -> None:
        mission = self.mission_by_id(mission_id)
        if mission is None:
            self._schedule_next()
            return
        if now < occurrence:
            self.state = STATE_ANNOUNCED
            self.last_reason = "mission_announced"
            await self._async_notify(
                f"{mission.name}: next cleaning",
                f"Scheduled for {occurrence.strftime('%A %H:%M')}. Skip or postpone it from the Cleaning Control card.",
                tag=f"racc_announce_{mission.id}",
            )
            self._schedule_next()
            return
        await self.async_run(mission.id)

    def mission_by_id(self, mission_id: str) -> CleaningMission | None:
        return next((mission for mission in self.missions if mission.id == mission_id), None)

    def context_for(self, mission: CleaningMission) -> PlannerContext:
        vacation_entity = self.config.get(CONF_VACATION_ENTITY)
        vacation_state = self.hass.states.get(vacation_entity) if vacation_entity else None
        vacation = bool(
            vacation_state and vacation_state.state == "on"
        )
        adapter = adapter_for(self.hass, mission.vacuum_entity_id)
        mop_attached = getattr(adapter, "mop_attached", lambda: None)()
        people_home: bool | None = None
        if self.presence_entities:
            people_home = any(self._entity_is_home(entity_id) for entity_id in self.presence_entities)
        return PlannerContext(
            vacation=vacation,
            vacuum_available=adapter.available,
            mop_attached=mop_attached,
            people_home=people_home,
        )

    def _entity_is_home(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        # Fail safe: an unknown tracker is not proof that the home is empty.
        if state is None or state.state in {"unknown", "unavailable"}:
            return True
        domain = entity_id.split(".", 1)[0]
        if domain == "zone":
            try:
                return float(state.state) > 0
            except ValueError:
                return False
        if domain in {"binary_sensor", "input_boolean"}:
            return state.state == "on"
        return state.state == "home"

    async def async_run(self, mission_id: str | None = None) -> MissionDecision:
        if mission_id is None:
            next_item = self.next_mission()
            if next_item is None:
                decision = MissionDecision(False, "blocked", "no_mission")
                self._set_decision(decision, STATE_BLOCKED)
                return decision
            mission = next_item[0]
        else:
            mission = self.mission_by_id(mission_id)
            if mission is None:
                decision = MissionDecision(False, "blocked", "mission_not_found")
                self._set_decision(decision, STATE_BLOCKED)
                return decision

        if self.skip_mission_id == mission.id:
            self.skip_mission_id = None
            decision = MissionDecision(False, "skip", "skip_once_consumed")
            self._set_decision(decision, STATE_SKIPPED)
            await self._async_persist()
            self._schedule_next()
            return decision

        decision = decide_mission(mission, self.context_for(mission))
        self.last_decision = decision
        self.last_reason = decision.reason
        if not decision.allowed:
            if decision.resolution == "wait":
                if mission.id not in self.pending_mission_ids:
                    self.pending_mission_ids.append(mission.id)
                self.state = STATE_WAITING
                await self._async_persist()
                self._schedule_next()
            elif decision.resolution == "postpone":
                self.state = STATE_BLOCKED
                await self.async_postpone(mission.id, DEFAULT_POSTPONE_MINUTES)
            else:
                self.state = STATE_SKIPPED if decision.resolution == "skip" else STATE_BLOCKED
                await self._async_persist()
                self._schedule_next()
            await self._async_notify(
                f"{mission.name}: not started",
                f"Planner decision: {decision.reason} ({decision.resolution}).",
                tag=f"racc_blocked_{mission.id}",
            )
            return decision

        if mission.id in self.pending_mission_ids:
            self.pending_mission_ids.remove(mission.id)
        self.state = STATE_PREPARING
        self.active_mission_id = mission.id
        self._notify_listeners()
        try:
            await adapter_for(self.hass, mission.vacuum_entity_id).async_start_mission(mission)
        except Exception:
            _LOGGER.exception("Could not start cleaning mission %s", mission.id)
            self.state = STATE_FAILED
            self.last_reason = "adapter_start_failed"
            self._notify_listeners()
            raise
        self.state = STATE_RUNNING
        self.postponed.pop(mission.id, None)
        await self._async_persist()
        self._schedule_next()
        return decision

    async def async_skip_next(self) -> bool:
        next_item = self.next_mission()
        if next_item is None:
            return False
        self.skip_mission_id = next_item[0].id
        self.last_reason = "skip_once_armed"
        await self._async_persist()
        self._notify_listeners()
        return True

    async def async_postpone(
        self, mission_id: str | None = None, minutes: int = DEFAULT_POSTPONE_MINUTES
    ) -> bool:
        mission = self.mission_by_id(mission_id) if mission_id else None
        if mission is None:
            next_item = self.next_mission()
            mission = next_item[0] if next_item else None
        if mission is None:
            return False
        self.postponed[mission.id] = dt_util.now() + timedelta(minutes=max(1, minutes))
        self.state = STATE_POSTPONED
        self.last_reason = "mission_postponed"
        await self._async_persist()
        self._schedule_next()
        return True

    async def async_add_mission(self, raw: dict[str, Any]) -> CleaningMission:
        mission = CleaningMission.from_dict(raw)
        if mission.vacuum_entity_id not in self.vacuums:
            raise ValueError("Mission vacuum is not managed by this config entry")
        self.missions = [item for item in self.missions if item.id != mission.id]
        self.missions.append(mission)
        await self._async_persist()
        self._refresh_state_listener()
        self._schedule_next()
        return mission

    async def async_remove_mission(self, mission_id: str) -> bool:
        before = len(self.missions)
        self.missions = [mission for mission in self.missions if mission.id != mission_id]
        changed = len(self.missions) != before
        if changed:
            self.postponed.pop(mission_id, None)
            if mission_id in self.pending_mission_ids:
                self.pending_mission_ids.remove(mission_id)
            if self.skip_mission_id == mission_id:
                self.skip_mission_id = None
            await self._async_persist()
            self._refresh_state_listener()
            self._schedule_next()
        return changed

    async def async_set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        await self._async_persist()
        self._schedule_next()

    def _set_decision(self, decision: MissionDecision, state: str) -> None:
        self.last_decision = decision
        self.last_reason = decision.reason
        self.state = state
        self._notify_listeners()

    async def _async_persist(self, *, starter_seeded: bool = True) -> None:
        await self.store.async_save(
            self.missions,
            {
                "skip_mission_id": self.skip_mission_id,
                "enabled": self.enabled,
                "pending_mission_ids": self.pending_mission_ids,
                "starter_seeded": starter_seeded,
                "postponed": {
                    mission_id: value.isoformat()
                    for mission_id, value in self.postponed.items()
                },
            },
        )

    async def _async_notify(self, title: str, message: str, *, tag: str) -> None:
        configured = str(self.config.get(CONF_NOTIFICATION_SCRIPT) or "")
        dashboard_path = str(
            self.config.get(CONF_DASHBOARD_PATH) or DEFAULT_DASHBOARD_PATH
        )
        if configured.startswith("script."):
            data: dict[str, Any] = {
                "payload": {
                    "title": title,
                    "message": message,
                    "data": {
                        "tag": tag,
                        "url": dashboard_path,
                        "clickAction": dashboard_path,
                    },
                }
            }
            if route := self.config.get(CONF_NOTIFICATION_ROUTE):
                data["route"] = route
            await self.hass.services.async_call(
                "script", configured.split(".", 1)[1], data, blocking=False
            )
            return
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {"title": title, "message": message, "notification_id": tag},
            blocking=False,
        )

    async def _async_state_changed(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        schedule_missions = [
            mission
            for mission in self.missions
            if mission.schedule_entity_id == entity_id
        ]
        if new_state is not None and new_state.state == "on" and getattr(old_state, "state", None) != "on":
            for mission in schedule_missions:
                await self.async_run(mission.id)
            return
        if entity_id in self.presence_entities and self.pending_mission_ids:
            if not any(self._entity_is_home(item) for item in self.presence_entities):
                for mission_id in tuple(self.pending_mission_ids):
                    await self.async_run(mission_id)
                return
        if entity_id in self.vacuums and new_state is not None:
            if new_state.state == "cleaning":
                self.state = STATE_RUNNING
                self.last_reason = "vacuum_cleaning"
            elif new_state.state == "docked" and self.state == STATE_RUNNING:
                self.state = STATE_COMPLETED
                self.last_reason = "mission_completed"
                self.active_mission_id = None
            elif new_state.state in {"error", "unavailable"}:
                self.state = STATE_FAILED
                self.last_reason = f"vacuum_{new_state.state}"
        self._notify_listeners()
        self._schedule_next()
