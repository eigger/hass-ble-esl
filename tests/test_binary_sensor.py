"""Tests for BLE ESL binary sensor entities."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from conftest import make_entry, make_runtime_data
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from custom_components.ble_esl.binary_sensor import (
    BleEslBatteryLowBinarySensor,
    BleEslBluetoothConnectivitySensorEntity,
    BleEslDisplayInSyncBinarySensor,
    async_setup_entry,
)
from custom_components.ble_esl.esl_ble.base import BleBackend, Capabilities


def test_bluetooth_connectivity_sensor():
    """Verify bluetooth connectivity binary sensor entity."""
    hass = MagicMock()
    entry = make_entry()

    coordinator = MagicMock()
    coordinator.data = True

    sensor = BleEslBluetoothConnectivitySensorEntity(hass, entry, coordinator)
    assert (
        sensor.entity_category == EntityCategory.DIAGNOSTIC
        or sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    )
    assert (
        sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
        or sensor._attr_device_class == BinarySensorDeviceClass.CONNECTIVITY
    )
    assert sensor.unique_id == "ble_esl_54200055_connectivity"

    sensor._handle_coordinator_update()
    assert sensor.is_on is True

    coordinator.data = False
    sensor._handle_coordinator_update()
    assert sensor.is_on is False


def test_display_in_sync_sensor():
    """Verify display synchronization binary sensor entity."""
    hass = MagicMock()
    entry = make_entry()

    image_coord = MagicMock()
    preview_coord = MagicMock()

    sensor = BleEslDisplayInSyncBinarySensor(hass, entry, image_coord, preview_coord)
    assert (
        sensor.entity_category == EntityCategory.DIAGNOSTIC
        or sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    )
    assert sensor.unique_id == "ble_esl_54200055_display_in_sync"

    # Both None
    image_coord.data = None
    preview_coord.data = None
    assert sensor.is_on is None

    # One None
    image_coord.data = b"image_data"
    preview_coord.data = None
    assert sensor.is_on is None

    # Equal
    image_coord.data = b"same_data"
    preview_coord.data = b"same_data"
    assert sensor.is_on is True

    # Different
    image_coord.data = b"data_a"
    preview_coord.data = b"data_b"
    assert sensor.is_on is False


def test_async_setup_entry_binary_sensor():
    """Verify binary sensor setup."""

    async def _test():
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_entry"

        # Passive-battery backend (WOLINK / PickSmart): battery low comes from
        # the passive processor, so no coordinator-based entity is added.
        backend_passive = MagicMock(spec=BleBackend)
        backend_passive.capabilities = Capabilities(
            passive_battery=True,
            session_battery=False,
            session_temperature=False,
            model_detection=False,
            palettes=("BWRY",),
        )
        entry.runtime_data = make_runtime_data(backend=backend_passive)

        added_entities = []
        await async_setup_entry(hass, entry, added_entities.extend)

        assert len(added_entities) == 2
        types = [type(e) for e in added_entities]
        assert BleEslBluetoothConnectivitySensorEntity in types
        assert BleEslDisplayInSyncBinarySensor in types

        # Session-battery backend (easyTag): coordinator-based battery low added.
        backend_session = MagicMock(spec=BleBackend)
        backend_session.capabilities = Capabilities(
            passive_battery=False,
            session_battery=True,
            session_temperature=True,
            model_detection=False,
            palettes=("BWR",),
        )
        entry.runtime_data = make_runtime_data(backend=backend_session)

        added_session = []
        await async_setup_entry(hass, entry, added_session.extend)
        assert len(added_session) == 3
        assert BleEslBatteryLowBinarySensor in [type(e) for e in added_session]

    asyncio.run(_test())


def test_battery_low_binary_sensor():
    """Battery low is on at or below the session minimum voltage."""
    hass = MagicMock()
    entry = make_entry()

    coordinator = MagicMock()
    sensor = BleEslBatteryLowBinarySensor(hass, entry, coordinator)
    assert sensor.unique_id == "ble_esl_54200055_battery_low"
    assert sensor.device_class == BinarySensorDeviceClass.BATTERY
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    coordinator.data = 3.0
    assert sensor.is_on is False
    coordinator.data = 2.2
    assert sensor.is_on is True
    coordinator.data = 2.0
    assert sensor.is_on is True
    coordinator.data = None
    assert sensor.is_on is None
