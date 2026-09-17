"""Tests for PickSmart advertisement parser and broadcast decoding."""

from __future__ import annotations

from unittest.mock import MagicMock
from sensor_state_data import BinarySensorDeviceClass, SensorLibrary

from custom_components.zhsunyco.zhsunyco_ble.picksmart.const import (
    MANUFACTURER_ID,
    SERVICE_UUIDS,
)
from custom_components.zhsunyco.zhsunyco_ble.picksmart.devices import (
    PRESETS,
    get_device_preset,
)
from custom_components.zhsunyco.zhsunyco_ble.picksmart.parser import (
    PickSmartBluetoothDeviceData,
    is_picksmart_advertisement,
    parse_manufacturer_data,
)


def test_picksmart_parser_supported():
    """Verify PickSmart advertisement matcher."""
    parser = PickSmartBluetoothDeviceData(PRESETS["0x0033"])

    # Match by Manufacturer ID 0x5053 (20563)
    info_mfr = MagicMock()
    info_mfr.manufacturer_data = {MANUFACTURER_ID: b"\x00" * 5}
    info_mfr.service_uuids = []
    assert is_picksmart_advertisement(info_mfr) is True
    assert parser.supported(info_mfr) is True

    # Match by Service UUID
    info_uuid = MagicMock()
    info_uuid.manufacturer_data = {}
    info_uuid.service_uuids = [SERVICE_UUIDS[0]]
    assert is_picksmart_advertisement(info_uuid) is True
    assert parser.supported(info_uuid) is True

    # Non-matching advertisement
    info_other = MagicMock()
    info_other.manufacturer_data = {48042: b"\x00"}
    info_other.service_uuids = ["00001523-1212-efde-1523-785feabcd123"]
    assert is_picksmart_advertisement(info_other) is False
    assert parser.supported(info_other) is False


def test_picksmart_parse_manufacturer_data():
    """Verify decoding 5-byte 0x5053 broadcast."""
    # 2.9" BWR (0x0033): data = [0x33, 0x1E (3.0V), 0x81, 0x01, 0x40]
    # device_id = ((0x40 << 8) | 0x33) & 0x3FFF = 0x0033
    data = bytes([0x33, 0x1E, 0x81, 0x01, 0x40])
    parsed = parse_manufacturer_data(data)
    assert parsed is not None
    assert parsed["device_id"] == 0x0033
    assert parsed["model_key"] == "0x0033"
    assert parsed["battery_v"] == 3.0
    assert parsed["battery_mv"] == 3000
    assert parsed["firmware"] == 0x8101


def test_picksmart_parser_device_info_and_battery():
    """Verify parser extracts battery percentage, voltage, and device info."""
    parser = PickSmartBluetoothDeviceData(PRESETS["0x0033"])

    info = MagicMock()
    info.address = "AA:BB:CC:DD:EE:FF"
    info.service_uuids = [SERVICE_UUIDS[0]]
    info.manufacturer_data = {
        MANUFACTURER_ID: bytes([0x33, 0x1A, 0x81, 0x01, 0x40])  # 2.6V
    }

    parser._start_update(info)

    assert parser.title == "CCDDEEFF (2.9\" EPD BWR)"
    assert parser.get_device_name() == "Zhsunyco CCDDEEFF"
    assert parser._sensor_values[SensorLibrary.VOLTAGE__ELECTRIC_POTENTIAL_VOLT] == 2.6
    # (2.6 - 2.5) * 100 / (2.9 - 2.5) = 25%
    assert parser._sensor_values[SensorLibrary.BATTERY__PERCENTAGE] == 25
    assert parser._binary_sensor_values[BinarySensorDeviceClass.BATTERY] is False
    assert parser._device_sw_version == "0x8101"


def test_picksmart_parser_battery_low_and_clamp():
    """Battery low turns on at 2.5 V; percentage clamps to 0-100."""
    def run(decivolts):
        parser = PickSmartBluetoothDeviceData(PRESETS["0x0033"])
        info = MagicMock()
        info.address = "AA:BB:CC:DD:EE:FF"
        info.service_uuids = [SERVICE_UUIDS[0]]
        info.manufacturer_data = {
            MANUFACTURER_ID: bytes([0x33, decivolts, 0x81, 0x01, 0x40])
        }
        parser._start_update(info)
        return (
            parser._sensor_values[SensorLibrary.BATTERY__PERCENTAGE],
            parser._binary_sensor_values[BinarySensorDeviceClass.BATTERY],
        )

    assert run(0x18) == (0, True)    # 2.4 V
    assert run(0x19) == (0, True)    # 2.5 V
    assert run(0x1A) == (25, False)  # 2.6 V
    assert run(0x1D) == (100, False)  # 2.9 V
    assert run(0x20) == (100, False)  # 3.2 V (clamped)


def test_picksmart_firmware_fix():
    """Verify 0x012B (7.5\" BWR) firmware 0x8101 compression switch fix."""
    normal_preset = get_device_preset(0x012B, firmware=0x0101)
    assert normal_preset is not None
    assert normal_preset.extra.get("compression2") is True
    assert normal_preset.extra.get("compression", False) is False

    fixed_preset = get_device_preset(0x012B, firmware=0x8101)
    assert fixed_preset is not None
    assert fixed_preset.extra.get("compression") is True
    assert fixed_preset.extra.get("compression2") is False


def test_picksmart_backend_refine_preset():
    """Verify PickSmartProtocol.refine_preset adjusts preset using AdvertisementInfo."""
    from custom_components.zhsunyco.zhsunyco_ble.base import AdvertisementInfo
    from custom_components.zhsunyco.zhsunyco_ble.picksmart import PickSmartProtocol

    backend = PickSmartProtocol()
    preset_75 = backend.presets()["0x012B"]

    # 1. Without AdvertisementInfo -> unmodified
    assert backend.refine_preset(preset_75, None) == preset_75

    # 2. With normal firmware 0x0101 -> unmodified (compression2=True)
    info_normal = AdvertisementInfo(raw={"device_id": 0x012B, "firmware": 0x0101})
    refined_normal = backend.refine_preset(preset_75, info_normal)
    assert refined_normal.extra.get("compression2") is True
    assert refined_normal.extra.get("compression", False) is False

    # 3. With quirk firmware 0x8101 on 7.5" -> refined (compression=True, compression2=False)
    info_quirk = AdvertisementInfo(raw={"device_id": 0x012B, "firmware": 0x8101})
    refined_quirk = backend.refine_preset(preset_75, info_quirk)
    assert refined_quirk.extra.get("compression") is True
    assert refined_quirk.extra.get("compression2") is False

    # 4. Advertisement is authoritative for PickSmart: if advertisement reports 0x012B, it resolves to 0x012B
    preset_29 = backend.presets()["0x0033"]
    refined_adv_authority = backend.refine_preset(preset_29, info_quirk)
    assert refined_adv_authority.key == "0x012B"
    assert refined_adv_authority.width == 800

