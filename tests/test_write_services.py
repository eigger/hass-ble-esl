"""Tests for the write / write_guarded service handlers in __init__.py.

These exercise the closures registered by async_setup_entry through a small
fake hass, with the backend's write_image and the renderer stubbed out.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from PIL import Image
import pytest

import custom_components.ble_esl as integration
from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.const import (
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_RETRY_COUNT,
    DOMAIN,
)
from custom_components.ble_esl.esl_ble import WriteResult
from homeassistant.exceptions import HomeAssistantError


class FakeCoordinator:
    """Minimal DataUpdateCoordinator stand-in."""

    def __init__(self, *args, **kwargs):
        self.data = None

    def async_set_updated_data(self, data):
        self.data = data


def _make_entry(entry_id: str, address: str, options: dict | None = None):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.unique_id = address
    entry.data = {"protocol": "wolink", "model": "290"}
    entry.options = options or {}
    return entry


class Harness:
    """Fake hass plus the two service handlers registered for it."""

    def __init__(self, monkeypatch, loop, options=None):
        self.loop = loop
        self.hass = MagicMock()
        self.hass.data = {}
        self.hass.loop = loop
        self.hass.config_entries.async_forward_entry_setups = AsyncMock()
        self.hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        self.hass.async_create_background_task = (
            lambda coro, name=None: loop.create_task(coro)
        )
        self.services: dict[str, object] = {}
        self.hass.services.async_register = (
            lambda domain, name, handler: self.services.__setitem__(name, handler)
        )
        self.entries: dict[str, MagicMock] = {}
        self.hass.config_entries.async_get_entry = (
            lambda entry_id: self.entries[entry_id]
        )

        # Rendering: return a different image per payload so image bytes differ.
        def fake_render(entry_id, preset, service, hass):
            img = Image.new("RGB", (preset.width, preset.height), "white")
            payload = service.data.get("payload", "")
            img.putpixel((0, 0), (len(str(payload)) % 256, 0, 0))
            return img

        monkeypatch.setattr(integration, "render_image", fake_render)
        monkeypatch.setattr(integration, "DataUpdateCoordinator", FakeCoordinator)
        monkeypatch.setattr(
            integration, "BleEslPassiveBluetoothProcessorCoordinator", MagicMock()
        )
        monkeypatch.setattr(integration, "async_last_service_info", lambda *a, **k: None)
        monkeypatch.setattr(integration, "sleep", AsyncMock())  # retry backoff

        self.ble_device = MagicMock()
        self.ble_device.address = "AA:BB:CC:DD:EE:FF"
        self.available = True
        monkeypatch.setattr(
            integration,
            "async_ble_device_from_address",
            lambda hass, address: self.ble_device if self.available else None,
        )

        self.write_image = AsyncMock(return_value=WriteResult(success=True))
        monkeypatch.setattr(esl_ble.get("wolink"), "write_image", self.write_image)
        self.options = options or {}

    async def add_entry(self, entry_id: str, address: str):
        entry = _make_entry(entry_id, address, self.options)
        self.entries[entry_id] = entry
        assert await integration.async_setup_entry(self.hass, entry)
        # Device id is what services target; make it predictable.
        self.hass.data[DOMAIN][entry_id]["device_id"] = f"dev-{entry_id}"
        return entry

    def entry_data(self, entry_id: str) -> dict:
        return self.hass.data[DOMAIN][entry_id]

    def call(self, name: str, device_id, **data):
        service = MagicMock()
        service.data = {"device_id": device_id, **data}
        return self.services[name](service)


@pytest.fixture
def harness_factory(monkeypatch):
    def factory(loop, options=None):
        return Harness(monkeypatch, loop, options)

    return factory


def test_write_without_ble_handle_counts_as_failed_attempts(harness_factory):
    """A missing BLE device handle is a failed attempt: retried, counted, raised."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 3})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        h.available = False

        with pytest.raises(HomeAssistantError, match="unavailable"):
            await h.call("write", "dev-e1", payload="x")

        assert h.write_image.await_count == 0
        assert h.entry_data("e1")["failure_coordinator"].data == 1
        assert h.entry_data("e1")["last_failure_coordinator"].data is not None

    asyncio.run(_test())


