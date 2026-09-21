"""The ble_esl.write / ble_esl.write_guarded services and the BLE write pipeline.

A write goes: resolve targets -> render (executor) -> [debounce] -> encode
(executor, started before queueing) -> BLE lock -> connect + transfer with
retries. Services are registered once per Home Assistant instance in
async_setup(); handlers look up the targeted config entries at call time.
"""

from __future__ import annotations

import asyncio
from asyncio import Future, sleep
from collections.abc import Awaitable, Callable
import contextlib
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from io import BytesIO
import logging
import time
from typing import Any

from homeassistant.components.bluetooth import (
    BaseHaRemoteScanner,
    BaseHaScanner,
    async_ble_device_from_address,
    async_last_service_info,
    async_scanner_by_source,
    async_scanner_devices_by_address,
)
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.service import async_extract_config_entry_ids
from homeassistant.util.dt import now
from PIL import Image

from .const import (
    CONF_DEBOUNCE_MS,
    CONF_MODEL,
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_RETRY_COUNT,
    DATA_LOCK,
    DEFAULT_DEBOUNCE_MS,
    DEFAULT_MODEL,
    DEFAULT_PREVENT_DUPLICATE_SEND,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
    SERVICE_WRITE,
    SERVICE_WRITE_GUARDED,
)
from .data import BleEslRuntimeData
from .device import resolve_preset
from .esl_ble import WriteResult
from .esl_ble.base import RETRY_BACKOFF_S, DevicePreset
from .renderer import render_image
from .types import BleEslConfigEntry

_LOGGER = logging.getLogger(__name__)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the domain services (once per HA instance)."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_WRITE,
        partial(_async_write, hass),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_WRITE_GUARDED,
        partial(_async_write_guarded, hass),
        supports_response=SupportsResponse.OPTIONAL,
    )


# ── Target resolution ────────────────────────────────────────────────────


async def async_targeted_entries(
    hass: HomeAssistant, service: ServiceCall
) -> list[BleEslConfigEntry]:
    """Resolve a service call's target (entity/device/area/floor/label) to
    the loaded BLE ESL config entries it refers to."""
    entry_ids = await async_extract_config_entry_ids(service)
    # Ids the helper returns for devices/entities of *other* integrations, or
    # targets not in the registries at all, are simply absent here: that is
    # HA's standard target contract (a call is not an error because one of
    # several targets is unknown), so only an all-miss is reported.
    loaded = {entry.entry_id: entry for entry in hass.config_entries.async_loaded_entries(DOMAIN)}
    targets = [loaded[entry_id] for entry_id in sorted(entry_ids) if entry_id in loaded]
    if not targets:
        raise HomeAssistantError(
            "No loaded BLE ESL device matches the service target; "
            "target a BLE ESL device, one of its entities, or its area/label."
        )
    return targets


# ── Outcomes (service response data) ────────────────────────────────────


@dataclass
class WriteOutcome:
    """What happened to one target, reported in the service response.

    status:  written    the image is on the tag
             failed     every attempt failed (see error / attempts)
             scheduled  write_guarded: debounced, will run after `delay_ms`;
                        what happens then is not part of the response
             duplicate  write_guarded: unchanged image, not sent
             locked     the write-lock switch is on, not sent
             preview    dry_run: rendered only
             dropped    internal only (a fired debounced write superseded
                        on the lock); never reaches a service response
    """

    status: str
    error: str | None = None
    attempts: int | None = None
    duration_s: float | None = None
    delay_ms: int | None = None
    timing: dict[str, float | int | bool | str] | None = None

    def as_response(self) -> dict[str, Any]:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}


class WriteFailed(HomeAssistantError):
    """A write failed after its retries; carries the outcome for the response."""

    def __init__(self, address: str, outcome: WriteOutcome) -> None:
        super().__init__(
            f"Failed to write to {address} after {outcome.attempts} attempts: {outcome.error}"
        )
        self.outcome = outcome


