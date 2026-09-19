"""PickSmart (gicisky) Protocol Backend."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from typing import TYPE_CHECKING

from ..base import (
    AdvertisementInfo,
    BleBackend,
    Capabilities,
    DevicePreset,
    WriteResult,
)
from .const import BRAND, MANUFACTURER_ID
from .devices import PRESETS, apply_firmware_quirks, get_device_preset, preset_choices
from .parser import (
    PickSmartBluetoothDeviceData,
    is_picksmart_advertisement,
    parse_manufacturer_data,
)
from .protocol import encode_image
from .writer import update_image, update_prepared

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image


class PickSmartBleBackend(BleBackend):
    """PickSmart (gicisky) BLE backend implementation."""

    id = "picksmart"
    name = "PickSmart (gicisky)"
    brand = BRAND
    capabilities = Capabilities(
        passive_battery=True,
        session_battery=False,
        session_temperature=False,
        model_detection=True,
        palettes=("BW", "BWR", "BWRY"),
    )

    def presets(self) -> Mapping[str, DevicePreset]:
        """Return PickSmart device presets."""
        return PRESETS

    def refine_preset(
        self, preset: DevicePreset, info: AdvertisementInfo | None
    ) -> DevicePreset:
        """Refine preset using advertisement info (advertisement is authoritative for PickSmart)."""
        if info is None or not info.raw:
            return preset
        firmware = info.raw.get("firmware")
        device_id = info.raw.get("device_id")
        if device_id is not None and firmware is not None:
            refined = get_device_preset(device_id, firmware)
            if refined is not None:
                return refined
        return preset

    def create_parser(
        self, preset: DevicePreset | None = None
    ) -> PickSmartBluetoothDeviceData:
        """Return an advertisement parser bound to this preset."""
        return PickSmartBluetoothDeviceData(preset=preset)

    def supported(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Check if advertisement belongs to PickSmart."""
        return is_picksmart_advertisement(service_info)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Extract advertisement data from service info."""
        mfr_bytes = service_info.manufacturer_data.get(MANUFACTURER_ID)
        if not mfr_bytes:
            return None
        parsed = parse_manufacturer_data(mfr_bytes)
        if not parsed:
            return None

        # Return model_key if in catalog; else None to fall back to manual model selection
        model_key = parsed["model_key"] if parsed["model_key"] in PRESETS else None

        return AdvertisementInfo(
            battery_mv=parsed.get("battery_mv"),
            model_key=model_key,
            sw_version=f"0x{parsed['firmware']:04X}",
            hw_version=f"0x{parsed['hardware']:04X}",
            raw=parsed,
        )

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

    def prepare_image(
        self, preset: DevicePreset, image: Image.Image, address: str
    ) -> bytes:
        """Encode to the PickSmart byte stream (CPU-bound; caller runs it in a thread)."""
        return encode_image(image, preset)

    async def write_prepared(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        prepared: Awaitable[bytes],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Write an already-scheduled encode to the device."""
        return await update_prepared(
            ble_device, preset, prepared, attempt=attempt, write_delay_ms=write_delay_ms
        )


PickSmartProtocol = PickSmartBleBackend

__all__ = [
    "PRESETS",
    "PickSmartBleBackend",
    "PickSmartBluetoothDeviceData",
    "PickSmartProtocol",
    "apply_firmware_quirks",
    "get_device_preset",
    "is_picksmart_advertisement",
    "preset_choices",
]
