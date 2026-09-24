"""WOLINK Protocol backend for BLE ESL BWRY ESL tags."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset
from . import writer
from .const import MANUFACTURER_ID
from .devices import PRESETS, preset_for_advertisement
from .parser import WolinkBluetoothDeviceData, is_wolink_advertisement
from .protocol import parse_manufacturer_data

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class WolinkBleBackend(BleBackend):
    """WOLINK (BWRY) BLE backend."""

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
        """A captured display version names the panel; an unknown one leaves the choice."""
        if info is None or info.model_key is None:
            return preset
        return self.PRESETS.get(info.model_key, preset)

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
        preset = preset_for_advertisement(mfr_bytes)
        return AdvertisementInfo(
            battery_mv=parsed.get("battery_mv"),
            model_key=None if preset is None else preset.key,
            sw_version=str(parsed["app_ver"]) if parsed.get("app_ver") is not None else None,
            hw_version=str(parsed["hw_ver"]) if parsed.get("hw_ver") is not None else None,
            raw=parsed,
        )


__all__ = [
    "PRESETS",
    "WolinkBleBackend",
    "WolinkBluetoothDeviceData",
    "is_wolink_advertisement",
    "preset_for_advertisement",
]
