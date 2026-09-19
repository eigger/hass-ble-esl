"""WOLINK Protocol backend for BLE ESL BWRY ESL tags."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset, WriteResult
from . import writer
from .const import BRAND, MANUFACTURER_ID
from .devices import PRESETS, preset_choices
from .parser import WolinkBluetoothDeviceData, is_wolink_advertisement
from .protocol import parse_manufacturer_data

if TYPE_CHECKING:
    from bleak import BleakClient
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
    PRESETS = PRESETS
    parser_cls = WolinkBluetoothDeviceData

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Parse advertisement manufacturer data."""
        mfr_bytes = service_info.manufacturer_data.get(MANUFACTURER_ID)
        if not mfr_bytes or len(mfr_bytes) < 10:
            return None
        try:
            parsed = parse_manufacturer_data(mfr_bytes)
        except Exception:
            return None
        return AdvertisementInfo(
            battery_mv=parsed.get("battery_mv"),
            sw_version=str(parsed["app_ver"]) if parsed.get("app_ver") is not None else None,
            hw_version=str(parsed["hw_ver"]) if parsed.get("hw_ver") is not None else None,
            raw=parsed,
        )

    def prepare_image(
        self, preset: DevicePreset, image: Image.Image, address: str
    ) -> writer.PreparedImage:
        return writer.prepare_payload(image, preset)

    async def write_session(
        self,
        client: BleakClient,
        address: str,
        preset: DevicePreset,
        prepared: Awaitable[writer.PreparedImage],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        return await writer.write_session(
            client, address, preset, prepared, attempt=attempt, write_delay_ms=write_delay_ms
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
