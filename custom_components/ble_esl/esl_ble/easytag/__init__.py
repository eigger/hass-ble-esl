"""easyTag (eLabel) Protocol Backend."""

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
from .devices import PRESETS, preset_choices
from .parser import EasyTagBluetoothDeviceData, is_easytag_advertisement
from .writer import update_image

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image


class EasyTagBleBackend(BleBackend):
    """easyTag BLE backend implementation."""

    id = "easytag"
    name = "easyTag (eLabel)"
    capabilities = Capabilities(
        passive_battery=False,
        session_battery=True,
        session_temperature=True,
        model_detection=False,
        palettes=("BW", "BWR"),
    )

    def presets(self) -> Mapping[str, DevicePreset]:
        """Return easyTag device presets."""
        return PRESETS

    def create_parser(
        self, preset: DevicePreset | None = None
    ) -> EasyTagBluetoothDeviceData:
        """Return an advertisement parser bound to this preset."""
        return EasyTagBluetoothDeviceData(preset=preset)

    def supported(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Check if advertisement belongs to easyTag."""
        return is_easytag_advertisement(service_info)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Extract advertisement data from service info."""
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


EasyTagProtocol = EasyTagBleBackend

__all__ = [
    "EasyTagBleBackend",
    "EasyTagBluetoothDeviceData",
    "EasyTagProtocol",
    "PRESETS",
    "is_easytag_advertisement",
    "preset_choices",
]
