"""The BLE ESL integration."""

from __future__ import annotations

import asyncio
from asyncio import Lock, sleep
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
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceRegistry,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import now
from sensor_state_data import SensorUpdate

from . import esl_ble
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

    # Create write debouncer
    debounce_ms = int(options.get(CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS))
    hass.data[DOMAIN][entry.entry_id]["write_debouncer"] = Debouncer(
        hass, _LOGGER, cooldown=debounce_ms / 1000.0, immediate=False
    )
    hass.data[DOMAIN][entry.entry_id]["write_pending"] = False

    connectivity_coordinator.async_set_updated_data(False)
    duration_coordinator.async_set_updated_data(0.0)
    failure_coordinator.async_set_updated_data(0)
    last_failure_coordinator.async_set_updated_data(None)
    battery_coordinator.async_set_updated_data(None)
    temperature_coordinator.async_set_updated_data(None)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def update_duration_loop(entry_id: str):
        """Background task to update duration every second."""
        while True:
            start_time = hass.data[DOMAIN][entry_id].get("start_time")
            if start_time is not None:
                elapsed = round(time.monotonic() - start_time, 1)
                hass.data[DOMAIN][entry_id][
                    "duration_coordinator"
                ].async_set_updated_data(elapsed)
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
        service: ServiceCall, entry_id: str, require_ble_device: bool
    ) -> dict[str, Any] | None:
        """Build shared write context for write services."""
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
        ble_device = async_ble_device_from_address(hass, address)

        if require_ble_device and ble_device is None:
            _LOGGER.error(
                "Cannot write to %s: BLE device handle is unavailable. Please check power/range and Bluetooth adapter state.",
                address,
            )
            return None

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
            "ble_device": ble_device,
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
        ble_device = context["ble_device"]
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

            # Update final elapsed time
            start_time = hass.data[DOMAIN][entry_id].get("start_time")
            if start_time is not None:
                elapsed_time = round(time.monotonic() - start_time, 2)
                dur_coord.async_set_updated_data(elapsed_time)

            hass.data[DOMAIN][entry_id]["start_time"] = None
            hass.data[DOMAIN][entry_id]["duration_task"] = None
            conn_coord.async_set_updated_data(False)

    def cancel_pending_write(entry_id: str) -> None:
        """Cancel pending debounced write for immediate execution paths."""
        if not hass.data[DOMAIN][entry_id].get("write_pending"):
            return
        debouncer = hass.data[DOMAIN][entry_id]["write_debouncer"]
        debouncer.async_cancel()
        hass.data[DOMAIN][entry_id]["write_pending"] = False

    async def run_ble_write(
        entry_id: str,
        address: str,
        image_coordinator: DataUpdateCoordinator[bytes],
        current_image_data: bytes,
        context: dict[str, Any],
    ) -> None:
        """Run BLE write under lock with final write-lock check."""
        async with hass.data[DOMAIN][LOCK]:
            hass.data[DOMAIN][entry_id]["write_pending"] = False
            if hass.data[DOMAIN][entry_id].get(WRITE_LOCK, False):
                _LOGGER.info(
                    "Write lock active for %s — skipping BLE write", address
                )
                return
            await execute_write_core(context)

    # Handler for the write custom service
    async def writeservice(service: ServiceCall) -> None:
        device_ids = normalize_device_ids(service)
        dry_run = service.data.get("dry_run", False)

        for device_id in device_ids:
            entry_id = await get_entry_id_from_device(hass, device_id)
            context = await build_write_context(
                service, entry_id, require_ble_device=False
            )
            if context is None:
                continue

            address = context["address"]
            image_coord = context["image_coordinator"]
            current_image_data = context["current_image_data"]
            hass.data[DOMAIN][entry_id]["last_image_data"] = (
                current_image_data
            )

            if dry_run:
                continue

            cancel_pending_write(entry_id)
            await run_ble_write(
                entry_id,
                address,
                image_coord,
                current_image_data,
                context,
            )

    # Handler for the guarded write service
    async def writeguardedservice(service: ServiceCall) -> None:
        device_ids = normalize_device_ids(service)
        dry_run = service.data.get("dry_run", False)

        for device_id in device_ids:
            entry_id = await get_entry_id_from_device(hass, device_id)
            context = await build_write_context(
                service, entry_id, require_ble_device=True
            )
            if context is None:
                continue

            current_options = context["options"]
            address = context["address"]
            image_coord = context["image_coordinator"]
            current_image_data = context["current_image_data"]
            last_image_data = hass.data[DOMAIN][entry_id].get("last_image_data")
            prevent_duplicate_send = current_options.get(
                CONF_PREVENT_DUPLICATE_SEND, DEFAULT_PREVENT_DUPLICATE_SEND
            )

            if (
                prevent_duplicate_send
                and current_image_data == last_image_data
            ):
                _LOGGER.info("Skipping duplicate image for %s", address)
                continue

            hass.data[DOMAIN][entry_id]["last_image_data"] = (
                current_image_data
            )

            if dry_run:
                continue

            if hass.data[DOMAIN][entry_id].get(WRITE_LOCK, False):
                _LOGGER.info(
                    "Write lock active for %s — skipping BLE write", address
                )
                continue

            debounce_ms = int(
                service.data.get(
                    "debounce_override_ms",
                    current_options.get(
                        CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS
                    ),
                )
            )

            debouncer = hass.data[DOMAIN][entry_id]["write_debouncer"]
            if debounce_ms > 0:
                new_cooldown = debounce_ms / 1000.0
                if debouncer.cooldown != new_cooldown:
                    debouncer.cooldown = new_cooldown
                had_pending = hass.data[DOMAIN][entry_id]["write_pending"]
                hass.data[DOMAIN][entry_id]["write_pending"] = True
                if had_pending:
                    _LOGGER.info(
                        "Cancelled pending write for %s, rescheduled with %dms delay",
                        address,
                        debounce_ms,
                    )
                debouncer.function = partial(
                    run_ble_write,
                    entry_id,
                    address,
                    image_coord,
                    current_image_data,
                    context,
                )
                debouncer.async_schedule_call()
            else:
                cancel_pending_write(entry_id)
                await run_ble_write(
                    entry_id,
                    address,
                    image_coord,
                    current_image_data,
                    context,
                )

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
        if write_debouncer := hass.data[DOMAIN][entry.entry_id].get(
            "write_debouncer"
        ):
            write_debouncer.async_shutdown()

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
