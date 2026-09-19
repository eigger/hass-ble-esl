"""Tests for WOLINK parser and advertisement parsing."""

from __future__ import annotations

from unittest.mock import MagicMock
from sensor_state_data import BinarySensorDeviceClass, SensorLibrary

from custom_components.ble_esl.esl_ble.wolink import WolinkBleBackend
from custom_components.ble_esl.esl_ble.wolink.const import (
    MANUFACTURER_ID,
    SERVICE_UUID,
)
from custom_components.ble_esl.esl_ble.wolink.devices import PRESETS
from custom_components.ble_esl.esl_ble.wolink.parser import (
    WolinkBluetoothDeviceData,
)


def test_parser_supported():
    """Verify WOLINK supported matcher."""
    parser = WolinkBluetoothDeviceData(PRESETS["290"])

    # Matching via manufacturer data 0xBBAA (48042)
    info_mfr = MagicMock()
    info_mfr.manufacturer_data = {MANUFACTURER_ID: b"\x00" * 10}
    info_mfr.service_uuids = []
    assert parser.supported(info_mfr) is True

    # Matching via Service UUID
    info_uuid = MagicMock()
    info_mfr.manufacturer_data = {}
    info_uuid.service_uuids = [SERVICE_UUID]
    assert parser.supported(info_uuid) is True

    # Non-matching advertisement
    info_other = MagicMock()
    info_other.manufacturer_data = {0x1234: b"\x00"}
    info_other.service_uuids = ["00001523-1212-efde-1523-785feabcd123"]
    assert parser.supported(info_other) is False


def test_parser_start_update_battery_and_versions():
    """Verify parser extracts battery, versions, and naming."""
    parser = WolinkBluetoothDeviceData(PRESETS["290"])

    info = MagicMock()
    info.address = "66:66:54:20:00:55"
    info.service_uuids = [SERVICE_UUID]
    # PID=0x1234, AppVer=0x0102(258), HwVer=0x0304(772), DispVer=0x0506, Bat=3000mV (0x0BB8)
    mfr_bytes = bytes([
        0x12, 0x34, 0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x0B, 0xB8
    ])
    info.manufacturer_data = {MANUFACTURER_ID: mfr_bytes}

    parser._start_update(info)

    assert parser.title == "54200055 (2.9\" BWRY)"
    assert parser.get_device_name() == "Zhsunyco 54200055"
    assert parser._sensor_values[SensorLibrary.VOLTAGE__ELECTRIC_POTENTIAL_VOLT] == 3.0
    assert parser._sensor_values[SensorLibrary.BATTERY__PERCENTAGE] == 100
    assert parser._binary_sensor_values[BinarySensorDeviceClass.BATTERY] is False
    assert parser._device_sw_version == "258"

    # 2200 mV (0x0898): 0 % and battery low
    info.manufacturer_data = {MANUFACTURER_ID: mfr_bytes[:8] + bytes([0x08, 0x98])}
    parser._start_update(info)
    assert parser._sensor_values[SensorLibrary.BATTERY__PERCENTAGE] == 0
    assert parser._binary_sensor_values[BinarySensorDeviceClass.BATTERY] is True
    assert parser._device_hw_version == "772"


def test_protocol_parse_advertisement():
    """Verify WolinkBleBackend.parse_advertisement helper."""
    protocol = WolinkBleBackend()

    info = MagicMock()
    info.manufacturer_data = {
        MANUFACTURER_ID: bytes([0x12, 0x34, 0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x0B, 0xB8])
    }
    adv_info = protocol.parse_advertisement(info)
    assert adv_info is not None
    assert adv_info.battery_mv == 3000
    assert adv_info.sw_version == "258"
    assert adv_info.hw_version == "772"

    # Empty/invalid manufacturer data returns None
    info_empty = MagicMock()
    info_empty.manufacturer_data = {}
    assert protocol.parse_advertisement(info_empty) is None
