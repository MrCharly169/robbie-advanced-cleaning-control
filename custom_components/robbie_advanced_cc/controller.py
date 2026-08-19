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
from .capabilities import profile_source_entities
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
    STATE_VACATION,
    STATE_WAITING,
    planner_presentation_state,
)
from .models import (
    CleaningMission,
    MissionDecision,
    PlannerContext,
    decide_mission,
    vacuum_runtime_transition,
)
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

    @property
    def vacation_active(self) -> bool:
        """Return whether the configured global vacation lock is active."""
        entity_id = self.config.get(CONF_VACATION_ENTITY)
        state = self.hass.states.get(entity_id) if entity_id else None
        return bool(state and state.state == "on")

    @property
    def effective_state(self) -> str:
        """Expose the canonical planner state without losing runtime details."""
        return planner_presentation_state(
            self.state,
            vacation_active=self.vacation_active,
            has_pending_missions=bool(self.pending_mission_ids),
            has_active_mission=bool(self.active_mission_id),
        )

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
            watched.extend(profile_source_entities(self.hass, entity_id))
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

    def next_occurrence_for(
        self, mission: CleaningMission, now: datetime | None = None
    ) -> datetime | None:
        """Return the next effective occurrence for one mission."""
        now = now or dt_util.now()
        postponed = self.postponed.get(mission.id)
        if postponed and postponed > now:
            return postponed
        return self._mission_occurrence(mission, now)

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
            postponed = self.postponed.get(mission.id)
            if (
                for_timer
                and mission.schedule_entity_id
                and not (postponed and postponed > now)
            ):
                continue
            occurrence = self.next_occurrence_for(mission, now)
            if occurrence:
                candidates.append((mission, occurrence))
        return min(candidates, key=lambda item: item[1]) if candidates else None

    def next_mission_for(self, vacuum_entity_id: str) -> tuple[CleaningMission, datetime] | None:
        return self.next_mission(vacuum_entity_id=vacuum_entity_id)

    def _schedule_next(self) -> None:
        if self._next_cancel:
            self._next_cancel()
            self._next_cancel = None
        if not self.enabled or self.vacation_active:
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
        # A timer may already be queued while vacation mode is switched on.
        # Do not announce or execute it; the vacation entity listener schedules
        # the next eligible occurrence after vacation mode is switched off.
        if self.vacation_active:
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
        adapter = adapter_for(self.hass, mission.vacuum_entity_id)
        mop_attached = getattr(adapter, "mop_attached", lambda: None)()
        people_home: bool | None = None
        if self.presence_entities:
            people_home = any(self._entity_is_home(entity_id) for entity_id in self.presence_entities)
        return PlannerContext(
            vacation=self.vacation_active,
            vacuum_available=adapter.available,
            mop_attached=mop_attached,
            people_home=people_home,
        )

    def conditions_for(self, mission: CleaningMission) -> list[dict[str, Any]]:
        """Return the user-facing condition trace for one mission."""
        context = self.context_for(mission)
        conditions = [
            {
                "key": "planner_enabled",
                "enabled": True,
                "passed": self.enabled and mission.enabled,
                "resolution": "block",
                "entities": [],
            },
            {
                "key": "vacuum_available",
                "enabled": True,
                "passed": context.vacuum_available,
                "resolution": mission.guards.vacuum_unavailable,
                "entities": [mission.vacuum_entity_id],
            },
            {
                "key": "vacation_inactive",
                "enabled": bool(self.config.get(CONF_VACATION_ENTITY))
                and mission.guards.vacation != "allow",
                "passed": not context.vacation,
                "resolution": mission.guards.vacation,
                "entities": [self.config[CONF_VACATION_ENTITY]]
                if self.config.get(CONF_VACATION_ENTITY)
                else [],
            },
            {
                "key": "mop_attached",
                "enabled": mission.profile.mode in {"mop", "vacuum_and_mop"},
                "passed": context.mop_attached is not False,
                "resolution": mission.guards.mop_missing,
                "entities": [],
            },
        ]
        if mission.guards.people_home != "allow":
            for entity_id in self.presence_entities:
                state = self.hass.states.get(entity_id)
                conditions.append(
                    {
                        "key": "home_empty",
                        "enabled": True,
                        "passed": not self._entity_is_home(entity_id),
                        "resolution": mission.guards.people_home,
                        "entities": [entity_id],
                        "entity_name": (
                            state.attributes.get("friendly_name", entity_id)
                            if state is not None
                            else entity_id
                        ),
                        "entity_state": state.state if state is not None else "unknown",
                    }
                )
        return conditions

    def _entity_is_home(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        # Fail safe: an unknown tracker is not proof that the home is empty.
        if state is None or state.state in {"unknown", "unavailable"}:
            return True
        domain = entity_id.split(".", 1)[0]
        if domain in {"zone", "sensor", "number", "input_number", "counter"}:
            try:
                return float(state.state) > 0
            except (TypeError, ValueError):
                # A non-numeric sensor value is treated like the normal HA
                # home/away vocabulary. Anything else remains fail-safe home.
                if state.state in {"not_home", "away", "off"}:
                    return False
                if state.state in {"home", "on"}:
                    return True
                return True
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
        if configured.startswith("script.") and self.hass.services.has_service(
            "script", configured.split(".", 1)[1]
        ):
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
            if route_entity_id := self.config.get(CONF_NOTIFICATION_ROUTE):
                route_state = self.hass.states.get(route_entity_id)
                if route_state and route_state.state not in {
                    "",
                    "unknown",
                    "unavailable",
                }:
                    data["route"] = route_state.state
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
        if entity_id == self.config.get(CONF_VACATION_ENTITY):
            self.last_reason = (
                "vacation_active" if self.vacation_active else "vacation_ended"
            )
            self._schedule_next()
            return
        if self.vacation_active and entity_id not in self.vacuums:
            # Native schedule and presence helper transitions are deliberately
            # inert during the global vacation lock. Robot state changes still
            # update the hidden runtime state so leaving vacation cannot reveal
            # a stale "running" value after the robot has docked.
            self._notify_listeners()
            return
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
            transition = vacuum_runtime_transition(
                self.state, new_state.state, self.active_mission_id
            )
            if transition:
                self.state, self.last_reason, clear_active = transition
                if clear_active:
                    self.active_mission_id = None
        self._notify_listeners()
        self._schedule_next()
