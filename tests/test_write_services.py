"""Tests for the write / write_guarded service handlers in __init__.py.

These exercise the closures registered by async_setup_entry through a small
fake hass, with the backend's write_image and the renderer stubbed out.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from PIL import Image
import pytest

import custom_components.ble_esl as integration
from custom_components.ble_esl import esl_ble
from custom_components.ble_esl import services as svc
from custom_components.ble_esl.const import (
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_RETRY_COUNT,
    DATA_LOCK,
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
        self._domain_ready = False
        self.hass.config_entries.async_forward_entry_setups = AsyncMock()
        # Real executor future: the encode is awaited by the backend after
        # connecting and again on retries, and cancelled if never awaited.
        self.hass.async_add_executor_job = (
            lambda func, *args: loop.run_in_executor(None, func, *args)
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
        self.hass.config_entries.async_loaded_entries = (
            lambda domain: list(self.entries.values())
        )

        # Rendering: return a different image per payload so image bytes differ.
        def fake_render(hass, preset, payload, *, rotate=0, background="white"):
            img = Image.new("RGB", (preset.width, preset.height), "white")
            img.putpixel((0, 0), (len(str(payload)) % 256, 0, 0))
            return img

        monkeypatch.setattr(svc, "render_image", fake_render)
        monkeypatch.setattr(integration, "DataUpdateCoordinator", FakeCoordinator)
        monkeypatch.setattr(
            integration, "BleEslPassiveBluetoothProcessorCoordinator", MagicMock()
        )
        monkeypatch.setattr(integration, "async_last_service_info", lambda *a, **k: None)
        monkeypatch.setattr(svc, "async_last_service_info", lambda *a, **k: None)
        monkeypatch.setattr(svc, "sleep", AsyncMock())  # retry backoff

        # homeassistant.helpers.event is mocked; emulate async_call_later's
        # contract (action receives a datetime, returns a cancel callable).
        def fake_call_later(hass, delay, action):
            handle = loop.call_later(delay, action, None)
            return handle.cancel

        monkeypatch.setattr(svc, "async_call_later", fake_call_later)

        # homeassistant.helpers.service is mocked; emulate the real helper's
        # contract for the device_id form (it also handles entity/area/label):
        # return the config entry ids of the referenced devices.
        async def fake_extract(*args):
            service = args[-1]
            device_ids = service.data.get("device_id", [])
            if isinstance(device_ids, str):
                device_ids = [device_ids]
            return {
                entry_id
                for entry_id, entry in self.entries.items()
                if entry.runtime_data.device_id in device_ids
            }

        self.extract = AsyncMock(side_effect=fake_extract)
        monkeypatch.setattr(svc, "async_extract_config_entry_ids", self.extract)

        self.ble_device = MagicMock()
        self.ble_device.address = "AA:BB:CC:DD:EE:FF"
        self.available = True
        monkeypatch.setattr(
            svc,
            "async_ble_device_from_address",
            lambda hass, address: self.ble_device if self.available else None,
        )

        # Encoding is the identity here so tests can inspect the image that
        # reached the backend via the awaited future's result().
        # The small sleep keeps the encode future *pending* when the write
        # starts, as on a loaded CI runner, so the await-after-connect path
        # is what the tests exercise rather than an already-finished future.
        def identity_prepare(preset, image, address):
            time.sleep(0.02)
            return image

        backend = esl_ble.get("wolink")
        monkeypatch.setattr(backend, "prepare_image", identity_prepare)
        # Like a real backend, the mock awaits the encode future (after
        # "connecting") before writing; tests steer the outcome with
        # `write_result` or a `write_hook(ble_device, preset, image, **kw)`.
        self.write_result = WriteResult(success=True)
        self.write_hook = None

        async def fake_write_prepared(ble_device, preset, prepared, **kwargs):
            image = await prepared
            if self.write_hook is not None:
                return await self.write_hook(ble_device, preset, image, **kwargs)
            return self.write_result

        self.write_prepared = AsyncMock(side_effect=fake_write_prepared)
        monkeypatch.setattr(backend, "write_prepared", self.write_prepared)
        self.options = options or {}

    async def add_entry(self, entry_id: str, address: str):
        if not self._domain_ready:
            # Lock and services are domain-level, registered once.
            assert await integration.async_setup(self.hass, {})
            self._domain_ready = True
        entry = _make_entry(entry_id, address, self.options)
        self.entries[entry_id] = entry
        assert await integration.async_setup_entry(self.hass, entry)
        # Device id is what services target; make it predictable.
        entry.runtime_data.device_id = f"dev-{entry_id}"
        return entry

    def entry_data(self, entry_id: str):
        return self.entries[entry_id].runtime_data

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

        assert h.write_prepared.await_count == 0
        assert h.entry_data("e1").failure_coordinator.data == 1
        assert h.entry_data("e1").last_failure_coordinator.data is not None

    asyncio.run(_test())


def test_ble_handle_resolved_per_attempt(harness_factory):
    """Handle is looked up at write time, not at service call time."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 2})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        h.available = False
        async def become_available(*args, **kwargs):
            return WriteResult(success=True)

        # First attempt has no handle; make it appear before the retry.
        real_sleep = svc.sleep

        async def sleep_then_available(*args, **kwargs):
            h.available = True
            await real_sleep(*args, **kwargs)

        svc.sleep = sleep_then_available
        h.write_hook = become_available
        try:
            await h.call("write", "dev-e1", payload="x")
        finally:
            svc.sleep = real_sleep

        assert h.write_prepared.await_count == 1
        assert h.entry_data("e1").failure_coordinator.data == 0

    asyncio.run(_test())