async def _for_each_target(
    hass: HomeAssistant,
    service: ServiceCall,
    handler: Callable[[BleEslConfigEntry], Awaitable[WriteOutcome]],
) -> ServiceResponse:
    """Run handler for every targeted entry, continuing past failures.

    Handlers run concurrently: each renders and starts its encode right
    away and then queues on the BLE lock, which transfers to one tag at a
    time, so later tags encode while an earlier one is transferring. (The
    render step awaits before the lock, so the transfer order is the order
    renders finish, not necessarily the target order.)

    Without a requested response, write failures are collected and raised
    together at the end (one unreachable tag does not prevent the others
    from being written). With `response_variable`, failures are reported
    per target in the response instead of raising, so an automation can
    branch on them. Programming errors always raise.
    """
    targets = await async_targeted_entries(hass, service)
    results = await asyncio.gather(*(handler(entry) for entry in targets), return_exceptions=True)

    outcomes: dict[str, WriteOutcome] = {}
    errors: list[str] = []
    unexpected: list[BaseException] = []
    for entry, result in zip(targets, results, strict=True):
        if isinstance(result, WriteOutcome):
            outcomes[entry.runtime_data.device_id] = result
        elif isinstance(result, WriteFailed):
            outcomes[entry.runtime_data.device_id] = result.outcome
            errors.append(str(result))
        elif isinstance(result, HomeAssistantError):
            outcomes[entry.runtime_data.device_id] = WriteOutcome("failed", error=str(result))
            errors.append(str(result))
        else:
            unexpected.append(result)
    if unexpected:
        # A programming error keeps its traceback; the other tags' write
        # failures are attached so they are not lost from the report.
        if errors:
            unexpected[0].add_note("Other targets failed: " + "; ".join(errors))
        raise unexpected[0]
    if errors and not service.return_response:
        raise HomeAssistantError("; ".join(errors))
    if not service.return_response:
        return None
    return {device_id: outcome.as_response() for device_id, outcome in outcomes.items()}


# ── Write job ────────────────────────────────────────────────────────────


@dataclass
class WriteJob:
    """One rendered image bound for one tag, with the options in force."""

    data: BleEslRuntimeData
    """The entry's runtime data, captured rather than re-read from the entry:
    HA drops entry.runtime_data on unload while a background (debounced)
    write may still be finishing."""
    preset: DevicePreset
    image: Image.Image
    image_png: bytes
    max_retries: int
    prevent_duplicate_send: bool = False
    generation: int | None = None
    """Set for debounced writes; compared under the lock (see run_ble_write)."""
    prepared: Future[Any] | None = field(default=None, repr=False)
    """The encode future, started before queueing on the BLE lock."""

    @property
    def address(self) -> str:
        return self.data.address


async def build_write_job(
    hass: HomeAssistant, entry: BleEslConfigEntry, service: ServiceCall
) -> WriteJob:
    """Render the payload for `entry` and collect the write options.

    The BLE device handle is deliberately not resolved here: it is looked up
    right before each attempt in execute_write, so an unavailable tag goes
    through the same retry/failure path for both services and a debounced
    write never uses a stale handle.
    """
    data = entry.runtime_data
    options = {**entry.data, **entry.options}
    backend = data.backend

    preset = resolve_preset(
        hass, backend, data.address, options.get(CONF_MODEL, DEFAULT_MODEL)
    ).preset
    data.preset = preset
    data.parser.set_preset(preset)

    image = await hass.async_add_executor_job(
        partial(
            render_image,
            hass,
            preset,
            service.data.get("payload", ""),
            rotate=service.data.get("rotate", 0),
            background=service.data.get("background", "white"),
        )
    )
    buffer = BytesIO()
    image.save(buffer, "PNG")
    image_png = buffer.getvalue()
    data.preview_coordinator.async_set_updated_data(image_png)
    data.image_store.set_preview(image_png, now())

    return WriteJob(
        data=data,
        preset=preset,
        image=image,
        image_png=image_png,
        max_retries=int(options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)),
    )


# ── Execution ────────────────────────────────────────────────────────────


async def _update_duration_loop(data: BleEslRuntimeData) -> None:
    """Background task to update the duration sensor every second during a write."""
    while True:
        if data.start_time is not None:
            elapsed = round(time.monotonic() - data.start_time, 1)
            data.duration_coordinator.async_set_updated_data(elapsed)
        await asyncio.sleep(1)


