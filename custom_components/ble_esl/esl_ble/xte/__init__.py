"""XTE protocol backend (tags sold as Poshiji)."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset, WriteResult
from . import writer
from .const import MANUFACTURER_ID, PALETTES
from .devices import PRESETS, preset_for_advertisement
from .parser import XteBluetoothDeviceData, is_xte_advertisement
from .protocol import parse_advertisement

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class XteBleBackend(BleBackend):
    """XTE BLE backend."""

    id = "xte"
    label = "XTE"
    name = "XTE (Poshiji)"
    capabilities = Capabilities(
        passive_battery=True,
        session_battery=False,
        session_temperature=False,
        model_detection=True,
        palettes=tuple(PALETTES),
    )
    PRESETS = PRESETS
    parser_cls = XteBluetoothDeviceData
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def refine_preset(self, preset: DevicePreset, info: AdvertisementInfo | None) -> DevicePreset:
        """The advertised device number is authoritative over the configured model."""
        if info is None or info.model_key is None:
            return preset
        return self.PRESETS.get(info.model_key, preset)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """The advertisement names the tag type (model), battery and versions."""
        data = service_info.manufacturer_data.get(MANUFACTURER_ID)
        advertisement = parse_advertisement(data)
        preset = preset_for_advertisement(data)
        if advertisement is None or preset is None:
            return None
        return AdvertisementInfo(
            model_key=preset.key,
            sw_version=advertisement.firmware,
            hw_version=str(advertisement.hardware_revision),
            raw={
                "device_number": advertisement.device_number,
                "battery_percent": advertisement.battery_percent,
                "record_type": advertisement.record_type,
                "chip_type": advertisement.chip_type,
                "tx_power": advertisement.tx_power,
            },
        )

    async def write_prepared(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        prepared: Awaitable[bytes],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        # Only captured profiles are known; refuse anything else before connecting.
        if self.PRESETS.get(preset.key) != preset:
            return WriteResult(success=False, error="Unsupported XTE preset")
        return await super().write_prepared(
            ble_device, preset, prepared, attempt=attempt, write_delay_ms=write_delay_ms
        )


__all__ = [
    "PRESETS",
    "XteBleBackend",
    "XteBluetoothDeviceData",
    "is_xte_advertisement",
    "preset_for_advertisement",
]
