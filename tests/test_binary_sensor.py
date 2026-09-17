"""Tests for Zhsunyco binary sensor entities."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from custom_components.zhsunyco.binary_sensor import (
    ZhsunycoBatteryLowBinarySensor,
    ZhsunycoBluetoothConnectivitySensorEntity,
    ZhsunycoDisplayInSyncBinarySensor,
    async_setup_entry,
)
from custom_components.zhsunyco.const import DOMAIN
from custom_components.zhsunyco.zhsunyco_ble.base import BleBackend, Capabilities


def test_bluetooth_connectivity_sensor():
    """Verify bluetooth connectivity binary sensor entity."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"address": "66:66:54:20:00:55"}}}

    coordinator = MagicMock()
    coordinator.data = True

    sensor = ZhsunycoBluetoothConnectivitySensorEntity(hass, entry, coordinator)
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC or sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY or sensor._attr_device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert sensor.unique_id == "zhsunyco_54200055_connectivity"

    sensor._handle_coordinator_update()
    assert sensor.is_on is True

    coordinator.data = False
    sensor._handle_coordinator_update()
    assert sensor.is_on is False


def test_display_in_sync_sensor():
    """Verify display synchronization binary sensor entity."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"address": "66:66:54:20:00:55"}}}

    image_coord = MagicMock()
    preview_coord = MagicMock()

    sensor = ZhsunycoDisplayInSyncBinarySensor(
        hass, entry, image_coord, preview_coord
    )
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC or sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.unique_id == "zhsunyco_54200055_display_in_sync"

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
        entry.runtime_data = MagicMock()

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
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    "address": "66:66:54:20:00:55",
                    "backend": backend_passive,
                    "battery_coordinator": MagicMock(),
                    "connectivity_coordinator": MagicMock(),
                    "image_coordinator": MagicMock(),
                    "preview_coordinator": MagicMock(),
                }
            }
        }

        added_entities = []
        await async_setup_entry(hass, entry, added_entities.extend)

        assert len(added_entities) == 2
        types = [type(e) for e in added_entities]
        assert ZhsunycoBluetoothConnectivitySensorEntity in types
        assert ZhsunycoDisplayInSyncBinarySensor in types

        # Session-battery backend (easyTag): coordinator-based battery low added.
        backend_session = MagicMock(spec=BleBackend)
        backend_session.capabilities = Capabilities(
            passive_battery=False,
            session_battery=True,
            session_temperature=True,
            model_detection=False,
            palettes=("BWR",),
        )
        hass.data[DOMAIN]["test_entry"]["backend"] = backend_session

        added_session = []
        await async_setup_entry(hass, entry, added_session.extend)
        assert len(added_session) == 3
        assert ZhsunycoBatteryLowBinarySensor in [type(e) for e in added_session]

    asyncio.run(_test())


def test_battery_low_binary_sensor():
    """Battery low is on at or below the session minimum voltage."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"address": "66:66:54:20:00:55"}}}

    coordinator = MagicMock()
    sensor = ZhsunycoBatteryLowBinarySensor(hass, entry, coordinator)
    assert sensor.unique_id == "zhsunyco_54200055_battery_low"
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
