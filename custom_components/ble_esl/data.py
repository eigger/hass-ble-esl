"""Per-entry runtime state for the BLE ESL integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .esl_ble.base import BleBackend, BleParser, DevicePreset

if TYPE_CHECKING:
    from .coordinator import BleEslPassiveBluetoothProcessorCoordinator


@dataclass
class BleEslRuntimeData:
    """Everything a loaded config entry holds, attached as entry.runtime_data."""

    address: str
    backend: BleBackend
    preset: DevicePreset
    parser: BleParser
    device_id: str
    manufacturer: str
    model: str | None
    sw_version: str | None
    hw_version: str | None

    bt_coordinator: BleEslPassiveBluetoothProcessorCoordinator
    image_coordinator: DataUpdateCoordinator[bytes | None]
    preview_coordinator: DataUpdateCoordinator[bytes | None]
    connectivity_coordinator: DataUpdateCoordinator[bool]
    duration_coordinator: DataUpdateCoordinator[float]
    failure_coordinator: DataUpdateCoordinator[int]
    last_failure_coordinator: DataUpdateCoordinator[datetime | None]
    battery_coordinator: DataUpdateCoordinator[float | None]
    temperature_coordinator: DataUpdateCoordinator[int | None]

    # Write pipeline state (see services.py)
    write_lock: bool = False
    """Physical writes are skipped while set (the write-lock switch)."""
    start_time: float | None = None
    """monotonic() when the current BLE write started, for the duration sensor."""
    last_image_data: bytes | None = None
    """PNG of the last image successfully written, for Prevent Duplicate Send."""
    pending_write_cancel: CALLBACK_TYPE | None = None
    """Cancels the pending debounced write's timer, if one is scheduled."""
    write_generation: int = 0
    """Bumped whenever a pending write is cancelled; a debounced write that
    already fired but is still queued on the BLE lock is dropped if its
    generation no longer matches."""
    last_write_timing: dict[str, float | int | bool | str] | None = None
    """The most recent write attempt: attempt, success, error (if any) and the
    per-stage timings (see WriteResult.timing). Shown as the Write Duration
    sensor's attributes so it can be monitored without debug logging."""
    last_failure_timing: dict[str, float | int | bool | str] | None = None
    """The final attempt of the most recent *failed* write, in the same shape.
    Shown as the Last Failure Time sensor's attributes: a later successful
    write replaces last_write_timing but leaves this in place, so an
    intermittent failure can still be read after the fact."""

    @property
    def identifier(self) -> str:
        """Short tag id used in names and unique ids (last 8 hex digits of the address)."""
        return self.address.replace(":", "")[-8:]
