"""The BLE ESL integration."""

from __future__ import annotations

import asyncio
from asyncio import Lock, sleep
from collections.abc import Awaitable, Callable
from datetime import datetime
from functools import partial
from io import BytesIO
import logging
import time
from typing import Any

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_last_service_info,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceRegistry,
)
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import now
from sensor_state_data import SensorUpdate

from . import esl_ble
from .esl_ble import WriteResult
from .const import (
    CONF_DEBOUNCE_MS,
    CONF_MODEL,
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_PROTOCOL,
    CONF_RETRY_COUNT,
    CONF_WRITE_DELAY_MS,
    DEFAULT_DEBOUNCE_MS,
    DEFAULT_MODEL,
    DEFAULT_PREVENT_DUPLICATE_SEND,
    DEFAULT_PROTOCOL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_WRITE_DELAY_MS,
    DOMAIN,
    LOCK,
    WRITE_LOCK,
)
from .coordinator import BleEslPassiveBluetoothProcessorCoordinator
from .device import backend_brand, format_model_name, protocol_label
from .renderer import render_image
from .types import BleEslConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.IMAGE,
    Platform.TEXT,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)


def process_service_info(
    hass: HomeAssistant,
    entry: BleEslConfigEntry,
    device_registry: DeviceRegistry,
    service_info: BluetoothServiceInfoBleak,
) -> SensorUpdate:
    """Process a BluetoothServiceInfoBleak, running side effects and returning sensor data."""
    coordinator = entry.runtime_data
    data = coordinator.device_data
    update = data.update(service_info)

    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data:
        backend = entry_data.get("backend")
        current_preset = entry_data.get("preset")
        if backend and current_preset:
            adv_info = backend.parse_advertisement(service_info)
            if adv_info:
                refined_preset = backend.refine_preset(current_preset, adv_info)
                entry_data["preset"] = refined_preset
                data.set_preset(refined_preset)

                manufacturer = backend_brand(backend)
                model = format_model_name(refined_preset)

                device_id = entry_data.get("device_id")
                if device_id:
                    update_kwargs: dict[str, Any] = {}
                    if adv_info.sw_version and adv_info.sw_version != entry_data.get("sw_version"):
                        entry_data["sw_version"] = adv_info.sw_version
                        update_kwargs["sw_version"] = adv_info.sw_version
                    if adv_info.hw_version and adv_info.hw_version != entry_data.get("hw_version"):
                        entry_data["hw_version"] = adv_info.hw_version
                        update_kwargs["hw_version"] = adv_info.hw_version
                    if model != entry_data.get("model"):
                        entry_data["model"] = model
                        update_kwargs["model"] = model
                    if manufacturer != entry_data.get("manufacturer"):
                        entry_data["manufacturer"] = manufacturer
                        update_kwargs["manufacturer"] = manufacturer
                    if update_kwargs:
                        device_registry.async_update_device(
                            device_id,
                            **update_kwargs,
                        )

    return update


