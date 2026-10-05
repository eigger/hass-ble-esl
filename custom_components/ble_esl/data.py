"""Per-entry runtime state for the BLE ESL integration."""

from __future__ import annotations

from asyncio import Lock
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from blesession import SessionReports
from homeassistant.core import CALLBACK_TYPE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .esl_ble.base import BleParser, DevicePreset, EslProtocol

if TYPE_CHECKING:
    from .coordinator import BleEslPassiveBluetoothProcessorCoordinator
    from .storage import ImageStore


@dataclass
class BleEslRuntimeData:
    """Everything a loaded config entry holds, attached as entry.runtime_data."""

    address: str
    protocol: EslProtocol
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
    lifecycle_generation: int = 0
    """Bumped when the entry unloads so queued writes from this runtime are dropped."""
    request_generation: int = 0
    """Order of non-preview service writes, reserved before rendering begins."""
    reports: SessionReports = field(default_factory=SessionReports)
    """blesession's report slots and failure count, filled by services.execute_write.

    `last` is the most recent write *attempt* as blesession's report: outcome,
    where it failed and why, the radio, the per-stage timings (see
    services._report). Shown as the Write Duration sensor's attributes so the
    write path can be monitored without debug logging. An attempt a guard
    declined under the BLE lock is recorded too, as `skipped` (`locked` /
    `duplicate` / `dropped`) rather than an error, so "nothing was sent" is as
    readable as a failure.

    Every attempt is recorded, and blesession tells them apart by whether
    another attempt follows (`retrying`): a failed attempt a retry follows goes
    to `last_retry` only, so `last_failure`, `failures` and `last_failure_at`
    describe *writes* that failed with every retry exhausted — what the Last
    Failure Time sensor (state and attributes) and the Failure Count sensor
    show (services.track_reports publishes them). A later successful write
    replaces `last` but leaves `last_failure` in place, so an intermittent
    failure can still be read after the fact."""

    @property
    def label(self) -> str:
        """The id on the tag's label, for device names (unique ids use `identifier`)."""
        return self.protocol.tag_label(self.address)

    @property
    def identifier(self) -> str:
        """Short tag id used in names and unique ids (last 8 hex digits of the address)."""
        return self.address.replace(":", "")[-8:]
