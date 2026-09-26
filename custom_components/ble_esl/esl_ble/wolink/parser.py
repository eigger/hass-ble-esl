"""WOLINK advertisement parser: battery and versions for the device page."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, MANUFACTURER_ID, SERVICE_UUID
from .protocol import battery_plausible, parse_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)


def is_wolink_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """WOLINK manufacturer data, or the WOLINK service UUID."""
    if MANUFACTURER_ID in data.manufacturer_data:
        return True
    return SERVICE_UUID in {uuid.lower() for uuid in data.service_uuids}


class WolinkBluetoothDeviceData(BleParser):
    """Sensor data from WOLINK advertisements."""

    brand = BRAND
    fallback_name = "WOLINK"
    is_advertisement = staticmethod(is_wolink_advertisement)

    def _parse(self, service_info: BluetoothServiceInfoBleak) -> None:
        advertisement = parse_advertisement(service_info.manufacturer_data.get(MANUFACTURER_ID))
        if advertisement is None:
            return
        if not battery_plausible(advertisement.battery_mv):
            _LOGGER.warning(
                "WOLINK battery reading %d mV is out of the plausible range",
                advertisement.battery_mv,
            )
        self.update_battery(advertisement.battery_mv / 1000.0)
        self.set_device_sw_version(str(advertisement.app_version))
        self.set_device_hw_version(str(advertisement.hardware_version))
