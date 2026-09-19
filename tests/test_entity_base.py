"""Tests for the shared entity base: unique ids, device info, availability."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import ADDRESS, make_entry
import pytest

from custom_components.ble_esl.binary_sensor import (
    BleEslBatteryLowBinarySensor,
    BleEslBluetoothConnectivitySensorEntity,
    BleEslDisplayInSyncBinarySensor,
)
from custom_components.ble_esl.image import BleEslImageEntity, BleEslPreviewImageEntity
from custom_components.ble_esl.sensor import (
    BleEslBatteryPercentageSensorEntity,
    BleEslBatteryVoltageSensorEntity,
    BleEslDurationSensorEntity,
    BleEslFailureCountSensorEntity,
    BleEslLastFailureTimeSensorEntity,
    BleEslTemperatureSensorEntity,
)
from custom_components.ble_esl.switch import BleEslWriteLockSwitch
from custom_components.ble_esl.text import BleEslTextEntity

IDENT = "54200055"


def _hass_entry():
    return MagicMock(), make_entry()


def _coord(data=None):
    coordinator = MagicMock()
    coordinator.data = data
    return coordinator


# Every unique-id suffix in one place: changing one silently orphans the
# entity in users' registries.
EXPECTED_UNIQUE_IDS = [
    (lambda h, e: BleEslBatteryPercentageSensorEntity(h, e, _coord()), "battery"),
    (lambda h, e: BleEslBatteryVoltageSensorEntity(h, e, _coord()), "battery_voltage"),
    (lambda h, e: BleEslTemperatureSensorEntity(h, e, _coord()), "temperature"),
    (lambda h, e: BleEslDurationSensorEntity(h, e, _coord()), "write_duration"),
    (lambda h, e: BleEslFailureCountSensorEntity(h, e, _coord()), "failure_count"),
    (lambda h, e: BleEslLastFailureTimeSensorEntity(h, e, _coord()), "last_failure_time"),
    (lambda h, e: BleEslBatteryLowBinarySensor(h, e, _coord()), "battery_low"),
    (lambda h, e: BleEslBluetoothConnectivitySensorEntity(h, e, _coord()), "connectivity"),
    (lambda h, e: BleEslDisplayInSyncBinarySensor(h, e, _coord(), _coord()), "display_in_sync"),
    (lambda h, e: BleEslImageEntity(h, e, _coord(b"")), "last_updated_content"),
    (lambda h, e: BleEslPreviewImageEntity(h, e, _coord(b"")), "preview_content_image"),
    (lambda h, e: BleEslWriteLockSwitch(h, e), "write_lock"),
    (lambda h, e: BleEslTextEntity(h, e), "alias"),
]


@pytest.mark.parametrize(("make", "suffix"), EXPECTED_UNIQUE_IDS, ids=[s for _, s in EXPECTED_UNIQUE_IDS])
def test_unique_id_and_binding(make, suffix):
    hass, entry = _hass_entry()
    entity = make(hass, entry)

    assert entity.unique_id == f"ble_esl_{IDENT}_{suffix}"
    assert entity._address == ADDRESS
    assert entity._entry_id == "test_entry"
    assert entity.available is True
    assert entity._attr_has_entity_name is True

    info = entity.device_info
    assert ("bluetooth", ADDRESS) in info["connections"]
    assert info["name"].endswith(IDENT)


def test_text_entity_defaults_to_identifier():
    hass, entry = _hass_entry()
    assert BleEslTextEntity(hass, entry)._attr_native_value == IDENT
