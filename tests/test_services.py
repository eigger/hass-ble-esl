"""ble_esl.write / ble_esl.write_guarded through a real Home Assistant.

Only the backend's encode/transfer and the renderer are stubbed (see the
`tag_writer` fixture); target resolution, the BLE lock, debounce timers,
retries and the result sensors are the real code paths.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from bt import register_adapter, register_proxy
from conftest import IDENT, device_id_of, setup_entry, wolink_service_info
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.ble_esl.const import (
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_RETRY_COUNT,
    DATA_LOCK,
    DOMAIN,
)
from custom_components.ble_esl.esl_ble.base import WriteResult

PAYLOAD = [{"type": "text", "value": "hi", "x": 0, "y": 0}]


async def call(hass: HomeAssistant, service: str, target, **data) -> None:
    await hass.services.async_call(
        DOMAIN, service, {"device_id": target, "payload": PAYLOAD, **data}, blocking=True
    )


def sensor(hass: HomeAssistant, key: str, ident: str = IDENT) -> str:
    return hass.states.get(f"sensor.zhsunyco_{ident}_{key}").state


async def advance(hass: HomeAssistant, freezer, seconds: float, *, settle: bool = True) -> None:
    """Move the (frozen) clock `seconds` ahead and fire due timers.

    With `settle`, also wait for debounced writes that fired to finish; pass
    settle=False when the test itself holds the BLE lock they queue on.
    """
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    if settle:
        await debounced_writes_done()


async def debounced_writes_done() -> None:
    """Await the background tasks that fired debounced writes create.

    block_till_done() skips background tasks (and waiting for *all* of them
    would include bluetooth's long-running ones), so wait for ours by name.
    """
    ours = [t for t in asyncio.all_tasks() if t.get_name().startswith("ble_esl debounced write")]
    if ours:
        await asyncio.gather(*ours)


# ── Basics ───────────────────────────────────────────────────────────────


async def test_write_sends_rendered_image_and_updates_image_entity(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    device_id = device_id_of(hass)
    assert hass.states.get(f"image.zhsunyco_{IDENT}_last_updated_content").state == "unknown"

    await call(hass, "write", device_id)

    assert tag_writer.write_prepared.await_count == 1
    assert tag_writer.sent_image().size == (296, 128)
    assert hass.states.get(f"image.zhsunyco_{IDENT}_last_updated_content").state != "unknown"
    assert wolink_entry.runtime_data.last_write_timing == {
        "attempt": 1,
        "success": True,
        "transfer_s": 0.1,
    }
    # ...and the Write Duration sensor carries it as attributes for monitoring.
    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert attrs["attempt"] == 1 and attrs["success"] is True and attrs["transfer_s"] == 0.1
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_display_in_sync").state == "on"
    assert sensor(hass, "failure_count") == "0"
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_connectivity").state == "off"


async def test_write_reports_the_radio_it_went_through(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """The Write Duration attributes name the proxy (or adapter) used, the
    tag's RSSI as that radio saw it, and how many radios could reach the tag.

    Without the connected-scanner handle (older habluetooth, or a stubbed
    client) the scanner holding the strongest advertisement is reported.
    """
    proxy = register_proxy(hass, "esp-livingroom", "AA:BB:CC:00:00:01")
    proxy.inject_advertisement(wolink_service_info(rssi=-71))
    await setup_entry(hass, advertise=False)

    await call(hass, "write", device_id_of(hass))

    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert attrs["via"] == "esp-livingroom (AA:BB:CC:00:00:01)"
    assert attrs["via_type"] == "proxy"
    assert attrs["via_source"] == "AA:BB:CC:00:00:01"
    assert attrs["rssi"] == -71
    assert attrs["paths"] == 1
    assert attrs["transfer_s"] == 0.1  # the protocol's own stages follow

    # With the handle (newer habluetooth), the scanner actually used wins,
    # even when another radio holds the stronger advertisement.
    other = register_proxy(hass, "esp-kitchen", "AA:BB:CC:00:00:02")
    other.inject_advertisement(wolink_service_info(rssi=-50))
    tag_writer.write_result = WriteResult(success=True, timing={"transfer_s": 0.1}, scanner=proxy)
    await call(hass, "write", device_id_of(hass))

    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert attrs["via_source"] == "AA:BB:CC:00:00:01" and attrs["rssi"] == -71
    assert attrs["paths"] == 2


async def test_write_reports_a_local_adapter(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """A tag reached through the host's own adapter is reported as such."""
    hci0 = register_adapter(hass, "hci0", "00:1A:7D:DA:71:13")
    hci0.inject_advertisement(wolink_service_info(rssi=-58))
    await setup_entry(hass, advertise=False)

    await call(hass, "write", device_id_of(hass))

    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert attrs["via"] == "hci0 (00:1A:7D:DA:71:13)"
    assert attrs["via_type"] == "adapter"
    assert attrs["via_source"] == "00:1A:7D:DA:71:13"
    assert attrs["rssi"] == -58
    assert attrs["paths"] == 1


async def test_dry_run_only_updates_preview(hass: HomeAssistant, wolink_entry, tag_writer) -> None:
    await call(hass, "write", device_id_of(hass), dry_run=True)
    assert tag_writer.write_prepared.await_count == 0
    assert hass.states.get(f"image.zhsunyco_{IDENT}_preview_content").state != "unknown"
    assert hass.states.get(f"image.zhsunyco_{IDENT}_last_updated_content").state == "unknown"
    assert wolink_entry.runtime_data.last_image_data is None  # not counted as sent


async def test_unavailable_handle_counts_as_failed_attempts(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """A missing BLE handle is a failed attempt: retried, counted, raised."""
    await setup_entry(hass, options={CONF_RETRY_COUNT: 3})
    tag_writer.available = False

    with pytest.raises(HomeAssistantError, match="unavailable"):
        await call(hass, "write", device_id_of(hass))

    assert tag_writer.write_prepared.await_count == 0
    assert sensor(hass, "failure_count") == "1"
    assert sensor(hass, "last_failure_time") != "unknown"


async def test_ble_handle_resolved_per_attempt(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """The handle is looked up right before each attempt, not at call time."""
    await setup_entry(hass, options={CONF_RETRY_COUNT: 2})
    tag_writer.available = False

    async def become_available(*args, **kwargs):
        return WriteResult(success=True)

    tag_writer.write_hook = become_available
    from custom_components.ble_esl import services as svc

    async def sleep_then_available(*args, **kwargs):
        tag_writer.available = True

    svc.sleep.side_effect = sleep_then_available  # the retry backoff (already stubbed)

    await call(hass, "write", device_id_of(hass))
    assert tag_writer.write_prepared.await_count == 1
    assert sensor(hass, "failure_count") == "0"


async def test_failed_write_after_retries(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    await setup_entry(hass, options={CONF_RETRY_COUNT: 3})
    tag_writer.write_result = WriteResult(success=False, error="boom")

    with pytest.raises(HomeAssistantError, match="after 3 attempts: boom"):
        await call(hass, "write", device_id_of(hass))

    assert tag_writer.write_prepared.await_count == 3
    assert sensor(hass, "failure_count") == "1"
    assert hass.states.get(f"image.zhsunyco_{IDENT}_last_updated_content").state == "unknown"
    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert (attrs["attempt"], attrs["success"], attrs["error"]) == (3, False, "boom")


async def test_retry_pacing_follows_only_transfer_failures(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """Packets are paced more only after an attempt that failed mid-transfer.

    Attempt 1 fails to connect (no transfer stage): attempt 2 runs at full
    speed. Attempt 2 fails during the transfer: attempt 3 is paced. The
    pacing is reported on the attempt it applied to.
    """
    await setup_entry(hass, options={CONF_RETRY_COUNT: 4})
    outcomes = iter(
        [
            WriteResult(success=False, error="connect", timing={"connect_s": 0.4}),
            WriteResult(
                success=False,
                error="stalled",
                timing={"connect_s": 0.1, "start_s": 0.2, "transfer_s": 1.5, "session_s": 1.7},
            ),
            WriteResult(
                success=False,
                error="refresh timeout",
                timing={"connect_s": 0.1, "transfer_s": 1.0, "finish_s": 30.0, "session_s": 31},
            ),
            WriteResult(success=True, timing={"transfer_s": 0.9}),
        ]
    )
    pacing: list[float] = []

    async def hook(ble_device, preset, image, **kwargs):
        pacing.append(kwargs["pacing_s"])
        return next(outcomes)

    tag_writer.write_hook = hook
    await call(hass, "write", device_id_of(hass))

    # connect failure -> no pacing; transfer failure -> paced; the refresh
    # timeout (panel, not link) adds nothing on top.
    assert pacing == [0.0, 0.0, 0.05, 0.05]
    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert attrs["attempt"] == 4 and attrs["pacing_s"] == 0.05
    assert sensor(hass, "failure_count") == "0"


async def test_encode_once_per_write_reused_across_retries(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    await setup_entry(hass, options={CONF_RETRY_COUNT: 3})
    tag_writer.write_result = WriteResult(success=False, error="boom")
    with pytest.raises(HomeAssistantError):
        await call(hass, "write", device_id_of(hass))
    futures = {id(c.args[2]) for c in tag_writer.write_prepared.await_args_list}
    assert len(futures) == 1


# ── Targets ──────────────────────────────────────────────────────────────


async def test_target_by_entity_and_area(hass: HomeAssistant, wolink_entry, tag_writer) -> None:
    """Any target form the UI offers resolves to the tag."""
    from homeassistant.helpers import area_registry as ar, device_registry as dr

    await hass.services.async_call(
        DOMAIN,
        "write",
        {"entity_id": f"switch.zhsunyco_{IDENT}_write_lock", "payload": PAYLOAD},
        blocking=True,
    )
    assert tag_writer.write_prepared.await_count == 1

    area = ar.async_get(hass).async_get_or_create("Kitchen")
    dr.async_get(hass).async_update_device(device_id_of(hass), area_id=area.id)
    await hass.services.async_call(
        DOMAIN, "write", {"area_id": area.id, "payload": PAYLOAD}, blocking=True
    )
    assert tag_writer.write_prepared.await_count == 2


async def test_no_matching_target_is_an_error(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    with pytest.raises(HomeAssistantError, match="No loaded BLE ESL device matches"):
        await call(hass, "write", "not-a-device")
    assert tag_writer.write_prepared.await_count == 0


async def test_multi_device_call_continues_after_failure(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """One unreachable tag must not stop the remaining targets from being written."""
    await setup_entry(hass, address="66:66:54:20:00:01", options={CONF_RETRY_COUNT: 1})
    await setup_entry(hass, address="66:66:54:20:00:02", options={CONF_RETRY_COUNT: 1})

    async def fail_first(ble_device, preset, image, **kwargs):
        if tag_writer.write_prepared.await_count == 1:
            return WriteResult(success=False, error="boom")
        return WriteResult(success=True)

    tag_writer.write_hook = fail_first
    targets = [device_id_of(hass, "66:66:54:20:00:01"), device_id_of(hass, "66:66:54:20:00:02")]
    with pytest.raises(HomeAssistantError, match="boom"):
        await call(hass, "write", targets)

    assert tag_writer.write_prepared.await_count == 2  # both attempted
    failures = sorted(sensor(hass, "failure_count", ident) for ident in ("54200001", "54200002"))
    assert failures == ["0", "1"]


async def test_multi_target_pipelines_encodes(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """The second tag has encoded before the first has finished transferring."""
    await setup_entry(hass, address="66:66:54:20:00:01")
    await setup_entry(hass, address="66:66:54:20:00:02")
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def slow_write(ble_device, preset, image, **kwargs):
        if not first_started.is_set():
            first_started.set()
            await release_first.wait()
        return WriteResult(success=True)

    tag_writer.write_hook = slow_write
    targets = [device_id_of(hass, "66:66:54:20:00:01"), device_id_of(hass, "66:66:54:20:00:02")]
    task = hass.async_create_task(call(hass, "write", targets))
    await first_started.wait()
    # While the first tag is still transferring, the second has already encoded.
    for _ in range(200):
        if len(tag_writer.encoded) == 2:
            break
        await asyncio.sleep(0.01)
    assert sorted(tag_writer.encoded) == ["66:66:54:20:00:01", "66:66:54:20:00:02"]
    assert tag_writer.write_prepared.await_count == 1
    release_first.set()
    await task
    assert tag_writer.write_prepared.await_count == 2


# ── write_guarded ────────────────────────────────────────────────────────


async def test_duplicate_guard_ignores_failed_write(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """Only a successful write may suppress a later identical write_guarded call."""
    await setup_entry(hass, options={CONF_RETRY_COUNT: 1, CONF_PREVENT_DUPLICATE_SEND: True})
    device_id = device_id_of(hass)

    tag_writer.write_result = WriteResult(success=False, error="boom")
    with pytest.raises(HomeAssistantError):
        await call(hass, "write_guarded", device_id)

    tag_writer.write_result = WriteResult(success=True)
    await call(hass, "write_guarded", device_id)  # same payload: must be sent
    assert tag_writer.write_prepared.await_count == 2

    await call(hass, "write_guarded", device_id)  # now a genuine duplicate
    assert tag_writer.write_prepared.await_count == 2


async def test_duplicate_guard_rechecked_under_lock(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """Same payload arriving while an identical write is in flight is skipped."""
    await setup_entry(hass, options={CONF_PREVENT_DUPLICATE_SEND: True})
    device_id = device_id_of(hass)
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def slow_write(*args, **kwargs):
        first_started.set()
        await release_first.wait()
        return WriteResult(success=True)

    tag_writer.write_hook = slow_write
    first = hass.async_create_task(call(hass, "write_guarded", device_id))
    await first_started.wait()
    second = hass.async_create_task(call(hass, "write_guarded", device_id))
    await asyncio.sleep(0)
    release_first.set()
    await first
    await second
    assert tag_writer.write_prepared.await_count == 1


async def test_write_lock_skips_physical_write(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": f"switch.zhsunyco_{IDENT}_write_lock"}, blocking=True
    )
    assert wolink_entry.data["write_lock"] is True  # persisted
    await call(hass, "write", device_id_of(hass))
    await call(hass, "write_guarded", device_id_of(hass))
    assert tag_writer.write_prepared.await_count == 0
    assert hass.states.get(f"image.zhsunyco_{IDENT}_preview_content").state != "unknown"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": f"switch.zhsunyco_{IDENT}_write_lock"}, blocking=True
    )
    await call(hass, "write", device_id_of(hass))
    assert tag_writer.write_prepared.await_count == 1


async def test_dry_run_guarded_is_preview_only(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    await setup_entry(hass, options={CONF_PREVENT_DUPLICATE_SEND: True})
    device_id = device_id_of(hass)
    await call(hass, "write_guarded", device_id, dry_run=True)
    assert tag_writer.write_prepared.await_count == 0
    await call(hass, "write_guarded", device_id)  # not a duplicate of the dry run
    assert tag_writer.write_prepared.await_count == 1


# ── Debounce ─────────────────────────────────────────────────────────────


async def test_debounce_is_trailing_edge_with_last_payload(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer
) -> None:
    device_id = device_id_of(hass)
    await hass.services.async_call(
        DOMAIN,
        "write_guarded",
        {"device_id": device_id, "payload": "first", "debounce_override_ms": 5000},
        blocking=True,
    )
    await advance(hass, freezer, 3)
    await hass.services.async_call(
        DOMAIN,
        "write_guarded",
        {"device_id": device_id, "payload": "second!", "debounce_override_ms": 5000},
        blocking=True,
    )
    await advance(hass, freezer, 3)  # 6 s after the first call: timer was restarted
    assert tag_writer.write_prepared.await_count == 0

    await advance(hass, freezer, 3)  # 6 s after the second call
    assert tag_writer.write_prepared.await_count == 1
    assert tag_writer.sent_image().getpixel((0, 0))[0] == len("second!")
    assert wolink_entry.runtime_data.pending_write_cancel is None


async def test_immediate_write_cancels_pending_debounced_write(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer
) -> None:
    device_id = device_id_of(hass)
    await call(hass, "write_guarded", device_id, debounce_override_ms=5000)
    assert wolink_entry.runtime_data.pending_write_cancel is not None

    await call(hass, "write", device_id)
    assert wolink_entry.runtime_data.pending_write_cancel is None
    await advance(hass, freezer, 10)
    assert tag_writer.write_prepared.await_count == 1


async def test_fired_debounced_write_dropped_when_superseded(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer
) -> None:
    """A debounced write whose timer fired but which is still queued on the
    BLE lock is dropped once an immediate write cancels it."""
    device_id = device_id_of(hass)
    lock = hass.data[DATA_LOCK]
    await lock.acquire()

    await hass.services.async_call(
        DOMAIN,
        "write_guarded",
        {"device_id": device_id, "payload": "stale", "debounce_override_ms": 1000},
        blocking=True,
    )
    await advance(hass, freezer, 2, settle=False)  # timer fired; the write is queued on the lock
    assert wolink_entry.runtime_data.pending_write_cancel is None
    assert tag_writer.write_prepared.await_count == 0

    generation = wolink_entry.runtime_data.write_generation
    immediate = hass.async_create_task(
        hass.services.async_call(
            DOMAIN, "write", {"device_id": device_id, "payload": "fresh!!"}, blocking=True
        )
    )
    while wolink_entry.runtime_data.write_generation == generation:
        await asyncio.sleep(0)
    lock.release()
    await immediate
    await debounced_writes_done()

    assert tag_writer.write_prepared.await_count == 1
    assert tag_writer.sent_image().getpixel((0, 0))[0] == len("fresh!!")


async def test_unload_cancels_pending_debounced_write(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer
) -> None:
    await call(hass, "write_guarded", device_id_of(hass), debounce_override_ms=5000)
    assert wolink_entry.runtime_data.pending_write_cancel is not None
    assert await hass.config_entries.async_unload(wolink_entry.entry_id)
    await advance(hass, freezer, 10)
    assert tag_writer.write_prepared.await_count == 0


async def test_unload_drops_debounced_write_queued_on_lock(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer
) -> None:
    lock = hass.data[DATA_LOCK]
    await lock.acquire()
    await call(hass, "write_guarded", device_id_of(hass), debounce_override_ms=1000)
    await advance(hass, freezer, 2, settle=False)  # fired, queued on the lock
    assert await hass.config_entries.async_unload(wolink_entry.entry_id)
    lock.release()
    await debounced_writes_done()
    assert tag_writer.write_prepared.await_count == 0


# ── Unexpected errors ────────────────────────────────────────────────────


async def test_unexpected_error_keeps_other_targets_failures_as_note(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    await setup_entry(hass, address="66:66:54:20:00:01", options={CONF_RETRY_COUNT: 1})
    await setup_entry(hass, address="66:66:54:20:00:02", options={CONF_RETRY_COUNT: 1})

    async def hook(ble_device, preset, image, **kwargs):
        if tag_writer.write_prepared.await_count == 1:
            raise ValueError("bug")
        return WriteResult(success=False, error="boom")

    tag_writer.write_hook = hook
    targets = [device_id_of(hass, "66:66:54:20:00:01"), device_id_of(hass, "66:66:54:20:00:02")]
    with pytest.raises(ValueError, match="bug") as excinfo:
        await call(hass, "write", targets)
    assert any("boom" in note for note in getattr(excinfo.value, "__notes__", []))


async def test_skipped_write_discards_failed_encode_quietly(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    """A write skipped under the lock consumes its encode future, so a failing
    encode never logs 'exception was never retrieved'."""
    from custom_components.ble_esl.esl_ble.wolink import WolinkBleBackend

    wolink_entry.runtime_data.write_lock = True

    def broken(preset, image, address):
        raise RuntimeError("encode failed")

    unhandled: list = []
    hass.loop.set_exception_handler(lambda loop, ctx: unhandled.append(ctx))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(WolinkBleBackend, "prepare_image", staticmethod(broken))
        await call(hass, "write", device_id_of(hass))
        await asyncio.sleep(0.05)
    import gc

    gc.collect()
    assert tag_writer.write_prepared.await_count == 0
    assert unhandled == []


# ── Response data ────────────────────────────────────────────────────────


async def respond(hass: HomeAssistant, service: str, target, **data):
    return await hass.services.async_call(
        DOMAIN,
        service,
        {"device_id": target, "payload": PAYLOAD, **data},
        blocking=True,
        return_response=True,
    )


async def test_response_written(hass: HomeAssistant, wolink_entry, tag_writer) -> None:
    device_id = device_id_of(hass)
    response = await respond(hass, "write", device_id)
    assert set(response) == {device_id}
    outcome = response[device_id]
    assert outcome["status"] == "written"
    assert outcome["attempts"] == 1
    assert outcome["duration_s"] >= 0
    assert outcome["timing"] == {"transfer_s": 0.1}


async def test_response_reports_failure_instead_of_raising(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """With a response requested, a failed tag is reported, not raised."""
    await setup_entry(hass, options={CONF_RETRY_COUNT: 2})
    tag_writer.write_result = WriteResult(success=False, error="boom", timing={"connect_s": 0.5})

    response = await respond(hass, "write", device_id_of(hass))

    outcome = response[device_id_of(hass)]
    assert outcome["status"] == "failed"
    assert outcome["error"] == "boom"
    assert outcome["attempts"] == 2
    assert outcome["timing"] == {"connect_s": 0.5}
    assert sensor(hass, "failure_count") == "1"  # sensors still updated


async def test_response_mixed_targets(hass: HomeAssistant, enable_bluetooth, tag_writer) -> None:
    await setup_entry(hass, address="66:66:54:20:00:01", options={CONF_RETRY_COUNT: 1})
    await setup_entry(hass, address="66:66:54:20:00:02", options={CONF_RETRY_COUNT: 1})
    first, second = device_id_of(hass, "66:66:54:20:00:01"), device_id_of(hass, "66:66:54:20:00:02")

    async def fail_first(ble_device, preset, image, **kwargs):
        return WriteResult(success=ble_device.address != "66:66:54:20:00:01", error="boom")

    tag_writer.write_hook = fail_first
    response = await respond(hass, "write", [first, second])
    assert response[first]["status"] == "failed"
    assert response[second]["status"] == "written"


async def test_response_guarded_statuses(
    hass: HomeAssistant, enable_bluetooth, tag_writer, freezer
) -> None:
    entry = await setup_entry(hass, options={CONF_PREVENT_DUPLICATE_SEND: True})
    device_id = device_id_of(hass)

    assert (await respond(hass, "write_guarded", device_id, dry_run=True))[device_id] == {
        "status": "preview"
    }

    assert (await respond(hass, "write_guarded", device_id))[device_id]["status"] == "written"
    assert (await respond(hass, "write_guarded", device_id))[device_id] == {"status": "duplicate"}

    entry.runtime_data.write_lock = True
    assert (await respond(hass, "write_guarded", device_id, payload="new"))[device_id] == {
        "status": "locked"
    }
    entry.runtime_data.write_lock = False

    response = await respond(
        hass, "write_guarded", device_id, payload="newer", debounce_override_ms=5000
    )
    assert response[device_id] == {"status": "scheduled", "delay_ms": 5000}
    await advance(hass, freezer, 6)
    assert tag_writer.write_prepared.await_count == 2


async def test_response_locked_for_write(hass: HomeAssistant, wolink_entry, tag_writer) -> None:
    wolink_entry.runtime_data.write_lock = True
    response = await respond(hass, "write", device_id_of(hass))
    assert response[device_id_of(hass)] == {"status": "locked"}


async def test_no_target_still_raises_with_response(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    with pytest.raises(HomeAssistantError, match="No loaded BLE ESL device matches"):
        await respond(hass, "write", "not-a-device")
