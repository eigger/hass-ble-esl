"""easyTag (eLabel) Protocol Backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset
from . import writer
from .devices import PRESETS, preset_for_advertisement
from .parser import EasyTagBluetoothDeviceData, is_easytag_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class EasyTagBleBackend(BleBackend):
    """easyTag (eLabel) BLE backend."""

    id = "easytag"
    label = "easyTag"
    name = "easyTag (eLabel)"
    capabilities = Capabilities(
        passive_battery=False,
        session_battery=True,
        session_temperature=True,
        model_detection=True,
        palettes=("BW", "BWR"),
    )
    PRESETS = PRESETS
    parser_cls = EasyTagBluetoothDeviceData
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def refine_preset(self, preset: DevicePreset, info: AdvertisementInfo | None) -> DevicePreset:
        """A model the advertisement names wins; otherwise the choice stays."""
        if info is None or info.model_key is None:
            return preset
        return self.PRESETS.get(info.model_key, preset)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """easyTag advertisements carry no readings, only (someday) the model."""
        preset = preset_for_advertisement(service_info)
        if preset is None:
            return None
        return AdvertisementInfo(model_key=preset.key)


__all__ = [
    "PRESETS",
    "EasyTagBleBackend",
    "EasyTagBluetoothDeviceData",
    "is_easytag_advertisement",
    "preset_for_advertisement",
]
