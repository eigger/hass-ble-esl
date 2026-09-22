"""ble_esl.write / ble_esl.write_guarded through a real Home Assistant.

Only the backend's encode/transfer and the renderer are stubbed (see the
`tag_writer` fixture); target resolution, the BLE lock, debounce timers,
retries and the result sensors are the real code paths.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import patch

from blesession import LinkInfo, SessionDropped, generic_cause
from bt import register_adapter, register_proxy
from conftest import IDENT, device_id_of, setup_entry, wolink_service_info
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from writes import fail, ok

from custom_components.ble_esl.const import (
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_RETRY_COUNT,
    DATA_LOCK,
    DOMAIN,
)
from custom_components.ble_esl.esl_ble.base import WriteResult
from custom_components.ble_esl.services import _likely_cause

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
    report = wolink_entry.runtime_data.reports.last
    radio = {k: report.pop(k) for k in ("via", "via_type", "rssi", "paths") if k in report}
    assert report == {
        "operation": "write",
        "success": True,
        "attempt": 1,
        "attempts": 3,
        "transfer_s": 0.1,
    }
    assert "paths" in radio  # the radio itself is covered by the tests below
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
    assert attrs["rssi"] == -71
    assert attrs["paths"] == 1
    assert attrs["transfer_s"] == 0.1  # the protocol's own stages follow

    # With the handle (newer habluetooth), the scanner actually used wins,
    # even when another radio holds the stronger advertisement.
    other = register_proxy(hass, "esp-kitchen", "AA:BB:CC:00:00:02")
    other.inject_advertisement(wolink_service_info(rssi=-50))
    tag_writer.write_result = ok(transfer=0.1, link=LinkInfo(via=proxy))
    await call(hass, "write", device_id_of(hass))

    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert attrs["via"] == "esp-livingroom (AA:BB:CC:00:00:01)" and attrs["rssi"] == -71
    assert attrs["paths"] == 2
    # The radio with the strongest advertisement is named when it is not the one used.
    assert attrs["advertised_via"] == "esp-kitchen (AA:BB:CC:00:00:02)"


async def test_likely_cause_reads_stage_error_and_radio(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """The failure sensors explain a failure in one sentence, using the
    radio situation when it is the likely reason."""
    proxy = register_proxy(hass, "esp-kitchen", "AA:BB:CC:00:00:09")
    proxy.inject_advertisement(wolink_service_info(rssi=-91))
    await setup_entry(hass, options={CONF_RETRY_COUNT: 1}, advertise=False)
    tag_writer.write_result = fail(
        "Transfer stalled: part 3/40 requested 6 times", connect=0.2, handshake=0.3, transfer=4.0
    )

    with pytest.raises(HomeAssistantError):
        await call(hass, "write", device_id_of(hass))

    failed = hass.states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").attributes
    assert failed["failed_stage"] == "transfer"
    assert failed["likely_cause"] == (
        "The tag kept asking for the same part: a marginal link. "
        "The signal is weak (-91 dBm via esp-kitchen (AA:BB:CC:00:00:09)) "
        "and no other radio reaches the tag — move the tag or add a proxy."
    )

    # No handle at all: nothing was tried, and the sentence says so.
    tag_writer.available = False
    with pytest.raises(HomeAssistantError):
        await call(hass, "write", device_id_of(hass))
    failed = hass.states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").attributes
    assert failed["failed_stage"] == "unreachable"
    assert failed["likely_cause"].startswith("No radio currently sees the tag")


@pytest.mark.parametrize(
    ("stage", "error", "via", "backend", "expected"),
    [
        # A single radio with a fine signal is the normal case: no placement advice.
        (
            "connect",
            "timeout",
            {"rssi": -60, "paths": 1},
            "wolink",
            "The BLE link could not be established.",
        ),
        # A handshake that goes unanswered is not an unexpected answer.
        (
            "auth",
            "No response from device within 5s after command 0x01",
            {},
            "xte",
            "The tag did not answer the handshake: not ready, or the link dropped.",
        ),
        (
            "auth",
            "device error 5: unlock (auth) failed",
            {},
            "wolink",
            "The tag rejected authentication: not a WOLINK tag, or different firmware.",
        ),
        # The completion wait is the panel on WOLINK/easyTag, the end-command ack on XTE.
        (
            "finish",
            "No response from device within 30s after refresh",
            {},
            "wolink",
            "The tag took the image but did not report the refresh done in time: "
            "a slow panel (cold, large) or a tag-side error.",
        ),
        (
            "finish",
            "No response from device within 5s after command 0x04",
            {},
            "xte",
            "The tag took the image but did not acknowledge the end command.",
        ),
        (
            "finish",
            "device error 2: epd write error",
            {},
            "wolink",
            "The tag reported an error after the transfer: device error 2: epd write error.",
        ),
        # A link that went away mid-session is blesession's `link_lost`, not
        # a protocol failure: no per-stage reading of ours improves on it.
        (
            "transfer",
            "The link dropped while waiting for part 12",
            {},
            "wolink",
            "The link to the tag went away mid-session: out of range, powered "
            "down, or the adapter / proxy reset.",
        ),
        (
            "finish",
            "The link dropped while waiting for refresh",
            {},
            "xte",
            "The link to the tag went away mid-session: out of range, powered "
            "down, or the adapter / proxy reset.",
        ),
    ],
)
def test_likely_cause_wording(stage, error, via, backend, expected) -> None:
    """The tag's own sentences first; blesession's generic ones where it has none."""
    sentence = _likely_cause(stage, error, via, backend)
    if sentence is None:
        sentence = generic_cause(stage, error, via, noun="tag")
    assert sentence == expected


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

    with pytest.raises(HomeAssistantError, match="No connectable radio sees"):
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
    from blesession import attempts as attempts_mod

    async def sleep_then_available(*args, **kwargs):
        tag_writer.available = True

    attempts_mod.sleep.side_effect = sleep_then_available  # the retry pause (already stubbed)

    await call(hass, "write", device_id_of(hass))
    assert tag_writer.write_prepared.await_count == 1
    assert sensor(hass, "failure_count") == "0"


async def test_failed_write_after_retries(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    await setup_entry(hass, options={CONF_RETRY_COUNT: 3})
    tag_writer.write_result = fail("boom", connect=0.5)

    with pytest.raises(HomeAssistantError, match="after 3 attempts: boom"):
        await call(hass, "write", device_id_of(hass))

    assert tag_writer.write_prepared.await_count == 3
    assert sensor(hass, "failure_count") == "1"
    assert hass.states.get(f"image.zhsunyco_{IDENT}_last_updated_content").state == "unknown"
    attrs = hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes
    assert (attrs["attempt"], attrs["success"], attrs["error"]) == (3, False, "boom")
    assert attrs["failed_stage"] == "connect"  # the stub died in `connect`
    assert attrs["likely_cause"].startswith("The BLE link could not be established.")
    # The failed write's breakdown is also on Last Failure Time...
    failed = hass.states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").attributes
    assert (failed["attempt"], failed["success"], failed["error"]) == (3, False, "boom")
    assert failed["failed_stage"] == "connect"

    # ...and stays there after a later write succeeds, while Write Duration moves on.
    tag_writer.write_result = ok(transfer=0.1)
    await call(hass, "write", device_id_of(hass))
    assert hass.states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes["success"] is True
    failed = hass.states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").attributes
    assert (failed["attempt"], failed["success"], failed["error"]) == (3, False, "boom")


async def test_recovered_attempt_is_not_a_write_failure(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    """An attempt a retry recovered from does not become the last failure.

    `last_failure` is the write that failed with every retry exhausted, which
    is what the Last Failure Time timestamp beside it records; filing each
    failed attempt would leave the attributes describing an event the state
    does not.
    """
    data = wolink_entry.runtime_data
    calls = 0

    async def hook(ble_device, preset, image, **kwargs):
        nonlocal calls
        calls += 1
        return fail("first try", connect=0.1) if calls == 1 else ok(transfer=0.1)

    tag_writer.write_hook = hook
    await call(hass, "write", device_id_of(hass))

    assert data.reports.last["success"] is True  # attempt 2
    assert data.reports.last_failure is None
    assert sensor(hass, "failure_count") == "0"
    assert sensor(hass, "last_failure_time") == "unknown"


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
            fail("connect", connect=0.4),
            fail("stalled", connect=0.1, handshake=0.2, transfer=1.5),
            fail("refresh timeout", connect=0.1, transfer=1.0, finish=30.0),
            ok(transfer=0.9),
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

    # The action's response carries the same breakdown, pacing included.
    outcomes = iter([fail("stalled", transfer=1.0), ok(transfer=1.0)])
    response = await respond(hass, "write", device_id_of(hass))
    timing = response[device_id_of(hass)]["timing"]
    assert (timing["attempt"], timing["transfer_s"], timing["pacing_s"]) == (2, 1.0, 0.05)


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

    """A bug in the pipeline itself (not a failed attempt: anything the
    attempt raises is one) keeps its traceback and the other tags' failures."""
    from custom_components.ble_esl import services as svc

    real_report = svc._report

    def report(hass, job, attempt):
        if job.address == "66:66:54:20:00:01":
            raise ValueError("bug")
        return real_report(hass, job, attempt)

    tag_writer.write_result = fail("boom")
    targets = [device_id_of(hass, "66:66:54:20:00:01"), device_id_of(hass, "66:66:54:20:00:02")]
    with patch.object(svc, "_report", report), pytest.raises(ValueError, match="bug") as excinfo:
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
    assert outcome["timing"]["success"] is True and outcome["timing"]["transfer_s"] == 0.1


