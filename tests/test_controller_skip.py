"""Execute the real controller against deterministic HA adapters and events.

Run in the HA image to include Home Assistant; the lightweight host suite skips
this module when HA is not installed. No real devices or credentials are used.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

try:
    from custom_components.robbie_advanced_cc import controller as runtime
except ModuleNotFoundError as exc:
    if not (exc.name or "").startswith("homeassistant"):
        raise
    raise unittest.SkipTest("Run controller tests in the Home Assistant image") from exc


class SkipTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.robot = SimpleNamespace(state="docked", attributes={})
        self.hass = SimpleNamespace(states=SimpleNamespace(get=lambda _: self.robot))
        self.entry = SimpleNamespace(entry_id="test", data={"vacuums": ["vacuum.test"]}, options={})
        self.adapter = SimpleNamespace(
            async_start_mission=AsyncMock(), async_return_to_base=AsyncMock(),
            available=True, error=None, dock_visit_resumable=False,
        )
        self.store_patch = patch.object(runtime, "PlannerStore")
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)
        self.adapter_patch = patch.object(runtime, "adapter_for", return_value=self.adapter)
        self.adapter_patch.start()
        self.addCleanup(self.adapter_patch.stop)
        self.planner = runtime.CleaningPlanner(self.hass, self.entry)
        self.planner.store.async_save = AsyncMock()
        for name in ("_schedule_next", "_schedule_completion_release", "_schedule_dock_completion_check", "_cancel_dock_completion_check", "_refresh_state_listener", "_schedule_robot_error_refresh"):
            setattr(self.planner, name, Mock())
        self.planner._async_notify_completed = AsyncMock()
        self.mission = runtime.CleaningMission.from_dict({
            "id": "today", "name": "Morning", "vacuum_entity_id": "vacuum.test",
            "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_time": "06:00", "profile": {"mode": "vacuum"},
        })
        self.planner.missions = [self.mission]

    def pending(self):
        self.planner.pending_mission_ids = ["today"]
        self.planner.pending_occurrences = {"today": datetime(2026, 9, 22, 6, tzinfo=timezone.utc)}
        self.planner.state = runtime.STATE_WAITING

    async def event(self, state, entity="vacuum.test"):
        self.robot.state = state
        await self.planner._async_state_changed(SimpleNamespace(data={
            "entity_id": entity, "new_state": self.robot, "old_state": None,
        }))

    async def test_waiting_today_removed_without_arming_tomorrow(self):
        self.pending()
        self.planner.next_mission = Mock(side_effect=AssertionError("Do not select a future run"))
        self.assertTrue(await self.planner.async_skip_next())
        self.assertEqual(self.planner.pending_mission_ids, [])
        self.assertEqual(self.planner.pending_occurrences, {})
        self.assertIsNone(self.planner.skip_mission_id)
        self.assertEqual(self.planner.state, runtime.STATE_SKIPPED)
        self.adapter.async_return_to_base.assert_not_awaited()
        await self.planner.async_run("today")
        self.adapter.async_start_mission.assert_awaited_once()

    async def test_active_returns_and_completes_as_skipped_only_when_docked(self):
        await self.planner.async_run("today")
        self.pending()  # Active run still takes precedence over waiting work.
        self.assertTrue(await self.planner.async_skip_next())
        self.assertTrue(await self.planner.async_skip_next())
        self.adapter.async_return_to_base.assert_awaited_once()
        self.assertEqual(self.planner.active_mission_id, "today")
        self.assertIsNone(self.planner.skip_mission_id)
        await self.event("returning")
        await self.planner._async_confirm_docked_completion("vacuum.test")
        self.assertIsNotNone(self.planner.active_vacuum_entity_id)
        self.adapter.dock_visit_resumable = True
        await self.event("docked")
        await self.planner._async_confirm_docked_completion("vacuum.other")
        self.assertIsNotNone(self.planner.active_vacuum_entity_id)
        await self.planner._async_confirm_docked_completion("vacuum.test")
        self.assertEqual(self.planner.state, runtime.STATE_SKIPPED)
        self.assertIsNone(self.planner.active_vacuum_entity_id)
        self.assertFalse(self.planner._skipping_active)
        self.planner._async_notify_completed.assert_not_awaited()
        await self.planner.async_run("today")
        self.assertEqual(self.adapter.async_start_mission.await_count, 2)

    async def test_skip_during_start_orders_return_after_start(self):
        started, release = asyncio.Event(), asyncio.Event()
        order = []
        async def start(_mission):
            started.set()
            await release.wait()
            order.append("start")
        async def home():
            order.append("return")
        self.adapter.async_start_mission.side_effect = start
        self.adapter.async_return_to_base.side_effect = home
        task = asyncio.create_task(self.planner.async_run("today"))
        await started.wait()
        skipping = asyncio.create_task(self.planner.async_skip_next())
        await asyncio.sleep(0)
        self.assertFalse(skipping.done())
        release.set()
        await asyncio.gather(task, skipping)
        self.assertEqual(order, ["start", "return"])
        self.assertTrue(self.planner._skipping_active)
        self.assertEqual(self.planner.state, runtime.STATE_DOCK_SERVICE)

    async def test_return_failure_preserves_current_run_and_can_retry(self):
        await self.planner.async_run("today")
        self.adapter.async_return_to_base.side_effect = RuntimeError("offline")
        with self.assertRaises(RuntimeError):
            await self.planner.async_skip_next()
        self.assertEqual(self.planner.active_mission_id, "today")
        self.assertFalse(self.planner._skipping_active)
        self.assertIsNone(self.planner.skip_mission_id)
        self.adapter.async_return_to_base.side_effect = None
        await self.planner.async_skip_next()
        self.assertTrue(self.planner._skipping_active)

    async def test_future_skip_consumption_cleans_legacy_pending(self):
        await self.planner.async_skip_next()
        self.assertEqual(self.planner.skip_mission_id, "today")
        self.pending()
        decision = await self.planner.async_run("today")
        self.assertEqual(decision.resolution, "skip")
        self.assertFalse(self.planner.pending_mission_ids)
        self.assertFalse(self.planner.pending_occurrences)
        self.adapter.async_start_mission.assert_not_awaited()

    async def test_restart_keeps_cancelled_run_until_docking(self):
        await self.planner.async_run("today")
        await self.planner.async_skip_next()
        saved = self.planner.store.async_save.call_args.args[1]
        self.planner.store.async_load = AsyncMock(return_value=([self.mission], saved))
        self.planner._async_refresh_maintenance_notifications = AsyncMock()
        self.planner._async_refresh_robot_error_notifications = AsyncMock()
        self.planner._skipping_active = False
        self.planner.active_mission_id = None
        self.planner.active_vacuum_entity_id = None
        await self.planner.async_setup()
        self.assertTrue(self.planner._skipping_active)
        self.assertEqual(self.planner.active_mission_id, "today")
        await self.planner._async_confirm_docked_completion("vacuum.test")
        self.assertEqual(self.planner.state, runtime.STATE_SKIPPED)
        self.planner._async_notify_completed.assert_not_awaited()

    async def test_start_cannot_overwrite_returning_identity(self):
        await self.planner.async_run("today")
        await self.planner.async_skip_next()
        decision = await self.planner.async_run("today")
        self.assertFalse(decision.allowed)
        self.assertEqual(self.planner.active_mission_id, "today")
        self.adapter.async_start_mission.assert_awaited_once()

    async def test_two_pending_only_consume_one(self):
        self.pending()
        self.planner.pending_mission_ids.append("later")
        await self.planner.async_skip_next()
        self.assertEqual(self.planner.pending_mission_ids, ["later"])

    async def test_no_mission_is_noop(self):
        self.planner.missions = []
        self.assertFalse(await self.planner.async_skip_next())
        self.adapter.async_return_to_base.assert_not_awaited()

    async def test_stale_presence_queue_cannot_restart_skipped_waiting_run(self):
        self.pending()
        await self.planner._run_lock.acquire()
        skipping = asyncio.create_task(self.planner.async_skip_next())
        await asyncio.sleep(0)
        pending_start = asyncio.create_task(self.planner._async_run_pending("today"))
        await asyncio.sleep(0)
        self.planner._run_lock.release()
        await asyncio.gather(skipping, pending_start)
        self.adapter.async_start_mission.assert_not_awaited()
        self.assertFalse(self.planner.pending_mission_ids)

    async def test_failed_start_does_not_transfer_skip_to_tomorrow(self):
        started, release = asyncio.Event(), asyncio.Event()
        async def start(_mission):
            started.set()
            await release.wait()
            raise RuntimeError("start failed")
        self.adapter.async_start_mission.side_effect = start
        task = asyncio.create_task(self.planner.async_run("today"))
        await started.wait()
        skipping = asyncio.create_task(self.planner.async_skip_next())
        await asyncio.sleep(0)
        release.set()
        with self.assertLogs(runtime.__name__, level="ERROR"):
            result = await asyncio.gather(task, skipping, return_exceptions=True)
        self.assertIsInstance(result[0], RuntimeError)
        self.assertFalse(result[1])
        self.assertIsNone(self.planner.skip_mission_id)

    async def test_normal_resumable_dock_still_does_not_complete(self):
        await self.planner.async_run("today")
        self.adapter.dock_visit_resumable = True
        await self.planner._async_confirm_docked_completion("vacuum.test")
        self.assertEqual(self.planner.state, runtime.STATE_DOCK_SERVICE)
        self.assertEqual(self.planner.active_mission_id, "today")
        self.planner._async_notify_completed.assert_not_awaited()

    async def test_paused_and_external_active_runs_can_be_skipped(self):
        self.planner.active_vacuum_entity_id = "vacuum.test"
        self.planner.active_run_external = True
        self.robot.state = "paused"
        await self.planner.async_skip_next()
        self.adapter.async_return_to_base.assert_awaited_once()
        await self.event("docked")
        await self.planner._async_confirm_docked_completion("vacuum.test")
        self.assertEqual(self.planner.state, runtime.STATE_SKIPPED)
        self.assertFalse(self.planner.active_run_external)
