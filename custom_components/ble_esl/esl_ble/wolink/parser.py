"""Parser for WOLINK BLE advertisements."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..base import BleParser
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


class WolinkBluetoothDeviceData(BleParser):
    """Data parser for WOLINK Bluetooth ESL devices."""

    brand = BRAND
    fallback_name = "WOLINK"
    is_advertisement = staticmethod(is_wolink_advertisement)

    def _parse(self, service_info: BluetoothServiceInfoBleak) -> None:
        mfr_bytes = service_info.manufacturer_data.get(MANUFACTURER_ID)
        if not mfr_bytes or len(mfr_bytes) < 10:
            return
        try:
            info = parse_manufacturer_data(mfr_bytes)
        except Exception as err:
            _LOGGER.debug("Failed to parse WOLINK manufacturer data: %s", err)
            return

        batt_mv = info["battery_mv"]
        if not battery_looks_plausible(batt_mv):
            _LOGGER.warning(
                "Battery read %d mV is out of plausible range (raw %s)",
                batt_mv,
                mfr_bytes[8:10].hex(),
            )
        self.update_battery(batt_mv / 1000.0, MIN_VOLTAGE, MAX_VOLTAGE)
        if info.get("app_ver") is not None:
            self.set_device_sw_version(str(info["app_ver"]))
        if info.get("hw_ver") is not None:
            self.set_device_hw_version(str(info["hw_ver"]))
