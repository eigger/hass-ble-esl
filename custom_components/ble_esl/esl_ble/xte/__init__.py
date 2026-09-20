"""XTE protocol backend (tags sold as Poshiji)."""

from __future__ import annotations

from collections.abc import Awaitable
import dataclasses
from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities, DevicePreset, WriteResult
from . import writer
from .const import MANUFACTURER_ID, PALETTES, UNSUPPORTED_PACKING_DEVICE_NUMBERS
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
        """A captured device number is authoritative; otherwise the configured model stays.

        A hand-picked (size-only) preset is stamped with the device number the
        tag advertises, so the write guard can refuse the tag types whose
        pixel layout is not implemented.
        """
        if info is None:
            return preset
        if info.model_key is not None:
            return self.PRESETS.get(info.model_key, preset)
        seen = info.raw.get("device_number")
        if seen is None or preset.extra.get("seen_device_number") == seen:
            return preset
        return dataclasses.replace(preset, extra={**preset.extra, "seen_device_number": seen})

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """The advertisement names the tag type, battery and versions.

        model_key is set only for a captured device number; otherwise the
        config flow asks for the model and the size-only presets are offered.
        """
        data = service_info.manufacturer_data.get(MANUFACTURER_ID)
        advertisement = parse_advertisement(data)
        if advertisement is None:
            return None
        preset = preset_for_advertisement(data)
        return AdvertisementInfo(
            model_key=None if preset is None else preset.key,
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
        # Only catalog geometry is packed correctly; refuse anything else, and
        # the tag types with an unimplemented pixel layout, before connecting.
        catalog = self.PRESETS.get(preset.key)
        if catalog is None or (preset.width, preset.height, preset.colors) != (
            catalog.width,
            catalog.height,
            catalog.colors,
        ):
            return WriteResult(success=False, error="Unsupported XTE preset")
        seen = preset.extra.get("seen_device_number")
        if seen in UNSUPPORTED_PACKING_DEVICE_NUMBERS:
            return WriteResult(
                success=False,
                error=f"XTE device number {seen} uses a pixel layout that is not implemented",
            )
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