def _transport(hass: HomeAssistant, address: str, scanner: Any) -> dict[str, str | int]:
    """Which radio the write went through, for the Write Duration attributes.

    `scanner` is what the backend saw on the client after connecting (newer
    habluetooth records it). When that is unavailable, the scanner holding
    the strongest advertisement is reported instead: it is the one the
    client wrapper tries first, so it is right except after a failover.
    """
    if not isinstance(scanner, BaseHaScanner):
        info = async_last_service_info(hass, address, connectable=True)
        scanner = async_scanner_by_source(hass, info.source) if info else None
        if scanner is None:
            return {}
    via: dict[str, str | int] = {
        "via": scanner.name,
        "via_type": "proxy" if isinstance(scanner, BaseHaRemoteScanner) else "adapter",
    }
    if seen := scanner.get_discovered_device_advertisement_data(address):
        via["rssi"] = seen[1].rssi
    # How many connectable radios currently see the tag: 1 means no failover.
    via["paths"] = len(async_scanner_devices_by_address(hass, address, connectable=True))
    return via


def _likely_cause(stage: str, error: str | None, via: dict[str, str | int], backend_id: str) -> str:
    """One sentence on what a failed attempt most likely means.

    Read from where it died (`stage`), the error text, the radio situation
    and the protocol, so the failure sensors can be understood without the
    code or the logs. Best effort — `error` keeps the exact detail.
    """
    err = (error or "").lower()
    no_reply = "no response" in err
    # Placement advice only when the signal is actually weak; a single
    # radio is the normal case and on its own says nothing about the cause.
    placement = ""
    rssi = via.get("rssi")
    if isinstance(rssi, int) and rssi <= -85:
        placement = f" The signal is weak ({rssi} dBm via {via.get('via')})"
        if via.get("paths") == 1:
            placement += " and no other radio reaches the tag"
        placement += " — move the tag or add a proxy."
    if stage == "unreachable":
        return (
            "No radio currently sees the tag: out of range, asleep, its battery flat, "
            "or the adapter / proxy is down."
        )
    if stage == "connect":
        if "slot" in err:
            return "The proxy has no free connection slot; add a proxy or reduce other BLE connections."
        return f"The BLE link could not be established.{placement}"
    if stage == "session":
        return (
            "Connected, but the tag dropped or refused the session before the protocol "
            "started (service discovery / notifications); usually transient — if it "
            "repeats, the protocol or model may not match this tag."
        )
    if stage == "handshake":
        if "probes" in err:
            return (
                "The tag did not answer START after connecting (not ready yet); usually transient."
            )
        if no_reply:
            return (
                f"The tag did not answer the handshake: not ready, or the link dropped.{placement}"
            )
        if "device error 5" in err:
            return "The tag rejected authentication: not a WOLINK tag, or different firmware."
        return "The tag answered the handshake unexpectedly; the protocol or model may not match."
    if stage == "transfer":
        if "stalled" in err:
            return f"The tag kept asking for the same part: a marginal link.{placement}"
        if no_reply:
            return f"The tag stopped answering mid-transfer: link dropped or tag reset.{placement}"
        if "unexpected" in err:
            return "Unexpected reply mid-transfer; the protocol or model may not match this tag."
        return f"The transfer failed: {error or 'unknown error'}.{placement}"
    # finish: what the tag was expected to say depends on the protocol.
    if "device error" in err:
        return f"The tag reported an error after the transfer: {error}."
    if backend_id == "xte":
        if no_reply:
            return f"The tag took the image but did not acknowledge the end command.{placement}"
        return f"The end of the transfer failed: {error or 'unknown error'}."
    if no_reply:
        return (
            "The tag took the image but did not report the refresh done in time: "
            "a slow panel (cold, large) or a tag-side error."
        )
    return f"The completion wait failed: {error or 'unknown error'}."


