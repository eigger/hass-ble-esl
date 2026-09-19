"""Poshiji PSJ-420 backend using the XTE BLE protocol."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset, WriteResult
from . import writer
from .const import BRAND
from .devices import PRESETS, PSJ_420
from .parser import PoshijiBluetoothDeviceData, is_poshiji_advertisement

if TYPE_CHECKING:
    from bleak import BleakClient
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image


class PoshijiBleBackend(BleBackend):
    """Poshiji (XTE) BLE backend implementation."""

    id = "poshiji"
    name = "Poshiji (XTE)"
    brand = BRAND
    capabilities = Capabilities(
        passive_battery=False,
        session_battery=False,
        session_temperature=False,
        model_detection=True,
        palettes=("BWRY",),
    )
    PRESETS = PRESETS
    parser_cls = PoshijiBluetoothDeviceData

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """The advertisement identifies the (single) model and carries no readings."""
        if not self.supported(service_info):
            return None
        return AdvertisementInfo(model_key=PSJ_420.key)

    def prepare_image(
        self, preset: DevicePreset, image: Image.Image, address: str
    ) -> bytes:
        return writer.prepare_image_object(image)

    async def write_prepared(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        prepared: Awaitable[bytes],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        # Only the captured PSJ-420 profile is known; refuse before connecting.
        if (preset.key, preset.width, preset.height, preset.colors) != (
            PSJ_420.key, PSJ_420.width, PSJ_420.height, PSJ_420.colors,
        ):
            return WriteResult(success=False, error="Unsupported Poshiji preset")
        return await super().write_prepared(
            ble_device, preset, prepared, attempt=attempt, write_delay_ms=write_delay_ms
        )

    async def write_session(
        self,
        client: BleakClient,
        address: str,
        preset: DevicePreset,
        prepared: Awaitable[bytes],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        return await writer.write_session(
            client, address, preset, prepared, attempt=attempt, write_delay_ms=write_delay_ms
        )


__all__ = ["PRESETS", "PoshijiBleBackend", "PoshijiBluetoothDeviceData", "is_poshiji_advertisement"]
