"""easyTag (eLabel) Protocol Backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, BleBackend, Capabilities
from . import writer
from .devices import PRESETS
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
        model_detection=False,
        palettes=("BW", "BWR"),
    )
    PRESETS = PRESETS
    parser_cls = EasyTagBluetoothDeviceData
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """easyTag advertisements carry no readings."""
        return None


__all__ = ["PRESETS", "EasyTagBleBackend", "EasyTagBluetoothDeviceData", "is_easytag_advertisement"]
