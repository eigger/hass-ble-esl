"""Tests for easyTag advertisement parser and supported matchers."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.ble_esl.esl_ble.easytag.const import SERVICE_UUID
from custom_components.ble_esl.esl_ble.easytag.devices import PRESETS
from custom_components.ble_esl.esl_ble.easytag.parser import (
    EasyTagBluetoothDeviceData,
    is_easytag_advertisement,
)


def test_easytag_parser_supported():
    """Verify easyTag matcher by service UUID and local name."""
    parser = EasyTagBluetoothDeviceData(PRESETS["3D"])

    # Match by Service UUID
    info_uuid = MagicMock()
    info_uuid.service_uuids = [SERVICE_UUID]
    info_uuid.name = None
    info_uuid.manufacturer_data = {}
    assert is_easytag_advertisement(info_uuid) is True
    assert parser.supported(info_uuid) is True

    # Match by Local Name
    info_name = MagicMock()
    info_name.service_uuids = []
    info_name.name = "easyTag3D:00:11:22"
    info_name.manufacturer_data = {}
    assert is_easytag_advertisement(info_name) is True
    assert parser.supported(info_name) is True

    # Non-matching advertisement
    info_other = MagicMock()
    info_other.service_uuids = ["0000ffff-0000-1000-8000-00805f9b34fb"]
    info_other.name = "OtherDevice"
    info_other.manufacturer_data = {48042: b"\x00"}
    assert is_easytag_advertisement(info_other) is False
    assert parser.supported(info_other) is False


def test_easytag_parser_device_info():
    """Verify easyTag parser sets device naming and title."""
    parser = EasyTagBluetoothDeviceData(PRESETS["3D"])

    info = MagicMock()
    info.address = "3D:00:00:E5:7D:76"
    info.service_uuids = [SERVICE_UUID]
    info.name = "easyTag"
    info.manufacturer_data = {}

    parser._start_update(info)

    assert parser.title == "00E57D76 (2.9\" BWR (ET0290-3DB))"
    assert parser.get_device_name() == "Zhsunyco 00E57D76"
