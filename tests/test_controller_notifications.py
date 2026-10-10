"""Recipient fan-out without sending real notifications."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

try:
    from custom_components.robbie_advanced_cc.controller import CleaningPlanner
    from custom_components.robbie_advanced_cc.config_flow import _services_schema
except ModuleNotFoundError as exc:
    if not (exc.name or '').startswith('homeassistant'):
        raise
    raise unittest.SkipTest('Requires Home Assistant runtime') from exc


class RecipientTests(unittest.IsolatedAsyncioTestCase):
    async def deliver(self, selected, states):
        services = SimpleNamespace(has_service=lambda *_: True, async_call=AsyncMock())
        planner = SimpleNamespace(
            config={'notification_script': 'script.router', 'notification_route': selected},
            hass=SimpleNamespace(services=services, states=SimpleNamespace(
                get=lambda entity: SimpleNamespace(state=states[entity]) if entity in states else None)),
        )
        await CleaningPlanner._async_notify(planner, 'Completed', 'Clean', tag='test')
        return services.async_call.await_args_list

    async def test_multiple_recipients_and_duplicate_destination(self):
        calls = await self.deliver(['input_text.a', 'input_text.b', 'input_text.c'], {
            'input_text.a': 'notify.mobile_app_a', 'input_text.b': 'notify.mobile_app_b',
            'input_text.c': 'notify.mobile_app_a'})
        self.assertEqual([c.args[2]['route'] for c in calls], ['notify.mobile_app_a', 'notify.mobile_app_b'])
        self.assertEqual(calls[0].args[2]['payload'], calls[1].args[2]['payload'])

    async def test_legacy_single_recipient(self):
        calls = await self.deliver('input_text.a', {'input_text.a': 'notify.mobile_app_a'})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[2]['route'], 'notify.mobile_app_a')

    async def test_unavailable_recipient_does_not_redirect(self):
        calls = await self.deliver(['input_text.a', 'input_text.b'], {'input_text.b': 'unavailable'})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args[:2], ('persistent_notification', 'create'))

    async def test_one_unavailable_does_not_block_other(self):
        calls = await self.deliver(['input_text.a', 'input_text.b'], {'input_text.b': 'notify.mobile_app_b'})
        self.assertEqual([c.args[2]['route'] for c in calls], ['notify.mobile_app_b'])

    async def test_empty_selection_preserves_default_router(self):
        calls = await self.deliver([], {})
        self.assertEqual(calls[0].args[:2], ('script', 'router'))
        self.assertNotIn('route', calls[0].args[2])

    def test_native_selector_normalizes_existing_binding(self):
        schema = _services_schema({'notification_route': 'input_text.a'})
        marker = next(key for key in schema.schema if str(key) == 'notification_route')
        self.assertEqual(marker.description['suggested_value'], ['input_text.a'])
        selected = schema.schema[marker]
        self.assertEqual(selected(['input_text.a', 'input_text.b']), ['input_text.a', 'input_text.b'])