async def execute_write(hass: HomeAssistant, job: WriteJob) -> WriteOutcome:
    """Write with retries, tracking duration/connectivity and the result sensors.

    Returns the "written" outcome; raises WriteFailed after the last failed
    attempt (a HomeAssistantError carrying the "failed" outcome).
    """
    data = job.data
    address = job.address
    assert job.prepared is not None, "run_ble_write() schedules the encode"

    data.start_time = time.monotonic()
    data.duration_coordinator.async_set_updated_data(0.0)
    data.connectivity_coordinator.async_set_updated_data(True)
    duration_task = asyncio.create_task(_update_duration_loop(data))

    try:
        # Packets are paced more only after an attempt that failed *while
        # transferring*: that is what a marginal link looks like. A failure
        # to connect or to get through the handshake is retried at full speed.
        transfer_failures = 0
        for attempt in range(1, job.max_retries + 1):
            pacing_s = RETRY_BACKOFF_S * transfer_failures
            # Resolve the handle fresh each attempt: the one seen at service
            # call time may be stale after a debounce delay or a retry sleep.
            ble_device = async_ble_device_from_address(hass, address)
            if ble_device is None:
                result = WriteResult(
                    success=False,
                    error="BLE device handle is unavailable (out of range or adapter down)",
                )
            else:
                # The encode was started before the BLE lock was taken; the
                # backend awaits it once the link is up, and a retry awaits
                # the same future again instead of re-encoding.
                result = await data.backend.write_prepared(
                    ble_device,
                    job.preset,
                    job.prepared,
                    pacing_s=pacing_s,
                )
            # Every attempt is recorded (with whatever the backend timed) so the
            # Write Duration sensor's attributes always describe the last one.
            via = _transport(hass, address, result.scanner)
            failure: dict[str, str] = {}
            if not result.success and (stage := result.failed_stage):
                failure = {
                    "failed_stage": stage,
                    "likely_cause": _likely_cause(stage, result.error, via, data.backend.id),
                }
            timing = {
                **failure,
                **({"pacing_s": pacing_s} if pacing_s else {}),
                **via,
                **result.timing,
            }
            data.last_write_timing = {
                "attempt": attempt,
                "success": result.success,
                **({"error": result.error} if not result.success and result.error else {}),
                **timing,
            }
            _LOGGER.debug("Write to %s timing: %s", address, data.last_write_timing)
            if result.success:
                # Session-based protocols (e.g. easyTag) report battery/temp
                # in the write result; others update passively from adverts.
                if result.battery_mv is not None:
                    data.battery_coordinator.async_set_updated_data(result.battery_mv / 1000.0)
                if result.temperature_c is not None:
                    data.temperature_coordinator.async_set_updated_data(result.temperature_c)
                data.image_coordinator.async_set_updated_data(job.image_png)
                # Only a successful write counts for duplicate detection; a
                # failed or locked-out write must not suppress a retry of
                # the same payload.
                data.last_image_data = job.image_png
                data.image_store.set_written(job.image_png, now())
                return WriteOutcome(
                    "written",
                    attempts=attempt,
                    duration_s=round(time.monotonic() - data.start_time, 2),
                    timing=timing or None,
                )

            _LOGGER.warning(
                "Write failed to %s (attempt %d/%d): %s",
                address,
                attempt,
                job.max_retries,
                result.error,
            )
            if attempt < job.max_retries:
                transfer_failures += result.failed_in_transfer
                await sleep(1)
                continue

            data.failure_coordinator.async_set_updated_data(
                (data.failure_coordinator.data or 0) + 1
            )
            # Kept until the next failure; the timestamp update publishes it.
            # A copy, so nothing that later touches last_write_timing in
            # place can change the failure record.
            data.last_failure_timing = dict(data.last_write_timing or {})
            data.last_failure_coordinator.async_set_updated_data(now())
            raise WriteFailed(
                address,
                WriteOutcome(
                    "failed",
                    error=result.error or "unknown error",
                    attempts=attempt,
                    duration_s=round(time.monotonic() - data.start_time, 2),
                    timing=timing or None,
                ),
            )
    finally:
        duration_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await duration_task
        if data.start_time is not None:
            data.duration_coordinator.async_set_updated_data(
                round(time.monotonic() - data.start_time, 2)
            )
        data.start_time = None
        data.connectivity_coordinator.async_set_updated_data(False)


async def run_ble_write(hass: HomeAssistant, job: WriteJob) -> WriteOutcome:
    """Encode, then write under the BLE lock.

    The encode runs once per write, in HA's executor, *before* queueing on
    the lock: tags waiting their turn encode while another transfers, and
    the CPU-bound work never runs on the event loop. The backend awaits the
    future only once its link is up (overlapping connect), and every retry
    attempt reuses the same result.

    Checks that can change while waiting for the lock are repeated under it:
    the write lock, whether this debounced write has been superseded, and
    the duplicate guard (a write of the same payload may have just finished
    ahead of us, which is exactly the case the guard is for).
    """
    data = job.data
    address = job.address
    prepared = hass.async_add_executor_job(
        data.backend.prepare_image, job.preset, job.image, address
    )
    job.prepared = prepared
    try:
        async with hass.data[DATA_LOCK]:
            if data.write_lock:
                _LOGGER.info("Write lock active for %s — skipping BLE write", address)
                return WriteOutcome("locked")
            if job.generation is not None and job.generation != data.write_generation:
                _LOGGER.debug("Superseded debounced write for %s dropped", address)
                return WriteOutcome("dropped")
            if job.prevent_duplicate_send and job.image_png == data.last_image_data:
                _LOGGER.info("Skipping duplicate image for %s", address)
                return WriteOutcome("duplicate")
            return await execute_write(hass, job)
    finally:
        # Skipped or failed before the encode was awaited: drop it without
        # a "Future exception was never retrieved" warning.
        if not prepared.done():
            prepared.cancel()
        elif not prepared.cancelled():
            prepared.exception()


