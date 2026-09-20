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
    """Any XTE record is ours; a device number not in the catalog is reported once."""
    data = info.manufacturer_data.get(MANUFACTURER_ID)
    advertisement = parse_advertisement(data)
    if advertisement is None:
        return False
    if preset_for_advertisement(data) is None and info.address not in _unknown_reported:
        # The model has to be picked by hand; log what a report needs so the
        # device number can be added to the catalog.
        _unknown_reported.add(info.address)
        _LOGGER.info(
            "XTE tag %s has an unknown device number %d (hardware %d, firmware %s, "
            "manufacturer data %s): select its model manually, and open an issue with "
            "this line and the tag's model and resolution.",
            info.address,
            advertisement.device_number,
            advertisement.hardware_revision,
            advertisement.firmware,
            data.hex(),
        )
    return True


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
