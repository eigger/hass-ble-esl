"""easyTag advertisement parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, NAME_PREFIX, SERVICE_UUID

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def is_easytag_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """The easyTag service UUID, or a name starting with "easyTag"."""
    if SERVICE_UUID in {uuid.lower() for uuid in data.service_uuids if isinstance(uuid, str)}:
        return True
    return isinstance(data.name, str) and data.name.startswith(NAME_PREFIX)


class EasyTagBluetoothDeviceData(BleParser):
    """easyTag advertisements carry no readings; battery and temperature come from writes."""

    brand = BRAND
    fallback_name = "easyTag"
    is_advertisement = staticmethod(is_easytag_advertisement)
