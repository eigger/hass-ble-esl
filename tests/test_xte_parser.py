"""Tests for XTE advertisement parser and supported matchers."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from bt import binary_values, sensor_values, service_info, update_device
import pytest

from custom_components.ble_esl.esl_ble.xte.const import MANUFACTURER_ID
from custom_components.ble_esl.esl_ble.xte.devices import PRESETS
from custom_components.ble_esl.esl_ble.xte.parser import (
    XteBluetoothDeviceData,
    is_xte_advertisement,
)

PSJ_420 = PRESETS["psj-420"]
PSJ_213 = PRESETS["psj-213"]


def advertisement(tail=0x1E, payload=None, address="AA:BB:CC:DD:EE:FF"):
    if payload is None:
        payload = bytes.fromhex("fd024002009964060102ffff") + bytes([tail])
    return service_info(address, manufacturer_data={MANUFACTURER_ID: payload})


def test_parser_supported():
    """Verify XTE advertisement matcher."""
    parser = XteBluetoothDeviceData(PSJ_420)

    # Valid XTE advertisement with manufacturer id 0x5258
    assert is_xte_advertisement(advertisement()) is True
    assert parser.supported(advertisement()) is True

    # Non-matching advertisements
    info_other = MagicMock()
    info_other.manufacturer_data = {0x1234: b"\x00" * 10}
    info_other.service_uuids = []
    assert is_xte_advertisement(info_other) is False
    assert parser.supported(info_other) is False

    info_empty = MagicMock()
    info_empty.manufacturer_data = {}
    info_empty.service_uuids = []
    assert is_xte_advertisement(info_empty) is False
    assert parser.supported(info_empty) is False


@pytest.mark.parametrize("tail", [0x1E, 0x1B])
def test_parser_update_battery_and_versions(tail):
    """Parser publishes battery % and sw/hw versions from advertisement."""
    parser = XteBluetoothDeviceData(PSJ_420)
    info = advertisement(tail)
    update = parser.update(info)

    device = update_device(update)
    assert device.manufacturer == "Poshiji"
    assert "PSJ-420" in device.model
    assert device.sw_version == "4.0.2"
    assert device.hw_version == "2"

    values = sensor_values(update)
    assert values["battery"] == 100
    assert binary_values(update)["battery"] is False
    assert set(values) == {"signal_strength", "battery"}  # no temperature


def test_parser_identity_survives_battery_and_firmware_changes():
    """The model is the device number; battery and firmware bytes may change."""
    parser = XteBluetoothDeviceData(PSJ_420)
    drained = advertisement(payload=bytes.fromhex("fd024103009905060102ffff1b"))

    assert is_xte_advertisement(drained) is True
    assert parser.supported(drained) is True

    update = parser.update(drained)
    device = update_device(update)
    assert device.sw_version == "4.1.3"
    assert sensor_values(update)["battery"] == 5
    assert binary_values(update)["battery"] is True


def test_parser_unknown_device_number_reported_once(caplog):
    """An uncaptured device number is claimed and reported to log once."""
    parser = XteBluetoothDeviceData(PRESETS["psj-290"])
    unknown = advertisement(
        address="11:22:33:44:55:66", payload=bytes.fromhex("fd024002008d63060102ffff1c")
    )

    with caplog.at_level(logging.INFO, logger="custom_components.ble_esl.esl_ble.xte"):
        assert is_xte_advertisement(unknown) is True
        assert parser.supported(unknown) is True
        # Repeated call should not re-log
        assert is_xte_advertisement(unknown) is True

    reports = [r for r in caplog.records if "unknown device number" in r.message]
    assert len(reports) == 1
    assert "device number 141" in reports[0].message
    assert "4.0.2" in reports[0].message
    assert "fd024002008d63060102ffff1c" in reports[0].message


def test_tag_label_is_the_address_reversed():
    """The label prints the address bytes in reverse; names and titles follow it."""
    label = XteBluetoothDeviceData.tag_label
    assert label("B9:B9:00:18:39:37") == "37391800B9B9"
    assert label("4D:BD:10:18:39:37") == "37391810BD4D"
    assert label("4f:9a:10:17:39:37") == "373917109A4F"

    info = advertisement(
        address="B9:B9:00:18:39:37", payload=bytes.fromhex("0402400300996406ff01ffff1c")
    )
    parser = XteBluetoothDeviceData(PRESETS["psj-420"])
    device = update_device(parser.update(info))
    assert device.name == "Poshiji 37391800B9B9"