def test_multi_device_call_continues_after_failure(harness_factory):
    """One unreachable tag must not stop the remaining targets from being written."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 1})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:01")
        await h.add_entry("e2", "AA:BB:CC:DD:EE:02")

        async def fail_first(ble_device, preset, image, **kwargs):
            # Handlers run concurrently, so which tag reaches the lock first
            # is not fixed; fail whichever writes first.
            if h.write_prepared.await_count == 1:
                return WriteResult(success=False, error="boom")
            return WriteResult(success=True)

        h.write_hook = fail_first

        with pytest.raises(HomeAssistantError, match="boom"):
            await h.call("write", ["dev-e1", "dev-e2"], payload="x")

        assert h.write_prepared.await_count == 2  # both attempted
        failures = [h.entry_data(e).failure_coordinator.data for e in ("e1", "e2")]
        written = [h.entry_data(e).image_coordinator.data is not None for e in ("e1", "e2")]
        assert sorted(failures) == [0, 1]
        assert sorted(written) == [False, True]

    asyncio.run(_test())


def test_duplicate_guard_ignores_failed_write(harness_factory):
    """Only a successful write may suppress a later identical write_guarded call."""

    async def _test():
        h = harness_factory(
            asyncio.get_running_loop(),
            {CONF_RETRY_COUNT: 1, CONF_PREVENT_DUPLICATE_SEND: True},
        )
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        h.write_result = WriteResult(success=False, error="boom")
        with pytest.raises(HomeAssistantError):
            await h.call("write_guarded", "dev-e1", payload="same")
        assert h.entry_data("e1").last_image_data is None

        # Same payload again: must be sent, not skipped as a duplicate.
        h.write_result = WriteResult(success=True)
        await h.call("write_guarded", "dev-e1", payload="same")
        assert h.write_prepared.await_count == 2
        assert h.entry_data("e1").last_image_data is not None

        # Now it is a genuine duplicate and is skipped.
        await h.call("write_guarded", "dev-e1", payload="same")
        assert h.write_prepared.await_count == 2

    asyncio.run(_test())


def test_debounce_is_trailing_edge_with_last_payload(harness_factory):
    """Repeated calls restart the timer; one write fires with the last payload."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        await h.call("write_guarded", "dev-e1", payload="first", debounce_override_ms=300)
        await asyncio.sleep(0.15)
        await h.call("write_guarded", "dev-e1", payload="second!", debounce_override_ms=300)

        # 300 ms after the *first* call nothing has been written yet.
        await asyncio.sleep(0.20)
        assert h.write_prepared.await_count == 0

        # 300 ms after the *second* call a single write with its payload fires.
        await asyncio.sleep(0.25)
        assert h.write_prepared.await_count == 1
        sent = h.write_prepared.await_args.args[2].result()
        assert sent.getpixel((0, 0))[0] == len("second!")
        assert h.entry_data("e1").pending_write_cancel is None

    asyncio.run(_test())


