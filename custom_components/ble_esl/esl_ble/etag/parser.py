"""ETAG advertisement parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sensor_state_data import BinarySensorDeviceClass, SensorLibrary

from ..base import BleParser
from .const import BRAND, NAME_PREFIX

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def is_etag_advertisement(info: BluetoothServiceInfoBleak) -> bool:
    """A local name starting with "ETAG-"."""
    return isinstance(info.name, str) and info.name.startswith(NAME_PREFIX)


def battery_percentage(info: BluetoothServiceInfoBleak) -> int | None:
    """Read ETAG's one-byte manufacturer record from the raw AD structures.

    Bluetooth label 1.3.3.73 (ScanBleDeviceActivity.J0) reads byte 29 as
    battery percent. In captured ETAG frames that is AD record ``02 FF xx``.
    It lacks a company identifier, so the normal manufacturer_data mapping
    drops it. Walk AD lengths rather than assuming a fixed byte offset.
    Raw data is available from ESPHome proxies on recent HA versions;
    transports/versions without it cannot supply this reading.
    """
    if not is_etag_advertisement(info):
        return None
    raw = getattr(info, "raw", None) or b""
    offset = 0
    while offset < len(raw):
        length = raw[offset]
        end = offset + 1 + length
        if length == 0 or end > len(raw):
            break
        if length == 2 and raw[offset + 1] == 0xFF:
            percent = raw[offset + 2]
            return percent if percent <= 100 else None
        offset = end
    return None


class EtagParser(BleParser):
    """ETAG battery percentage from the short manufacturer AD record."""

    brand = BRAND
    fallback_name = "ETAG 2.13"
    is_advertisement = staticmethod(is_etag_advertisement)

    def _parse(self, service_info: BluetoothServiceInfoBleak) -> None:
        percent = battery_percentage(service_info)
        if percent is None:
            return
        self.update_predefined_sensor(SensorLibrary.BATTERY__PERCENTAGE, percent)
        self.update_predefined_binary_sensor(BinarySensorDeviceClass.BATTERY, percent <= 10)