async def async_setup_entry(
    hass: HomeAssistant, entry: BleEslConfigEntry
) -> bool:
    """Set up a BLE ESL device from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    address = entry.unique_id
    assert address is not None

    options = {**entry.data, **entry.options}
    protocol_id = options.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
    backend = esl_ble.get(protocol_id)
    model_key = options.get(CONF_MODEL, DEFAULT_MODEL)
    preset = backend.presets().get(model_key)
    if preset is None:
        preset = next(iter(backend.presets().values()))

    adv_info = None
    service_info = async_last_service_info(hass, address, connectable=True)
    if service_info:
        adv_info = backend.parse_advertisement(service_info)
        preset = backend.refine_preset(preset, adv_info)

    data = backend.create_parser(preset=preset)
    if service_info:
        data.update(service_info)

    sw_version = adv_info.sw_version if adv_info else None
    hw_version = adv_info.hw_version if adv_info else None
    protocol_name = protocol_label(backend)
    manufacturer = backend_brand(backend)
    model = format_model_name(preset)

    hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]["address"] = address
    hass.data[DOMAIN][entry.entry_id]["data"] = data
    hass.data[DOMAIN][entry.entry_id]["backend"] = backend
    hass.data[DOMAIN][entry.entry_id]["preset"] = preset
    hass.data[DOMAIN][entry.entry_id]["sw_version"] = sw_version
    hass.data[DOMAIN][entry.entry_id]["hw_version"] = hw_version
    hass.data[DOMAIN][entry.entry_id]["model"] = model
    hass.data[DOMAIN][entry.entry_id]["manufacturer"] = manufacturer

    if LOCK not in hass.data[DOMAIN]:
        hass.data[DOMAIN][LOCK] = Lock()

    device_registry = dr.async_get(hass)
    _identifier = address.replace(":", "")[-8:]
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(CONNECTION_BLUETOOTH, address)},
        manufacturer=manufacturer,
        name=f"{manufacturer} {_identifier}",
        model=model,
        model_id=protocol_name,
        sw_version=sw_version,
        hw_version=hw_version,
    )
    hass.data[DOMAIN][entry.entry_id]["device_id"] = device_entry.id
    bt_coordinator = BleEslPassiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=partial(
            process_service_info, hass, entry, device_registry
        ),
        device_data=data,
        connectable=True,
        entry=entry,
    )

    image_coordinator: DataUpdateCoordinator[bytes] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
    )
    preview_coordinator: DataUpdateCoordinator[bytes] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
    )
    connectivity_coordinator: DataUpdateCoordinator[bool] = (
        DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
    )
    duration_coordinator: DataUpdateCoordinator[float] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
    )
    failure_coordinator: DataUpdateCoordinator[int] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
    )
    last_failure_coordinator: DataUpdateCoordinator[datetime | None] = (
        DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
    )
    battery_coordinator: DataUpdateCoordinator[float | None] = (
        DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
    )
    temperature_coordinator: DataUpdateCoordinator[int | None] = (
        DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
    )

    entry.runtime_data = bt_coordinator
    hass.data[DOMAIN][entry.entry_id]["image_coordinator"] = image_coordinator
    hass.data[DOMAIN][entry.entry_id]["preview_coordinator"] = (
        preview_coordinator
    )
    hass.data[DOMAIN][entry.entry_id]["connectivity_coordinator"] = (
        connectivity_coordinator
    )
    hass.data[DOMAIN][entry.entry_id]["duration_coordinator"] = (
        duration_coordinator
    )
    hass.data[DOMAIN][entry.entry_id]["failure_coordinator"] = (
        failure_coordinator
    )
    hass.data[DOMAIN][entry.entry_id]["last_failure_coordinator"] = (
        last_failure_coordinator
    )
    hass.data[DOMAIN][entry.entry_id]["battery_coordinator"] = (
        battery_coordinator
    )
    hass.data[DOMAIN][entry.entry_id]["temperature_coordinator"] = (
        temperature_coordinator
    )
    hass.data[DOMAIN][entry.entry_id]["duration_task"] = None
    hass.data[DOMAIN][entry.entry_id]["start_time"] = None
    hass.data[DOMAIN][entry.entry_id]["last_image_data"] = None

    # Trailing-edge debounce for write_guarded: a cancel callback for the
    # pending timer, replaced (cancelled + rescheduled) on every new call so the
    # write fires `debounce_ms` after the *last* request with its payload.
    # HA's Debouncer is not used because it neither restarts its timer nor
    # keeps a call that arrives while a previous one is still executing.
    # `write_generation` invalidates an already-fired write that is still
    # queued on the BLE lock when a newer request cancels it.
    hass.data[DOMAIN][entry.entry_id]["pending_write_cancel"] = None
    hass.data[DOMAIN][entry.entry_id]["write_generation"] = 0

    connectivity_coordinator.async_set_updated_data(False)
    duration_coordinator.async_set_updated_data(0.0)
    failure_coordinator.async_set_updated_data(0)
    last_failure_coordinator.async_set_updated_data(None)
    battery_coordinator.async_set_updated_data(None)
    temperature_coordinator.async_set_updated_data(None)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def update_duration_loop(entry_id: str):
        """Background task to update duration every second."""
        while (entry_data := hass.data[DOMAIN].get(entry_id)) is not None:
            start_time = entry_data.get("start_time")
            if start_time is not None:
                elapsed = round(time.monotonic() - start_time, 1)
                entry_data["duration_coordinator"].async_set_updated_data(elapsed)
            await asyncio.sleep(1)

    def normalize_device_ids(service: ServiceCall) -> list[str]:
        """Normalize service device_id payload into a list."""
        device_ids = service.data.get("device_id")
        if isinstance(device_ids, str):
            return [device_ids]
        if device_ids is None:
            return []
        return device_ids

    async def build_write_context(
        service: ServiceCall, entry_id: str
    ) -> dict[str, Any]:
        """Build shared write context for write services.

        The BLE device handle is deliberately not resolved here: it is looked
        up right before each attempt in execute_write_core, so an unavailable
        tag goes through the same retry/failure path for both services and a
        debounced write never uses a stale handle.
        """
        config_entry = hass.config_entries.async_get_entry(entry_id)
        current_options = {**config_entry.data, **config_entry.options}
        max_retries = int(
            current_options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)
        )
        write_delay_ms = int(
            current_options.get(CONF_WRITE_DELAY_MS, DEFAULT_WRITE_DELAY_MS)
        )
        current_protocol = current_options.get(
            CONF_PROTOCOL, DEFAULT_PROTOCOL
        )
        current_model = current_options.get(CONF_MODEL, DEFAULT_MODEL)

        address = hass.data[DOMAIN][entry_id]["address"]
        backend = esl_ble.get(current_protocol)
        preset = backend.presets().get(current_model)
        if preset is None:
            preset = next(iter(backend.presets().values()))

        service_info = async_last_service_info(hass, address, connectable=True)
        if service_info:
            adv_info = backend.parse_advertisement(service_info)
            preset = backend.refine_preset(preset, adv_info)

        hass.data[DOMAIN][entry_id]["preset"] = preset
        current_data = hass.data[DOMAIN][entry_id]["data"]
        current_data.set_preset(preset)

        image_coord = hass.data[DOMAIN][entry_id]["image_coordinator"]
        preview_coord = hass.data[DOMAIN][entry_id]["preview_coordinator"]
        conn_coord = hass.data[DOMAIN][entry_id]["connectivity_coordinator"]
        dur_coord = hass.data[DOMAIN][entry_id]["duration_coordinator"]
        fail_coord = hass.data[DOMAIN][entry_id]["failure_coordinator"]
        last_fail_coord = hass.data[DOMAIN][entry_id][
            "last_failure_coordinator"
        ]
        batt_coord = hass.data[DOMAIN][entry_id]["battery_coordinator"]
        temp_coord = hass.data[DOMAIN][entry_id]["temperature_coordinator"]

        image = await hass.async_add_executor_job(
            render_image, entry_id, preset, service, hass
        )
        image_bytes = BytesIO()
        image.save(image_bytes, "PNG")
        current_image_data = image_bytes.getvalue()
        preview_coord.async_set_updated_data(current_image_data)

        return {
            "entry_id": entry_id,
            "options": current_options,
            "address": address,
            "backend": backend,
            "preset": preset,
            "data": current_data,
            "image_coordinator": image_coord,
            "connectivity_coordinator": conn_coord,
            "duration_coordinator": dur_coord,
            "failure_coordinator": fail_coord,
            "last_failure_coordinator": last_fail_coord,
            "battery_coordinator": batt_coord,
            "temperature_coordinator": temp_coord,
            "image": image,
            "current_image_data": current_image_data,
            "max_retries": max_retries,
            "write_delay_ms": write_delay_ms,
        }

    async def execute_write_core(context: dict[str, Any]) -> None:
        """Execute BLE write with retry, duration tracking, and battery/temperature update."""
        entry_id = context["entry_id"]
        address = context["address"]
        backend = context["backend"]
        preset = context["preset"]
        image_coord = context["image_coordinator"]
        conn_coord = context["connectivity_coordinator"]
        dur_coord = context["duration_coordinator"]
        fail_coord = context["failure_coordinator"]
        last_fail_coord = context["last_failure_coordinator"]
        batt_coord = context["battery_coordinator"]
        temp_coord = context["temperature_coordinator"]
        image = context["image"]
        current_image_data = context["current_image_data"]
        max_retries = context["max_retries"]
        write_delay_ms = context["write_delay_ms"]

        # Start duration tracking
        hass.data[DOMAIN][entry_id]["start_time"] = time.monotonic()
        dur_coord.async_set_updated_data(0.0)
        conn_coord.async_set_updated_data(True)
        duration_task = asyncio.create_task(update_duration_loop(entry_id))
        hass.data[DOMAIN][entry_id]["duration_task"] = duration_task

        try:
            for attempt in range(1, max_retries + 1):
                # Resolve the handle fresh each attempt: the one seen at service
                # call time may be stale after a debounce delay or a retry sleep.
                ble_device = async_ble_device_from_address(hass, address)
                if ble_device is None:
                    result = WriteResult(
                        success=False,
                        error="BLE device handle is unavailable (out of range or adapter down)",
                    )
                else:
                    result = await backend.write_image(
                        ble_device,
                        preset,
                        image,
                        attempt=attempt,
                        write_delay_ms=write_delay_ms,
                    )
                if result.success:
                    # For session-based protocols (e.g. easyTag), write result provides battery/temp.
                    # For WOLINK, battery is passively updated via 0xBBAA advertisement broadcasts.
                    if result.battery_mv is not None:
                        batt_coord.async_set_updated_data(
                            result.battery_mv / 1000.0
                        )
                    if result.temperature_c is not None:
                        temp_coord.async_set_updated_data(
                            result.temperature_c
                        )
                    image_coord.async_set_updated_data(current_image_data)
                    # Only a successful write counts for duplicate detection;
                    # a failed or locked-out write must not suppress a retry
                    # of the same payload.
                    if entry_id in hass.data[DOMAIN]:
                        hass.data[DOMAIN][entry_id]["last_image_data"] = (
                            current_image_data
                        )
                    return

                _LOGGER.warning(
                    "Write failed to %s (attempt %d/%d): %s",
                    address,
                    attempt,
                    max_retries,
                    result.error,
                )
                if attempt < max_retries:
                    await sleep(1)
                    continue

                current_count = fail_coord.data if fail_coord.data else 0
                fail_coord.async_set_updated_data(current_count + 1)
                last_fail_coord.async_set_updated_data(now())
                raise HomeAssistantError(
                    f"Failed to write to {address} after {max_retries} attempts: {result.error}"
                )
        finally:
            # Stop duration tracking
            duration_task.cancel()
            try:
                await duration_task
            except asyncio.CancelledError:
                pass

            # Update final elapsed time. The entry may have been unloaded
            # while a debounced write was in flight; then only the (orphaned)
            # coordinators from the context are left to update.
            if entry_data := hass.data[DOMAIN].get(entry_id):
                start_time = entry_data.get("start_time")
                if start_time is not None:
                    elapsed_time = round(time.monotonic() - start_time, 2)
                    dur_coord.async_set_updated_data(elapsed_time)
                entry_data["start_time"] = None
                entry_data["duration_task"] = None
            conn_coord.async_set_updated_data(False)

    def cancel_pending_write(entry_id: str) -> None:
        """Cancel a pending debounced write (new request or immediate path).

        Bumping the generation also invalidates a debounced write whose timer
        has already fired but which is still waiting for the BLE lock, so a
        cancelled payload is never sent after a newer one was requested.
        """
        entry_data = hass.data[DOMAIN][entry_id]
        entry_data["write_generation"] += 1
        if cancel := entry_data.get("pending_write_cancel"):
            cancel()
            entry_data["pending_write_cancel"] = None

    async def run_ble_write(context: dict[str, Any]) -> None:
        """Run BLE write under the BLE lock.

        Checks that can change while waiting for the lock are repeated here:
        the write lock, whether this debounced write has been superseded, and
        the duplicate guard (a write of the same payload may have just
        finished ahead of us, which is exactly the case the guard is for).
        """
        entry_id = context["entry_id"]
        address = context["address"]
        async with hass.data[DOMAIN][LOCK]:
            entry_data = hass.data[DOMAIN].get(entry_id)
            if entry_data is None:
                return  # entry unloaded while waiting for the lock
            if entry_data.get(WRITE_LOCK, False):
                _LOGGER.info(
                    "Write lock active for %s — skipping BLE write", address
                )
                return
            generation = context.get("generation")
            if generation is not None and generation != entry_data["write_generation"]:
                _LOGGER.debug("Superseded debounced write for %s dropped", address)
                return
            if (
                context.get("prevent_duplicate_send")
                and context["current_image_data"] == entry_data.get("last_image_data")
            ):
                _LOGGER.info("Skipping duplicate image for %s", address)
                return
            await execute_write_core(context)

    def schedule_debounced_write(context: dict[str, Any], delay_s: float) -> None:
        """(Re)schedule a write to run `delay_s` after this call.

        Any pending write for the entry is cancelled first, so repeated calls
        collapse into one write carrying the last payload, sent once requests
        have been quiet for the debounce delay (trailing edge). The write runs
        as a background task; the service call itself returns immediately.
        """
        entry_id = context["entry_id"]
        address = context["address"]
        entry_data = hass.data[DOMAIN][entry_id]
        cancel_pending_write(entry_id)
        context["generation"] = entry_data["write_generation"]

        async def _run() -> None:
            try:
                await run_ble_write(context)
            except HomeAssistantError as err:
                # No service caller to propagate to; the failure sensors are
                # already updated by execute_write_core.
                _LOGGER.error("Debounced write to %s failed: %s", address, err)

        @callback
        def _fire(_now: datetime) -> None:
            entry_data["pending_write_cancel"] = None
            hass.async_create_background_task(
                _run(), name=f"ble_esl debounced write {address}"
            )

        entry_data["pending_write_cancel"] = async_call_later(hass, delay_s, _fire)

    async def for_each_target(
        service: ServiceCall,
        handler: Callable[[str], Awaitable[None]],
    ) -> None:
        """Run handler per targeted device, continuing past per-device failures.

        Errors are collected and raised together at the end so one unreachable
        tag does not prevent the remaining targets from being written.
        """
        errors: list[str] = []
        for device_id in normalize_device_ids(service):
            try:
                entry_id = await get_entry_id_from_device(hass, device_id)
                await handler(entry_id)
            except (HomeAssistantError, ValueError) as err:
                errors.append(str(err))
        if errors:
            raise HomeAssistantError("; ".join(errors))

    # Handler for the write custom service
    async def writeservice(service: ServiceCall) -> None:
        dry_run = service.data.get("dry_run", False)

        async def handle(entry_id: str) -> None:
            context = await build_write_context(service, entry_id)
            if dry_run:
                return

            cancel_pending_write(entry_id)
            await run_ble_write(context)

        await for_each_target(service, handle)

    # Handler for the guarded write service
    async def writeguardedservice(service: ServiceCall) -> None:
        dry_run = service.data.get("dry_run", False)

        async def handle(entry_id: str) -> None:
            context = await build_write_context(service, entry_id)
            current_options = context["options"]
            address = context["address"]
            current_image_data = context["current_image_data"]
            last_image_data = hass.data[DOMAIN][entry_id].get("last_image_data")
            prevent_duplicate_send = current_options.get(
                CONF_PREVENT_DUPLICATE_SEND, DEFAULT_PREVENT_DUPLICATE_SEND
            )

            context["prevent_duplicate_send"] = prevent_duplicate_send
            if (
                prevent_duplicate_send
                and current_image_data == last_image_data
            ):
                _LOGGER.info("Skipping duplicate image for %s", address)
                return

            if dry_run:
                # Preview only (README): leaves duplicate detection untouched.
                return

            if hass.data[DOMAIN][entry_id].get(WRITE_LOCK, False):
                _LOGGER.info(
                    "Write lock active for %s — skipping BLE write", address
                )
                return

            debounce_ms = int(
                service.data.get(
                    "debounce_override_ms",
                    current_options.get(
                        CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS
                    ),
                )
            )

            if debounce_ms > 0:
                if hass.data[DOMAIN][entry_id].get("pending_write_cancel"):
                    _LOGGER.info(
                        "Cancelled pending write for %s, rescheduled with %dms delay",
                        address,
                        debounce_ms,
                    )
                schedule_debounced_write(context, debounce_ms / 1000.0)
            else:
                cancel_pending_write(entry_id)
                await run_ble_write(context)

        await for_each_target(service, handle)

    # Register the services
    hass.services.async_register(DOMAIN, "write", writeservice)
    hass.services.async_register(DOMAIN, "write_guarded", writeguardedservice)

    entry.async_on_unload(bt_coordinator.async_start())
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BleEslConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if not unload_ok:
        return False

    if entry.entry_id in hass.data.get(DOMAIN, {}):
        if cancel := hass.data[DOMAIN][entry.entry_id].get(
            "pending_write_cancel"
        ):
            cancel()

    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if len(hass.config_entries.async_entries(DOMAIN)) == 1:
        hass.services.async_remove(DOMAIN, "write")
        hass.services.async_remove(DOMAIN, "write_guarded")

    return unload_ok


async def get_entry_id_from_device(hass: HomeAssistant, device_id: str) -> str:
    """Resolve HA device_id to config entry_id by scanning hass.data[DOMAIN] only."""
    domain_data = hass.data.get(DOMAIN, {})
    for entry_id, rt in domain_data.items():
        if entry_id == LOCK:
            continue
        if not isinstance(rt, dict) or "address" not in rt:
            continue
        if rt.get("device_id") == device_id:
            _LOGGER.debug("device %s -> entry %s", device_id, entry_id)
            return entry_id

    raise ValueError(
        f"No loaded BLE ESL entry has device_id {device_id!r} in hass.data['{DOMAIN}']. "
        "Reload the integration after updating, or target the correct device."
    )
