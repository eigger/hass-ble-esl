"""Poshiji PSJ-420 backend using the XTE BLE protocol."""

from ..base import AdvertisementInfo, BleBackend, Capabilities
from .const import BRAND
from .devices import PRESETS, PSJ_420
from .parser import PoshijiBluetoothDeviceData, is_poshiji_advertisement
from .writer import prepare_image_object, update_image, update_prepared


class PoshijiBleBackend(BleBackend):
    id = "poshiji"
    name = "Poshiji (XTE)"
    brand = BRAND
    capabilities = Capabilities(
        passive_battery=False, session_battery=False, session_temperature=False,
        model_detection=True, palettes=("BWRY",),
    )

    def presets(self):
        return PRESETS

    def supported(self, service_info):
        return is_poshiji_advertisement(service_info)

    def create_parser(self, preset=None):
        return PoshijiBluetoothDeviceData(preset)

    def parse_advertisement(self, service_info):
        if not self.supported(service_info):
            return None
        return AdvertisementInfo(model_key=PSJ_420.key)

    async def write_image(self, ble_device, preset, image, *, attempt=1, write_delay_ms=0):
        return await update_image(ble_device, preset, image,
                                  attempt=attempt, write_delay_ms=write_delay_ms)

    def prepare_image(self, preset, image, address):
        return prepare_image_object(image)

    async def write_prepared(self, ble_device, preset, prepared, *, attempt=1, write_delay_ms=0):
        return await update_prepared(ble_device, preset, prepared,
                                     attempt=attempt, write_delay_ms=write_delay_ms)
