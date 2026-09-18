"""Parser for WOLINK BLE advertisements."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sensor_state_data import BinarySensorDeviceClass, SensorLibrary

from ..base import DevicePreset, ProtocolParser
from .const import BRAND, MANUFACTURER_ID, SERVICE_UUID
from .protocol import battery_looks_plausible, parse_manufacturer_data

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)

# Battery % is a linear map of the advertised voltage over min-max, and at or
# below min the battery-low binary sensor turns on.
MIN_VOLTAGE = 2.2
MAX_VOLTAGE = 3.0


def is_wolink_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """Return True if advertisement matches WOLINK manufacturer data or service UUID."""
    if MANUFACTURER_ID in data.manufacturer_data:
        return True
    return SERVICE_UUID.lower() in {u.lower() for u in data.service_uuids}


class WolinkBluetoothDeviceData(ProtocolParser):
    """Data parser for WOLINK Bluetooth ESL devices."""

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
        """Return True if this advertisement is from a WOLINK device."""
        return is_wolink_advertisement(data)

    def _update_device_info(self, service_info: BluetoothServiceInfoBleak) -> None:
        identifier = service_info.address.replace(":", "")[-8:]
        display_name = self.preset.display_name if self.preset else "WOLINK"
        res = (
            f" {self.preset.width}x{self.preset.height}"
            if self.preset and f"{self.preset.width}x{self.preset.height}" not in display_name
            else ""
        )
        self.set_title(f"{identifier} ({display_name})")
        self.set_device_name(f"{BRAND} {identifier}")
        self.set_device_type(f"{display_name}{res}")
        self.set_device_manufacturer(BRAND)

    def _start_update(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Update from BLE advertisement data."""
        if not is_wolink_advertisement(service_info):
            return
        self.last_service_info = service_info
        self._update_device_info(service_info)

        mfr_bytes = service_info.manufacturer_data.get(MANUFACTURER_ID)
        if mfr_bytes and len(mfr_bytes) >= 10:
            try:
                info = parse_manufacturer_data(mfr_bytes)
                batt_mv = info["battery_mv"]
                if not battery_looks_plausible(batt_mv):
                    _LOGGER.warning(
                        "Battery read %d mV is out of plausible range (raw %s)",
                        batt_mv,
                        mfr_bytes[8:10].hex(),
                    )
                volts = batt_mv / 1000.0
                min_v, max_v = MIN_VOLTAGE, MAX_VOLTAGE
                pct = (volts - min_v) * 100.0 / (max_v - min_v)
                pct = max(0, min(100, round(pct)))
                self.update_predefined_sensor(
                    SensorLibrary.VOLTAGE__ELECTRIC_POTENTIAL_VOLT, volts
                )
                self.update_predefined_sensor(
                    SensorLibrary.BATTERY__PERCENTAGE, pct
                )
                self.update_predefined_binary_sensor(
                    BinarySensorDeviceClass.BATTERY, volts <= min_v
                )
                if info.get("app_ver") is not None:
                    self.set_device_sw_version(str(info["app_ver"]))
                if info.get("hw_ver") is not None:
                    self.set_device_hw_version(str(info["hw_ver"]))
            except Exception as err:
                _LOGGER.debug(
                    "Failed to parse WOLINK manufacturer data: %s", err
                )
