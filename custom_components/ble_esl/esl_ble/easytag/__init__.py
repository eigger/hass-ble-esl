"""easyTag (eLabel) Protocol Backend."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset, WriteResult
from . import writer
from .const import BRAND
from .devices import PRESETS
from .parser import EasyTagBluetoothDeviceData, is_easytag_advertisement

if TYPE_CHECKING:
    from bleak import BleakClient
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image


class EasyTagBleBackend(BleBackend):
    """easyTag BLE backend implementation."""

    id = "easytag"
    name = "easyTag (eLabel)"
    brand = BRAND
    capabilities = Capabilities(
        passive_battery=False,
        session_battery=True,
        session_temperature=True,
        model_detection=False,
        palettes=("BW", "BWR"),
    )
    PRESETS = PRESETS
    parser_cls = EasyTagBluetoothDeviceData

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """easyTag advertisements carry no readings."""
        return None

    def prepare_image(
        self, preset: DevicePreset, image: Image.Image, address: str
    ) -> list[bytes]:
        return writer.prepare_frames(image, preset, address)

    async def write_session(
        self,
        client: BleakClient,
        address: str,
        preset: DevicePreset,
        prepared: Awaitable[list[bytes]],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        return await writer.write_session(
            client, address, preset, prepared, attempt=attempt, write_delay_ms=write_delay_ms
        )


__all__ = [
    "EasyTagBleBackend",
    "EasyTagBluetoothDeviceData",
    "PRESETS",
    "is_easytag_advertisement",
]
