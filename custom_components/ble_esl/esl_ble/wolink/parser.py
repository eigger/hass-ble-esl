"""Parser for WOLINK BLE advertisements."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, MANUFACTURER_ID, SERVICE_UUID
from .devices import preset_for_advertisement
from .protocol import battery_looks_plausible, parse_manufacturer_data

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)
_unknown_reported: set[str] = set()


def is_wolink_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """Return True if advertisement matches WOLINK manufacturer data or service UUID."""
    mfr_bytes = data.manufacturer_data.get(MANUFACTURER_ID)
    if mfr_bytes is not None:
        if (
            len(mfr_bytes) >= 10
            and preset_for_advertisement(mfr_bytes) is None
            and data.address not in _unknown_reported
        ):
            _unknown_reported.add(data.address)
            _LOGGER.info(
                "WOLINK tag %s has an unknown display version (manufacturer data %s): "
                "select its model manually, and open an issue with this line and the "
                "tag's model and resolution.",
                data.address,
                mfr_bytes.hex(),
            )
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
        self.update_battery(batt_mv / 1000.0)
        if info.get("app_ver") is not None:
            self.set_device_sw_version(str(info["app_ver"]))
        if info.get("hw_ver") is not None:
            self.set_device_hw_version(str(info["hw_ver"]))