def test_immediate_write_cancels_pending_debounced_write(harness_factory):
    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        await h.call("write_guarded", "dev-e1", payload="queued", debounce_override_ms=300)
        assert h.entry_data("e1").pending_write_cancel is not None

        await h.call("write", "dev-e1", payload="now")
        assert h.entry_data("e1").pending_write_cancel is None
        await asyncio.sleep(0.4)
        assert h.write_prepared.await_count == 1

    asyncio.run(_test())


def test_fired_debounced_write_dropped_when_superseded(harness_factory):
    """A debounced write whose timer fired but is still queued on the BLE lock
    is dropped once an immediate write cancels it (generation token)."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        # Hold the BLE lock so a fired debounced write has to queue behind it.
        lock = h.hass.data[DATA_LOCK]
        await lock.acquire()

        await h.call("write_guarded", "dev-e1", payload="stale", debounce_override_ms=50)
        await asyncio.sleep(0.1)  # timer fires; task now waits on the lock
        assert h.entry_data("e1").pending_write_cancel is None
        assert h.write_prepared.await_count == 0

        generation_before = h.entry_data("e1").write_generation
        immediate = asyncio.get_running_loop().create_task(
            h.call("write", "dev-e1", payload="fresh!!")
        )
        # Release the lock only once the immediate write has cancelled the
        # pending one (bumped the generation) and is itself queued on the lock.
        while h.entry_data("e1").write_generation == generation_before:
            await asyncio.sleep(0)
        lock.release()
        await immediate
        await asyncio.sleep(0.05)

        assert h.write_prepared.await_count == 1
        sent = h.write_prepared.await_args.args[2].result()
        assert sent.getpixel((0, 0))[0] == len("fresh!!")

    asyncio.run(_test())


def test_duplicate_guard_rechecked_under_lock(harness_factory):
    """Same payload arriving while an identical write is in flight is skipped
    once the first one succeeds, instead of being sent a second time."""

    async def _test():
        h = harness_factory(
            asyncio.get_running_loop(), {CONF_PREVENT_DUPLICATE_SEND: True}
        )
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        first_started = asyncio.Event()
        release_first = asyncio.Event()

        async def slow_write(*args, **kwargs):
            first_started.set()
            await release_first.wait()
            return WriteResult(success=True)

        h.write_hook = slow_write

        first = asyncio.get_running_loop().create_task(
            h.call("write_guarded", "dev-e1", payload="same")
        )
        await first_started.wait()
        # Pre-lock check passes (nothing written yet); this call queues on the lock.
        second = asyncio.get_running_loop().create_task(
            h.call("write_guarded", "dev-e1", payload="same")
        )
        await asyncio.sleep(0)
        release_first.set()
        await first
        await second

        assert h.write_prepared.await_count == 1

    asyncio.run(_test())


def test_write_guarded_without_ble_handle_fails_like_write(harness_factory):
    """write_guarded no longer silently skips an invisible tag."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 2})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        h.available = False

        with pytest.raises(HomeAssistantError, match="unavailable"):
            await h.call("write_guarded", "dev-e1", payload="x")

        assert h.write_prepared.await_count == 0
        assert h.entry_data("e1").failure_coordinator.data == 1
        # Preview was still rendered.
        assert h.entry_data("e1").preview_coordinator.data is not None

    asyncio.run(_test())


def test_dry_run_is_preview_only(harness_factory):
    """dry_run renders the preview but does not count as a sent image."""

    async def _test():
        h = harness_factory(
            asyncio.get_running_loop(), {CONF_PREVENT_DUPLICATE_SEND: True}
        )
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")

        await h.call("write_guarded", "dev-e1", payload="p", dry_run=True)
        assert h.write_prepared.await_count == 0
        assert h.entry_data("e1").preview_coordinator.data is not None
        assert h.entry_data("e1").last_image_data is None

        # The real write of the same payload must not be treated as a duplicate.
        await h.call("write_guarded", "dev-e1", payload="p")
        assert h.write_prepared.await_count == 1

    asyncio.run(_test())