# ── Debounce ─────────────────────────────────────────────────────────────


@callback
def cancel_pending_write(data: BleEslRuntimeData) -> None:
    """Cancel a pending debounced write (new request or immediate path).

    Bumping the generation also invalidates a debounced write whose timer
    has already fired but which is still waiting for the BLE lock, so a
    cancelled payload is never sent after a newer one was requested.
    """
    data.write_generation += 1
    if data.pending_write_cancel is not None:
        data.pending_write_cancel()
        data.pending_write_cancel = None


@callback
def schedule_debounced_write(hass: HomeAssistant, job: WriteJob, delay_s: float) -> None:
    """(Re)schedule a write to run `delay_s` after this call.

    Any pending write for the entry is cancelled first, so repeated calls
    collapse into one write carrying the last payload, sent once requests
    have been quiet for the debounce delay (trailing edge). The write runs
    as a background task; the service call itself returns immediately.
    """
    data = job.data
    address = job.address
    cancel_pending_write(data)
    job.generation = data.write_generation

    async def _run() -> None:
        try:
            await run_ble_write(hass, job)
        except HomeAssistantError as err:
            # No service caller to propagate to; the failure sensors are
            # already updated by execute_write.
            _LOGGER.error("Debounced write to %s failed: %s", address, err)

    @callback
    def _fire(_now: datetime) -> None:
        data.pending_write_cancel = None
        hass.async_create_background_task(_run(), name=f"ble_esl debounced write {address}")

    data.pending_write_cancel = async_call_later(hass, delay_s, _fire)


# ── Service handlers ─────────────────────────────────────────────────────


async def _async_write(hass: HomeAssistant, service: ServiceCall) -> ServiceResponse:
    """ble_esl.write: always send (unless dry_run)."""
    dry_run = service.data.get("dry_run", False)

    async def handle(entry: BleEslConfigEntry) -> WriteOutcome:
        job = await build_write_job(hass, entry, service)
        if dry_run:
            return WriteOutcome("preview")
        cancel_pending_write(job.data)
        return await run_ble_write(hass, job)

    return await _for_each_target(hass, service, handle)


async def _async_write_guarded(hass: HomeAssistant, service: ServiceCall) -> ServiceResponse:
    """ble_esl.write_guarded: duplicate guard, write lock, debounce, then send."""
    dry_run = service.data.get("dry_run", False)

    async def handle(entry: BleEslConfigEntry) -> WriteOutcome:
        job = await build_write_job(hass, entry, service)
        data = job.data
        options = {**entry.data, **entry.options}
        job.prevent_duplicate_send = bool(
            options.get(CONF_PREVENT_DUPLICATE_SEND, DEFAULT_PREVENT_DUPLICATE_SEND)
        )

        if job.prevent_duplicate_send and job.image_png == data.last_image_data:
            _LOGGER.info("Skipping duplicate image for %s", job.address)
            return WriteOutcome("duplicate")
        if dry_run:
            # Preview only (README): leaves duplicate detection untouched.
            return WriteOutcome("preview")
        if data.write_lock:
            _LOGGER.info("Write lock active for %s — skipping BLE write", job.address)
            return WriteOutcome("locked")

        debounce_ms = int(
            service.data.get(
                "debounce_override_ms",
                options.get(CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS),
            )
        )
        if debounce_ms > 0:
            if data.pending_write_cancel is not None:
                _LOGGER.info(
                    "Cancelled pending write for %s, rescheduled with %dms delay",
                    job.address,
                    debounce_ms,
                )
            schedule_debounced_write(hass, job, debounce_ms / 1000.0)
            return WriteOutcome("scheduled", delay_ms=debounce_ms)
        cancel_pending_write(data)
        return await run_ble_write(hass, job)

    return await _for_each_target(hass, service, handle)
