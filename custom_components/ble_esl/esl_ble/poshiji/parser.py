"""Recognize PSJ-420 advertisements without inventing battery readings."""

from ..base import BleParser
from .const import BRAND, MANUFACTURER_ID
from .devices import PSJ_420
from .protocol import is_psj420_advertisement


def is_poshiji_advertisement(info):
    return is_psj420_advertisement(info.manufacturer_data.get(MANUFACTURER_ID))


class PoshijiBluetoothDeviceData(BleParser):
    def __init__(self, preset=None):
        super().__init__()
        self.preset = preset or PSJ_420
        self.last_service_info = None

    def set_preset(self, preset):
        self.preset = preset
        if self.last_service_info is not None:
            self._update_device_info(self.last_service_info)

    def supported(self, data):
        return is_poshiji_advertisement(data)

    def _update_device_info(self, info):
        identifier = info.address.replace(":", "")[-8:]
        self.set_title(f"{identifier} ({self.preset.display_name})")
        self.set_device_name(f"{BRAND} {identifier}")
        self.set_device_type(f"{self.preset.display_name} {self.preset.width}x{self.preset.height}")
        self.set_device_manufacturer(BRAND)

    def _start_update(self, info):
        if not self.supported(info):
            return
        self.last_service_info = info
        self._update_device_info(info)
