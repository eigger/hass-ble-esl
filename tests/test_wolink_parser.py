"""Tests for WOLINK parser and advertisement parsing."""

from __future__ import annotations

from unittest.mock import MagicMock

from bluetooth import binary_values, device_of, sensor_values, service_info

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
    """Parser publishes voltage/%/battery-low and sw/hw versions from the advertisement."""
    parser = WolinkBluetoothDeviceData(PRESETS["290"])
    # PID=0x1234, AppVer=258, HwVer=772, DispVer=0x0506, battery 3000 mV
    mfr_bytes = bytes([0x12, 0x34, 0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x0B, 0xB8])

    update = parser.update(
        service_info("66:66:54:20:00:55", manufacturer_data={MANUFACTURER_ID: mfr_bytes})
    )
    assert update.title == '54200055 (2.9" BWRY)'
    device = device_of(update)
    assert device.name == "Zhsunyco 54200055"
    assert device.sw_version == "258"
    assert device.hw_version == "772"
    values = sensor_values(update)
    assert values["voltage"] == 3.0
    assert values["battery"] == 100
    assert binary_values(update)["battery"] is False

    # 2200 mV (0x0898): 0 % and battery low
    update = parser.update(
        service_info(
            "66:66:54:20:00:55",
            manufacturer_data={MANUFACTURER_ID: mfr_bytes[:8] + bytes([0x08, 0x98])},
        )
    )
    assert sensor_values(update)["battery"] == 0
    assert binary_values(update)["battery"] is True


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