def test_ble_handle_resolved_per_attempt(harness_factory):
    """Handle is looked up at write time, not at service call time."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 2})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        h.available = False
        original = h.write_image.side_effect

        async def become_available(*args, **kwargs):
            return WriteResult(success=True)

        # First attempt has no handle; make it appear before the retry.
        real_sleep = integration.sleep

        async def sleep_then_available(*args, **kwargs):
            h.available = True
            await real_sleep(*args, **kwargs)

        integration.sleep = sleep_then_available
        h.write_image.side_effect = become_available
        try:
            await h.call("write", "dev-e1", payload="x")
        finally:
            integration.sleep = real_sleep
            h.write_image.side_effect = original

        assert h.write_image.await_count == 1
        assert h.entry_data("e1")["failure_coordinator"].data == 0

    asyncio.run(_test())


def test_multi_device_call_continues_after_failure(harness_factory):
    """One unreachable tag must not stop the remaining targets from being written."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 1})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:01")
        await h.add_entry("e2", "AA:BB:CC:DD:EE:02")

        async def fail_first(ble_device, preset, image, **kwargs):
            # Both entries share the fake handle; distinguish by call order.
            if h.write_image.await_count == 1:
                return WriteResult(success=False, error="boom")
            return WriteResult(success=True)

        h.write_image.side_effect = fail_first

        with pytest.raises(HomeAssistantError, match="boom"):
            await h.call("write", ["dev-e1", "unknown-device", "dev-e2"], payload="x")

        assert h.write_image.await_count == 2
        assert h.entry_data("e1")["failure_coordinator"].data == 1
        assert h.entry_data("e2")["image_coordinator"].data is not None

    asyncio.run(_test())


def test_duplicate_guard_ignores_failed_write(harness_factory):
    """Only a successful write may suppress a later identical write_guarded call."""

    async def _test():
        h = harness_factory(
            asyncio.get_running_loop(),
            {CONF_RETRY_COUNT: 1, CONF_PREVENT_DUPLICATE_SEND: True},
        )
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        h.write_image.return_value = WriteResult(success=False, error="boom")
        with pytest.raises(HomeAssistantError):
            await h.call("write_guarded", "dev-e1", payload="same")
        assert h.entry_data("e1")["last_image_data"] is None

        # Same payload again: must be sent, not skipped as a duplicate.
        h.write_image.return_value = WriteResult(success=True)
        await h.call("write_guarded", "dev-e1", payload="same")
        assert h.write_image.await_count == 2
        assert h.entry_data("e1")["last_image_data"] is not None

        # Now it is a genuine duplicate and is skipped.
        await h.call("write_guarded", "dev-e1", payload="same")
        assert h.write_image.await_count == 2

    asyncio.run(_test())


def test_debounce_is_trailing_edge_with_last_payload(harness_factory):
    """Repeated calls restart the timer; one write fires with the last payload."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        await h.call("write_guarded", "dev-e1", payload="first", debounce_override_ms=100)
        await asyncio.sleep(0.07)
        await h.call("write_guarded", "dev-e1", payload="second!", debounce_override_ms=100)

        # 100 ms after the *first* call nothing has been written yet.
        await asyncio.sleep(0.06)
        assert h.write_image.await_count == 0

        # 100 ms after the *second* call a single write with its payload fires.
        await asyncio.sleep(0.08)
        assert h.write_image.await_count == 1
        sent = h.write_image.await_args.args[2]
        assert sent.getpixel((0, 0))[0] == len("second!")
        assert h.entry_data("e1")["pending_write_handle"] is None

    asyncio.run(_test())


def test_immediate_write_cancels_pending_debounced_write(harness_factory):
    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        await h.call("write_guarded", "dev-e1", payload="queued", debounce_override_ms=100)
        assert h.entry_data("e1")["pending_write_handle"] is not None

        await h.call("write", "dev-e1", payload="now")
        assert h.entry_data("e1")["pending_write_handle"] is None
        await asyncio.sleep(0.15)
        assert h.write_image.await_count == 1

    asyncio.run(_test())
