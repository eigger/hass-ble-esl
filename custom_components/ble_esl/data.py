"""Per-entry runtime state for the BLE ESL integration."""

from __future__ import annotations

from asyncio import Lock
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from blesession import SessionReports
from homeassistant.core import CALLBACK_TYPE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .esl_ble.base import BleBackend, BleParser, DevicePreset

if TYPE_CHECKING:
    from .coordinator import BleEslPassiveBluetoothProcessorCoordinator
    from .storage import ImageStore


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
    image_store: ImageStore
    """The last written and last rendered PNG, persisted across restarts.
    Seeds image_coordinator / preview_coordinator / last_image_data on load."""

    # Write pipeline state (see services.py)
    write_serial: Lock = field(default_factory=Lock)
    """Held for a whole write (all its attempts) so two writes to this tag
    never interleave; the domain-wide BLE lock is taken per attempt."""
    write_lock: bool = False
    """Physical writes are skipped while set (the write-lock switch)."""
    start_time: float | None = None
    """monotonic() when the current BLE write started, for the duration sensor."""
    last_image_data: bytes | None = None
    """PNG of the last image successfully written, for Prevent Duplicate Send.
    Restored from image_store on load, so a restart does not rewrite every tag."""
    pending_write_cancel: CALLBACK_TYPE | None = None
    """Cancels the pending debounced write's timer, if one is scheduled."""
    write_generation: int = 0
    """Bumped whenever a pending write is cancelled; a debounced write that
    already fired but is still queued on the BLE lock is dropped if its
    generation no longer matches."""
    reports: SessionReports = field(default_factory=SessionReports)
    """blesession's two report slots, filled by services.execute_write.

    `last` is the most recent write *attempt* as blesession's report: outcome,
    where it failed and why, the radio, the per-stage timings (see
    services._report). Shown as the Write Duration sensor's attributes so the
    write path can be monitored without debug logging. An attempt a guard
    declined under the BLE lock is recorded too, as `skipped` (`locked` /
    `duplicate` / `dropped`) rather than an error, so "nothing was sent" is as
    readable as a failure.

    `last_failure` is the final attempt of the most recent failed *write* —
    every retry exhausted — shown as the Last Failure Time sensor's
    attributes. A later successful write replaces `last` but leaves it in
    place, so an intermittent failure can still be read after the fact.

    Per write rather than per attempt: that is what the Last Failure Time
    timestamp and the Failure Count sensor beside it count, so recording an
    attempt that a later retry recovered from would leave the attributes
    describing a different event than the state. blesession's own
    `SessionReports` docstring calls this the case for filing the attempt
    `run_attempts()` returns instead of every one."""

    @property
    def identifier(self) -> str:
        """Short tag id used in names and unique ids (last 8 hex digits of the address)."""
        return self.address.replace(":", "")[-8:]