def test_target_resolution_uses_ha_helper_and_filters_to_loaded_entries(harness_factory):
    """Targets come from async_extract_config_entry_ids (entity/device/area/label),
    limited to entries this integration has loaded; nothing matching is an error."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:01")
        await h.add_entry("e2", "AA:BB:CC:DD:EE:02")

        # The helper may return entries of other integrations sharing a device.
        h.extract.side_effect = None
        h.extract.return_value = {"e2", "other-integration-entry", "e1"}
        await h.call("write", "ignored-by-fake", payload="x")
        assert h.write_prepared.await_count == 2

        h.extract.return_value = {"other-integration-entry"}
        with pytest.raises(HomeAssistantError, match="No loaded BLE ESL device matches"):
            await h.call("write", "ignored-by-fake", payload="x")
        assert h.write_prepared.await_count == 2

    asyncio.run(_test())


def test_extract_helper_called_without_hass(harness_factory):
    """HA 2025.12+ signature: the service call alone (hass would log a warning)."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:01")
        await h.call("write", "dev-e1", payload="x")
        args = h.extract.await_args.args
        assert len(args) == 1 and args[0] is not h.hass

    asyncio.run(_test())


def test_encode_once_per_write_reused_across_retries(harness_factory, monkeypatch):
    """prepare_image runs once; every attempt receives the same future."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 3})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        prepare = MagicMock(side_effect=lambda preset, image, address: image)
        monkeypatch.setattr(esl_ble.get("wolink"), "prepare_image", prepare)
        h.write_result = WriteResult(success=False, error="boom")

        with pytest.raises(HomeAssistantError, match="boom"):
            await h.call("write", "dev-e1", payload="x")

        assert h.write_prepared.await_count == 3
        assert prepare.call_count == 1
        futures = {id(c.args[2]) for c in h.write_prepared.await_args_list}
        assert len(futures) == 1

    asyncio.run(_test())


def test_encode_starts_before_waiting_for_ble_lock(harness_factory, monkeypatch):
    """A tag queued behind the BLE lock encodes while it waits."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        encoded = asyncio.Event()

        def prepare(preset, image, address):
            h.loop.call_soon_threadsafe(encoded.set)
            return image

        monkeypatch.setattr(esl_ble.get("wolink"), "prepare_image", prepare)

        lock = h.hass.data[DATA_LOCK]
        await lock.acquire()
        write = asyncio.get_running_loop().create_task(h.call("write", "dev-e1", payload="x"))
        await asyncio.wait_for(encoded.wait(), 2)  # encoded while the lock is still held
        assert h.write_prepared.await_count == 0
        lock.release()
        await write
        assert h.write_prepared.await_count == 1

    asyncio.run(_test())


def test_skipped_write_discards_failed_encode_quietly(harness_factory, monkeypatch):
    """If the write is skipped (write lock) the unawaited encode future is
    consumed, so a failing encode never logs 'exception was never retrieved'."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        h.entry_data("e1").write_lock = True

        def broken_prepare(preset, image, address):
            raise RuntimeError("encode failed")

        monkeypatch.setattr(esl_ble.get("wolink"), "prepare_image", broken_prepare)
        unhandled = []
        asyncio.get_running_loop().set_exception_handler(lambda loop, ctx: unhandled.append(ctx))

        await h.call("write", "dev-e1", payload="x")  # skipped, no error raised
        await asyncio.sleep(0.05)
        import gc

        gc.collect()
        assert h.write_prepared.await_count == 0
        assert unhandled == []

    asyncio.run(_test())


def test_multi_target_call_pipelines_encodes_and_writes_in_order(harness_factory, monkeypatch):
    """Both tags of one call encode up front; writes are serialized by the lock in order."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        await h.add_entry("e1", "AA:BB:CC:DD:EE:01")
        await h.add_entry("e2", "AA:BB:CC:DD:EE:02")
        encoded: list[str] = []
        first_write_started = asyncio.Event()
        release_first = asyncio.Event()

        def prepare(preset, image, address):
            h.loop.call_soon_threadsafe(encoded.append, address)
            return image

        async def slow_write(ble_device, preset, image, **kwargs):
            if not first_write_started.is_set():
                first_write_started.set()
                await release_first.wait()
            return WriteResult(success=True)

        monkeypatch.setattr(esl_ble.get("wolink"), "prepare_image", prepare)
        h.write_hook = slow_write

        call = asyncio.get_running_loop().create_task(
            h.call("write", ["dev-e1", "dev-e2"], payload="x")
        )
        await first_write_started.wait()
        await asyncio.sleep(0.05)
        # Second tag has already encoded while the first is still writing.
        assert sorted(encoded) == ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"]
        assert h.write_prepared.await_count == 1
        release_first.set()
        await call

        assert h.write_prepared.await_count == 2
        assert h.entry_data("e1").image_coordinator.data is not None
        assert h.entry_data("e2").image_coordinator.data is not None

    asyncio.run(_test())


