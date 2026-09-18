"""WOLINK Protocol backend for BLE ESL BWRY ESL tags."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from ..base import (
    AdvertisementInfo,
    BleBackend,
    Capabilities,
    DevicePreset,
    WriteResult,
)
from .const import BRAND, MANUFACTURER_ID
from .devices import PRESETS, preset_choices
from .parser import WolinkBluetoothDeviceData, is_wolink_advertisement
from .protocol import parse_manufacturer_data
from .writer import update_image

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image


class WolinkBleBackend(BleBackend):
    """WOLINK BLE backend implementation."""

    id = "wolink"
    name = "WOLINK (BWRY)"
    brand = BRAND
    capabilities = Capabilities(
        passive_battery=True,
        session_battery=False,
        session_temperature=False,
        model_detection=False,
        palettes=("BW", "BWR", "BWRY"),
    )

    def presets(self) -> Mapping[str, DevicePreset]:
        """Return WOLINK device presets."""
        return PRESETS

    def create_parser(
        self, preset: DevicePreset | None = None
    ) -> WolinkBluetoothDeviceData:
        """Return an advertisement parser bound to this preset."""
        return WolinkBluetoothDeviceData(preset=preset)

    def supported(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Check if advertisement belongs to WOLINK."""
        return is_wolink_advertisement(service_info)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Parse advertisement manufacturer data."""
        mfr_bytes = service_info.manufacturer_data.get(MANUFACTURER_ID)
        if not mfr_bytes or len(mfr_bytes) < 10:
            return None
        try:
            parsed = parse_manufacturer_data(mfr_bytes)
            sw_ver = (
                str(parsed["app_ver"])
                if parsed.get("app_ver") is not None
                else None
            )
            hw_ver = (
                str(parsed["hw_ver"])
                if parsed.get("hw_ver") is not None
                else None
            )
            return AdvertisementInfo(
                battery_mv=parsed.get("battery_mv"),
                sw_version=sw_ver,
                hw_version=hw_ver,
                raw=parsed,
            )
        except Exception:
            return None

    async def write_image(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        image: Image.Image,
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Write image to device."""
        return await update_image(
            ble_device,
            preset,
            image,
            attempt=attempt,
            write_delay_ms=write_delay_ms,
        )


WolinkProtocol = WolinkBleBackend

__all__ = [
    "PRESETS",
    "WolinkBleBackend",
    "WolinkBluetoothDeviceData",
    "WolinkProtocol",
    "is_wolink_advertisement",
    "preset_choices",
]
