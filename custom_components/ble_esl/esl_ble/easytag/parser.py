"""Parser for easyTag BLE advertisements."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, NAME_PREFIX, SERVICE_UUID

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def is_easytag_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """Return True if advertisement matches easyTag service UUID or name prefix."""
    if any(isinstance(u, str) and u.lower() == SERVICE_UUID.lower() for u in data.service_uuids):
        return True
    return isinstance(data.name, str) and data.name.startswith(NAME_PREFIX)


class EasyTagBluetoothDeviceData(BleParser):
    """Data parser for easyTag Bluetooth ESL devices.

    easyTag advertisements carry no readings; battery and temperature come
    from the write session instead.
    """

    brand = BRAND
    fallback_name = "easyTag"
    is_advertisement = staticmethod(is_easytag_advertisement)