async def test_response_reports_failure_instead_of_raising(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """With a response requested, a failed tag is reported, not raised."""
    await setup_entry(hass, options={CONF_RETRY_COUNT: 2})
    tag_writer.write_result = fail("boom", connect=0.5)

    response = await respond(hass, "write", device_id_of(hass))

    outcome = response[device_id_of(hass)]
    assert outcome["status"] == "failed"
    assert outcome["error"] == "boom"
    assert outcome["attempts"] == 2
    timing = outcome["timing"]
    assert list(timing)[:7] == [
        "operation",
        "success",
        "error",
        "failed_stage",
        "likely_cause",
        "likely_cause_key",
        "attempt",
    ]
    assert timing["failed_stage"] == "connect"
    assert timing["likely_cause"] == "The BLE link could not be established."
    # The stable name of that generic sentence, for a translated rendering.
    assert timing["likely_cause_key"] == "connect.failed"
    assert timing["connect_s"] == 0.5
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


# ── Persistence across restarts ──────────────────────────────────────────


async def test_last_images_survive_a_reload(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer, hass_storage
) -> None:
    """The last written and last rendered image are kept in .storage, so after
    a restart Prevent Duplicate Send still knows the tag's image, the image
    entities are not blank, and Display In Sync is right."""
    device_id = device_id_of(hass)
    await call(hass, "write", device_id)
    # No wait for the delayed save: unloading flushes it, so a reload right
    # after a write restores the new image, not the previous one.

    key = f"{DOMAIN}.{wolink_entry.entry_id}.images"
    await hass.config_entries.async_reload(wolink_entry.entry_id)
    await hass.async_block_till_done()
    stored = hass_storage[key]["data"]
    assert stored["written"]["png"] == stored["preview"]["png"]
    written_at = stored["written"]["at"]

    data = wolink_entry.runtime_data
    assert data.last_image_data is not None
    image = hass.states.get(f"image.zhsunyco_{IDENT}_last_updated_content")
    assert image.state == written_at  # restored with its original timestamp
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_display_in_sync").state == "on"

    # The same payload after the restart is a duplicate: nothing is sent.
    hass.config_entries.async_update_entry(
        wolink_entry, options={CONF_PREVENT_DUPLICATE_SEND: True}
    )
    await hass.async_block_till_done()
    response = await respond(hass, "write_guarded", device_id_of(hass))
    assert response[device_id_of(hass)]["status"] == "duplicate"
    assert tag_writer.write_prepared.await_count == 1  # only the write before the reload


async def test_newer_preview_survives_a_reload_as_out_of_sync(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer, hass_storage
) -> None:
    """A dry_run rendered after the last write is remembered as such."""
    await call(hass, "write", device_id_of(hass))
    await call(hass, "write", device_id_of(hass), dry_run=True, payload=[*PAYLOAD, *PAYLOAD])
    await advance(hass, freezer, 2)

    await hass.config_entries.async_reload(wolink_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_display_in_sync").state == "off"
    assert hass.states.get(f"image.zhsunyco_{IDENT}_preview_content").state != "unknown"


async def test_stored_images_are_removed_with_the_entry(
    hass: HomeAssistant, wolink_entry, tag_writer, freezer, hass_storage
) -> None:
    await call(hass, "write", device_id_of(hass))
    await advance(hass, freezer, 2)
    key = f"{DOMAIN}.{wolink_entry.entry_id}.images"
    assert key in hass_storage

    await hass.config_entries.async_remove(wolink_entry.entry_id)
    await hass.async_block_till_done()

    assert key not in hass_storage


# ── Lock scope: one attempt at a time, one write per tag ─────────────────


async def test_other_tags_write_between_a_failing_tags_attempts(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """The BLE lock covers one attempt, not a whole retry sequence: while a
    failing tag pauses before its retry, the tags queued behind it write."""
    a, b = "66:66:54:20:00:01", "66:66:54:20:00:02"
    await setup_entry(hass, address=a, options={CONF_RETRY_COUNT: 2})
    await setup_entry(hass, address=b, options={CONF_RETRY_COUNT: 2})
    order: list[str] = []

    async def hook(ble_device, preset, image, **kwargs):
        order.append(ble_device.address[-2:])
        if ble_device.address == a and order.count("01") == 1:
            return fail("first try", connect=0.1)
        return ok(transfer=0.1)

    tag_writer.write_hook = hook
    response = await respond(hass, "write", [device_id_of(hass, a), device_id_of(hass, b)])

    assert response[device_id_of(hass, a)]["status"] == "written"
    assert response[device_id_of(hass, b)]["status"] == "written"
    assert order == ["01", "02", "01"]  # b went first while a waited to retry


async def test_two_writes_to_one_tag_do_not_interleave(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    """The per-tag lock keeps a second write to the same tag behind the first
    one's retries, so the tag's write state is never shared by two writes."""
    order: list[str] = []
    calls = 0

    async def hook(ble_device, preset, image, **kwargs):
        nonlocal calls
        calls += 1
        order.append(f"w{image.getpixel((0, 0))[0]}")
        if calls == 1:
            return fail("first try", connect=0.1)
        return ok(transfer=0.1)

    tag_writer.write_hook = hook
    device_id = device_id_of(hass)
    first = hass.async_create_task(call(hass, "write", device_id))
    await asyncio.sleep(0)  # let the first write take the tag's lock
    second = hass.async_create_task(call(hass, "write", device_id, payload=[*PAYLOAD, *PAYLOAD]))
    await asyncio.gather(first, second)

    # first write: two attempts back to back; then the second write.
    assert order[0] == order[1] and order[2] != order[0]


async def test_guards_are_rechecked_before_a_retry(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    """Turning the Write Lock on while a write waits to retry stops it."""
    data = wolink_entry.runtime_data

    async def hook(ble_device, preset, image, **kwargs):
        data.write_lock = True  # flipped during attempt 1
        return fail("first try", connect=0.1)

    tag_writer.write_hook = hook
    response = await respond(hass, "write", device_id_of(hass))

    assert response[device_id_of(hass)]["status"] == "locked"
    assert tag_writer.write_prepared.await_count == 1  # no second attempt
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_connectivity").state == "off"


async def test_declined_attempt_is_reported_as_skipped(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    """A guard that declines under the lock says so on the breakdown, and is
    not counted or published as a failure."""
    data = wolink_entry.runtime_data

    async def hook(ble_device, preset, image, **kwargs):
        data.write_lock = True  # flipped during attempt 1
        return fail("first try", connect=0.1)

    tag_writer.write_hook = hook
    await respond(hass, "write", device_id_of(hass))

    report = data.reports.last
    assert report["success"] is False
    assert report["skipped"] == "locked"  # a scalar: it goes on the entity
    assert "error" not in report
    # Declining is not failing: the write ends as "locked", so the failure
    # sensors stay where they were.
    assert sensor(hass, "failure_count") == "0"
    assert sensor(hass, "last_failure_time") == "unknown"


async def test_a_dropped_link_mid_transfer_reads_as_a_lost_link(
    hass: HomeAssistant, enable_bluetooth, tag_writer
) -> None:
    """blesession ends a wait the moment the link goes; the breakdown names
    the stage it died in and gives the generic `link_lost` reading."""
    await setup_entry(hass, options={CONF_RETRY_COUNT: 1})
    tag_writer.write_result = fail(
        "The link dropped while waiting for part 12",
        exc=SessionDropped,
        connect=0.2,
        handshake=0.1,
        transfer=0.4,
    )

    with pytest.raises(HomeAssistantError, match="The link dropped"):
        await call(hass, "write", device_id_of(hass))

    failed = hass.states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").attributes
    assert failed["failed_stage"] == "transfer"
    assert failed["likely_cause"].startswith("The link to the tag went away mid-session")
    assert failed["likely_cause_key"] == "link_lost"


async def test_timed_out_attempt_is_not_retried(
    hass: HomeAssistant, enable_bluetooth, tag_writer, monkeypatch
) -> None:
    """An attempt that hit the bound means a dead transport; the write fails
    without spending the remaining retries on the same path."""
    await setup_entry(hass, options={CONF_RETRY_COUNT: 3})
    from custom_components.ble_esl import services as svc

    monkeypatch.setattr(svc, "ATTEMPT_TIMEOUT_S", 0.05)

    async def hang(ble_device, preset, image, *, trace, **kwargs):
        with trace.timed("transfer"):
            await asyncio.Event().wait()

    tag_writer.write_hook = hang
    with pytest.raises(HomeAssistantError, match="after 1 attempts: Attempt timed out"):
        await call(hass, "write", device_id_of(hass))

    assert tag_writer.write_prepared.await_count == 1
    assert sensor(hass, "failure_count") == "1"
    failed = hass.states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").attributes
    assert failed["timed_out"] is True and failed["failed_stage"] == "transfer"
    assert "cut at its bound" in failed["likely_cause"]
