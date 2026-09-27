"""PickSmart protocol implementation (tags sold as Gicisky)."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, Capabilities, DevicePreset, EslProtocol
from . import writer
from .const import MANUFACTURER_ID
from .devices import PRESETS, preset_for_device
from .parser import PickSmartBluetoothDeviceData, is_picksmart_advertisement
from .wire import parse_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class PickSmartProtocol(EslProtocol):
    """PickSmart ESL protocol."""

    id = "picksmart"
    label = "PickSmart"
    name = "PickSmart (gicisky)"
    capabilities = Capabilities(
        passive_battery=True,
        session_battery=False,
        session_temperature=False,
        palettes=("BW", "BWR", "BWRY"),
    )
    PRESETS = PRESETS
    parser_cls = PickSmartBluetoothDeviceData
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def refine_preset(self, preset: DevicePreset, info: AdvertisementInfo | None) -> DevicePreset:
        """The advertised model and firmware are authoritative."""
        if info is None or not info.raw:
            return preset
        return preset_for_device(info.raw["device_id"], info.raw["firmware"]) or preset

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Battery, versions and, for a catalog model, its key."""
        advertisement = parse_advertisement(service_info.manufacturer_data.get(MANUFACTURER_ID))
        if advertisement is None:
            return None
        model_key = advertisement.model_key
        return AdvertisementInfo(
            battery_mv=advertisement.battery_mv,
            model_key=model_key if model_key in PRESETS else None,
            sw_version=f"0x{advertisement.firmware:04X}",
            hw_version=f"0x{advertisement.hardware:04X}",
            raw=dataclasses.asdict(advertisement),
        )


__all__ = [
    "PRESETS",
    "PickSmartBluetoothDeviceData",
    "PickSmartProtocol",
    "is_picksmart_advertisement",
    "preset_for_device",
]
