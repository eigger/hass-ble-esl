"""PickSmart advertisement parser: battery and versions for the device page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BATTERY_MAX_VOLTAGE, BATTERY_MIN_VOLTAGE, BRAND, MANUFACTURER_ID, SERVICE_UUIDS
from .wire import parse_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def is_picksmart_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """PickSmart manufacturer data, or one of the PickSmart service UUIDs."""
    if MANUFACTURER_ID in data.manufacturer_data:
        return True
    return any(
        isinstance(uuid, str) and uuid.lower() in SERVICE_UUIDS for uuid in data.service_uuids
    )


class PickSmartBluetoothDeviceData(BleParser):
    """Sensor data from PickSmart advertisements.

    The model the advertisement names is applied by the protocol's
    refine_preset(); a preset may narrow the battery range with
    extra["min_voltage"] / extra["max_voltage"].
    """

    brand = BRAND
    fallback_name = "PickSmart"
    is_advertisement = staticmethod(is_picksmart_advertisement)

    def _parse(self, service_info: BluetoothServiceInfoBleak) -> None:
        advertisement = parse_advertisement(service_info.manufacturer_data.get(MANUFACTURER_ID))
        if advertisement is None:
            return
        self.set_device_sw_version(f"0x{advertisement.firmware:04X}")
        self.set_device_hw_version(f"0x{advertisement.hardware:04X}")
        extra = self.preset.extra if self.preset else {}
        self.update_battery(
            round(advertisement.battery_mv / 1000, 1),
            extra.get("min_voltage", BATTERY_MIN_VOLTAGE),
            extra.get("max_voltage", BATTERY_MAX_VOLTAGE),
        )