def test_unexpected_error_keeps_other_targets_failures_as_note(harness_factory, monkeypatch):
    """A programming error from one target is re-raised with the other
    targets' write failures attached, so neither report is lost."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop(), {CONF_RETRY_COUNT: 1})
        await h.add_entry("e1", "AA:BB:CC:DD:EE:01")
        await h.add_entry("e2", "AA:BB:CC:DD:EE:02")

        async def hook(ble_device, preset, image, **kwargs):
            if h.write_prepared.await_count == 1:
                raise ValueError("bug")
            return WriteResult(success=False, error="boom")

        h.write_hook = hook
        with pytest.raises(ValueError, match="bug") as excinfo:
            await h.call("write", ["dev-e1", "dev-e2"], payload="x")
        assert any("boom" in note for note in getattr(excinfo.value, "__notes__", []))

    asyncio.run(_test())


def test_services_registered_once_at_domain_setup(harness_factory):
    """Services come from async_setup, not per entry, and survive an entry unload."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        assert h.services == {}
        await h.add_entry("e1", "AA:BB:CC:DD:EE:01")
        assert set(h.services) == {"write", "write_guarded"}
        first = h.services["write"]
        await h.add_entry("e2", "AA:BB:CC:DD:EE:02")
        assert h.services["write"] is first  # second entry does not re-register

        h.hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        assert await integration.async_unload_entry(h.hass, h.entries["e1"])
        assert h.services["write"] is first
        h.hass.services.async_remove.assert_not_called()

    asyncio.run(_test())


def test_unload_cancels_pending_debounced_write(harness_factory):
    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        entry = await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        await h.call("write_guarded", "dev-e1", payload="queued", debounce_override_ms=200)
        assert entry.runtime_data.pending_write_cancel is not None

        h.hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        assert await integration.async_unload_entry(h.hass, entry)
        assert entry.runtime_data.pending_write_cancel is None
        await asyncio.sleep(0.3)
        assert h.write_prepared.await_count == 0

    asyncio.run(_test())


def test_unload_drops_debounced_write_queued_on_lock(harness_factory):
    """A debounced write whose timer already fired but which is still waiting
    for the BLE lock is dropped when its entry unloads."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        entry = await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        lock = h.hass.data[DATA_LOCK]
        await lock.acquire()
        await h.call("write_guarded", "dev-e1", payload="stale", debounce_override_ms=50)
        await asyncio.sleep(0.1)  # timer fired; the write is queued on the lock

        h.hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        assert await integration.async_unload_entry(h.hass, entry)
        lock.release()
        await asyncio.sleep(0.05)
        assert h.write_prepared.await_count == 0

    asyncio.run(_test())


def test_write_lock_seeded_from_entry_data(harness_factory):
    """A persisted write lock gates writes before the switch entity is added."""

    async def _test():
        h = harness_factory(asyncio.get_running_loop())
        entry = await h.add_entry("e1", "AA:BB:CC:DD:EE:FF")
        assert entry.runtime_data.write_lock is False

        h.entries.clear()
        locked = _make_entry("e2", "AA:BB:CC:DD:EE:02", h.options)
        locked.data = {**locked.data, integration.WRITE_LOCK: True}
        h.entries["e2"] = locked
        assert await integration.async_setup_entry(h.hass, locked)
        locked.runtime_data.device_id = "dev-e2"
        assert locked.runtime_data.write_lock is True

        await h.call("write", "dev-e2", payload="x")
        assert h.write_prepared.await_count == 0

    asyncio.run(_test())
