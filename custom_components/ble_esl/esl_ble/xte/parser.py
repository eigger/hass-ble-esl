"""Recognize XTE advertisements and publish what they carry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sensor_state_data import BinarySensorDeviceClass, SensorLibrary

from ..base import BleParser
from .const import BATTERY_LOW_PERCENT, BRAND, MANUFACTURER_ID
from .devices import preset_for_advertisement
from .protocol import parse_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)
_unknown_reported: set[str] = set()


def is_xte_advertisement(info: BluetoothServiceInfoBleak) -> bool:
    data = info.manufacturer_data.get(MANUFACTURER_ID)
    if preset_for_advertisement(data) is not None:
        return True
    # An XTE tag of a type not in the catalog: say so once, with what a
    # report needs, instead of ignoring it silently.
    advertisement = parse_advertisement(data)
    if advertisement is not None and info.address not in _unknown_reported:
        _unknown_reported.add(info.address)
        _LOGGER.info(
            "Unsupported XTE tag %s: device number %d, hardware %d, firmware %s, "
            "manufacturer data %s. Open an issue with the tag's model and resolution.",
            info.address,
            advertisement.device_number,
            advertisement.hardware_revision,
            advertisement.firmware,
            data.hex(),
        )
    return False


class XteBluetoothDeviceData(BleParser):
    """Parser for XTE tags: battery percentage and versions from the advertisement."""

    brand = BRAND
    fallback_name = "XTE"
    is_advertisement = staticmethod(is_xte_advertisement)

    def _parse(self, service_info: BluetoothServiceInfoBleak) -> None:
        advertisement = parse_advertisement(service_info.manufacturer_data.get(MANUFACTURER_ID))
        if advertisement is None:
            return
        self.set_device_sw_version(advertisement.firmware)
        self.set_device_hw_version(str(advertisement.hardware_revision))
        # The tag reports a percentage, not a cell voltage.
        self.update_predefined_sensor(
            SensorLibrary.BATTERY__PERCENTAGE, advertisement.battery_percent
        )
        self.update_predefined_binary_sensor(
            BinarySensorDeviceClass.BATTERY, advertisement.battery_percent <= BATTERY_LOW_PERCENT
        )
