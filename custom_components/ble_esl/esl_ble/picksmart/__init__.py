"""PickSmart (gicisky) Protocol Backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset
from . import writer
from .const import MANUFACTURER_ID
from .devices import PRESETS, apply_firmware_quirks, get_device_preset
from .parser import (
    PickSmartBluetoothDeviceData,
    is_picksmart_advertisement,
    parse_manufacturer_data,
)

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class PickSmartBleBackend(BleBackend):
    """PickSmart (gicisky) BLE backend."""

    id = "picksmart"
    label = "PickSmart"
    name = "PickSmart (gicisky)"
    capabilities = Capabilities(
        passive_battery=True,
        session_battery=False,
        session_temperature=False,
        model_detection=True,
        palettes=("BW", "BWR", "BWRY"),
    )
    PRESETS = PRESETS
    parser_cls = PickSmartBluetoothDeviceData
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def refine_preset(
        self, preset: DevicePreset, info: AdvertisementInfo | None
    ) -> DevicePreset:
        """The advertisement identifies the model and firmware; it is authoritative."""
        if info is None or not info.raw:
            return preset
        firmware = info.raw.get("firmware")
        device_id = info.raw.get("device_id")
        if device_id is not None and firmware is not None:
            refined = get_device_preset(device_id, firmware)
            if refined is not None:
                return refined
        return preset

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Extract advertisement data from service info."""
        mfr_bytes = service_info.manufacturer_data.get(MANUFACTURER_ID)
        parsed = parse_manufacturer_data(mfr_bytes) if mfr_bytes else None
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


__all__ = [
    "PRESETS",
    "PickSmartBleBackend",
    "PickSmartBluetoothDeviceData",
    "apply_firmware_quirks",
    "get_device_preset",
    "is_picksmart_advertisement",
]
