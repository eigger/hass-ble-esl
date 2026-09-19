"""Parser for PickSmart (gicisky) BLE advertisements."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, MANUFACTURER_ID, SERVICE_UUIDS

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

# Battery % is a linear map of the advertised voltage over min-max, and at or
# below min the battery-low binary sensor turns on. Below 2.5 V e-paper refresh
# becomes unreliable even though BLE communication still works. A preset may
# override these via extra["min_voltage"] / extra["max_voltage"].
DEFAULT_MIN_VOLTAGE = 2.5
DEFAULT_MAX_VOLTAGE = 2.9


def is_picksmart_advertisement(data: BluetoothServiceInfoBleak) -> bool:
    """Return True if advertisement matches PickSmart manufacturer data or service UUIDs."""
    if MANUFACTURER_ID in data.manufacturer_data:
        return True
    return any(
        isinstance(uuid, str) and uuid.lower() in SERVICE_UUIDS
        for uuid in data.service_uuids
    )


def parse_manufacturer_data(data: bytes) -> dict | None:
    """Parse 5-byte 0x5053 manufacturer advertisement payload."""
    if len(data) != 5:
        return None
    device_id = ((data[4] << 8) | data[0]) & 0x3FFF
    battery_dv = data[1]
    firmware = (data[2] << 8) + data[3]
    hardware = (data[4] << 8) | data[0]
    return {
        "device_id": device_id,
        "model_key": f"0x{device_id:04X}",
        "battery_v": battery_dv / 10.0,
        "battery_mv": battery_dv * 100,
        "firmware": firmware,
        "hardware": hardware,
    }


class PickSmartBluetoothDeviceData(BleParser):
    """Data parser for PickSmart Bluetooth ESL devices."""

    brand = BRAND
    fallback_name = "PickSmart"
    is_advertisement = staticmethod(is_picksmart_advertisement)

    def _parse(self, service_info: BluetoothServiceInfoBleak) -> None:
        mfr_bytes = service_info.manufacturer_data.get(MANUFACTURER_ID)
        parsed = parse_manufacturer_data(mfr_bytes) if mfr_bytes else None
        if not parsed:
            return

        # The model the advertisement identifies is applied by the backend's
        # refine_preset() -> set_preset(); here only the readings are parsed.
        self.set_device_sw_version(f"0x{parsed['firmware']:04X}")
        self.set_device_hw_version(f"0x{parsed['hardware']:04X}")

        extra = self.preset.extra if self.preset else {}
        self.update_battery(
            round(parsed["battery_v"], 1),
            extra.get("min_voltage", DEFAULT_MIN_VOLTAGE),
            extra.get("max_voltage", DEFAULT_MAX_VOLTAGE),
        )
