"""WOLINK protocol backend (tags sold as Zhsunyco)."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset
from . import writer
from .const import MANUFACTURER_ID
from .devices import PRESETS, preset_for_advertisement
from .parser import WolinkBluetoothDeviceData, is_wolink_advertisement
from .protocol import parse_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class WolinkBleBackend(BleBackend):
    """WOLINK BLE backend."""

    id = "wolink"
    label = "WOLINK"
    name = "WOLINK (BWRY)"
    capabilities = Capabilities(
        passive_battery=True,
        session_battery=False,
        session_temperature=False,
        palettes=("BW", "BWR", "BWRY"),
    )
    PRESETS = PRESETS
    parser_cls = WolinkBluetoothDeviceData
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def refine_preset(self, preset: DevicePreset, info: AdvertisementInfo | None) -> DevicePreset:
        """A known display version names the panel; otherwise the choice stays."""
        if info is None or info.model_key is None:
            return preset
        return self.PRESETS.get(info.model_key, preset)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Battery, versions and (for a known display version) the model."""
        data = service_info.manufacturer_data.get(MANUFACTURER_ID)
        advertisement = parse_advertisement(data)
        if advertisement is None:
            return None
        preset = preset_for_advertisement(data)
        return AdvertisementInfo(
            battery_mv=advertisement.battery_mv,
            model_key=None if preset is None else preset.key,
            sw_version=str(advertisement.app_version),
            hw_version=str(advertisement.hardware_version),
            raw=dataclasses.asdict(advertisement),
        )


__all__ = [
    "PRESETS",
    "WolinkBleBackend",
    "WolinkBluetoothDeviceData",
    "is_wolink_advertisement",
    "preset_for_advertisement",
]
