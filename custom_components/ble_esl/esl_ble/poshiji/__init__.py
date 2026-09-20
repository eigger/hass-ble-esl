"""Poshiji backend using the XTE BLE protocol."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset, WriteResult
from . import writer
from .const import MANUFACTURER_ID, PALETTES
from .devices import PRESETS, preset_for_advertisement
from .parser import PoshijiBluetoothDeviceData, is_poshiji_advertisement

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class PoshijiBleBackend(BleBackend):
    """Poshiji (XTE) BLE backend."""

    id = "poshiji"
    label = "XTE"
    name = "Poshiji (XTE)"
    capabilities = Capabilities(
        passive_battery=False,
        session_battery=False,
        session_temperature=False,
        model_detection=True,
        palettes=tuple(PALETTES),
    )
    PRESETS = PRESETS
    parser_cls = PoshijiBluetoothDeviceData
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """The advertisement fingerprints the model and carries no readings."""
        preset = preset_for_advertisement(service_info.manufacturer_data.get(MANUFACTURER_ID))
        return None if preset is None else AdvertisementInfo(model_key=preset.key)

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
            return WriteResult(success=False, error="Unsupported Poshiji preset")
        return await super().write_prepared(
            ble_device, preset, prepared, attempt=attempt, write_delay_ms=write_delay_ms
        )


__all__ = [
    "PRESETS",
    "PoshijiBleBackend",
    "PoshijiBluetoothDeviceData",
    "is_poshiji_advertisement",
    "preset_for_advertisement",
]
