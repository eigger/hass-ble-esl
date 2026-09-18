"""Parser for easyTag BLE advertisements."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..base import DevicePreset, ProtocolParser
from .const import NAME_PREFIX, SERVICE_UUID

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)


def is_easytag_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """Return True if advertisement matches easyTag service UUID or name prefix."""
    if any(
        isinstance(u, str) and u.lower() == SERVICE_UUID.lower()
        for u in data.service_uuids
    ):
        return True
    if isinstance(data.name, str) and data.name.startswith(NAME_PREFIX):
        return True
    return False


class EasyTagBluetoothDeviceData(ProtocolParser):
    """Data parser for easyTag Bluetooth ESL devices."""

    def __init__(self, preset: DevicePreset | None = None) -> None:
        super().__init__()
        self.preset = preset
        self.last_service_info: BluetoothServiceInfoBleak | None = None

    def set_preset(self, preset: DevicePreset) -> None:
        """Update active device preset."""
        self.preset = preset
        if self.last_service_info is not None:
            self._update_device_info(self.last_service_info)

    def supported(self, data: BluetoothServiceInfoBleak) -> bool:
        """Return True if this advertisement is from an easyTag device."""
        return is_easytag_advertisement(data)

    def _update_device_info(self, service_info: BluetoothServiceInfoBleak) -> None:
        identifier = service_info.address.replace(":", "")[-8:]
        display_name = self.preset.display_name if self.preset else "easyTag"
        res = (
            f" {self.preset.width}x{self.preset.height}"
            if self.preset and f"{self.preset.width}x{self.preset.height}" not in display_name
            else ""
        )
        self.set_title(f"{identifier} ({display_name})")
        self.set_device_name(f"easyTag {identifier}")
        self.set_device_type(f"{display_name}{res}")
        self.set_device_manufacturer("easyTag")

    def _start_update(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Update from BLE advertisement data."""
        if not is_easytag_advertisement(service_info):
            return
        self.last_service_info = service_info
        self._update_device_info(service_info)
