"""Tests for Zhsunyco sensor entities and capabilities-based setup."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.zhsunyco.const import DOMAIN
from custom_components.zhsunyco.zhsunyco_ble.base import Capabilities, BleBackend
from custom_components.zhsunyco.sensor import (
    ZhsunycoBatteryPercentageSensorEntity,
    ZhsunycoBatteryVoltageSensorEntity,
    ZhsunycoDurationSensorEntity,
    ZhsunycoFailureCountSensorEntity,
    ZhsunycoLastFailureTimeSensorEntity,
    ZhsunycoTemperatureSensorEntity,
    async_setup_entry,
)


def test_battery_percentage_sensor():
    """Verify battery percentage mapping with 2.2V - 3.0V linear formula (integer)."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"address": "66:66:54:20:00:55"}}}

    coordinator = MagicMock()
    coordinator.data = 3.0

    sensor = ZhsunycoBatteryPercentageSensorEntity(hass, entry, coordinator)
    assert sensor.native_value == 100
    assert isinstance(sensor.native_value, int)
    assert sensor.unique_id == "zhsunyco_54200055_battery"

    coordinator.data = 2.6
    assert sensor.native_value == 50

    coordinator.data = 2.2
    assert sensor.native_value == 0

    # Over-voltage capping
    coordinator.data = 3.2
    assert sensor.native_value == 100

    # Under-voltage capping
    coordinator.data = 2.0
    assert sensor.native_value == 0

    # None data
    coordinator.data = None
    assert sensor.native_value is None


def test_battery_voltage_sensor():
    """Verify battery voltage entity."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"address": "66:66:54:20:00:55"}}}

    coordinator = MagicMock()
    coordinator.data = 2.95

    sensor = ZhsunycoBatteryVoltageSensorEntity(hass, entry, coordinator)
    assert sensor.native_value == 2.95
    assert sensor.unique_id == "zhsunyco_54200055_battery_voltage"


def test_temperature_sensor():
    """Verify temperature entity."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"address": "66:66:54:20:00:55"}}}

    coordinator = MagicMock()
    coordinator.data = 25

    sensor = ZhsunycoTemperatureSensorEntity(hass, entry, coordinator)
    assert sensor.native_value == 25
    assert sensor.unique_id == "zhsunyco_54200055_temperature"

    coordinator.data = -10
    assert sensor.native_value == -10


def test_duration_and_failure_sensors():
    """Verify write duration and failure entities."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    hass.data = {DOMAIN: {"test_entry": {"address": "66:66:54:20:00:55"}}}

    dur_coord = MagicMock()
    dur_coord.data = 4.5
    dur_sensor = ZhsunycoDurationSensorEntity(hass, entry, dur_coord)
    dur_sensor._handle_coordinator_update()
    assert dur_sensor.native_value == 4.5

    fail_coord = MagicMock()
    fail_coord.data = 2
    fail_sensor = ZhsunycoFailureCountSensorEntity(hass, entry, fail_coord)
    assert fail_sensor.native_value == 2

    last_fail_coord = MagicMock()
    last_fail_coord.data = None
    last_fail_sensor = ZhsunycoLastFailureTimeSensorEntity(
        hass, entry, last_fail_coord
    )
    assert last_fail_sensor.native_value is None


def test_async_setup_entry_capabilities():
    """Verify capability-based sensor entity creation in async_setup_entry."""

    async def _test():
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.runtime_data = MagicMock()

        # Case 1: WOLINK protocol (passive_battery=True, session_battery=False, session_temperature=False)
        backend_wolink = MagicMock(spec=BleBackend)
        backend_wolink.capabilities = Capabilities(
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
                    "backend": backend_wolink,
                    "battery_coordinator": MagicMock(),
                    "temperature_coordinator": MagicMock(),
                    "duration_coordinator": MagicMock(),
                    "failure_coordinator": MagicMock(),
                    "last_failure_coordinator": MagicMock(),
                }
            }
        }

        added_entities = []
        await async_setup_entry(hass, entry, added_entities.extend)

        # 3 base entities (duration, failure count, last failure time)
        assert len(added_entities) == 3
        types = [type(e) for e in added_entities]
        assert ZhsunycoDurationSensorEntity in types
        assert ZhsunycoFailureCountSensorEntity in types
        assert ZhsunycoLastFailureTimeSensorEntity in types
        assert ZhsunycoTemperatureSensorEntity not in types

        # Case 2: Session battery & temperature (e.g. easyTag)
        backend_session = MagicMock(spec=BleBackend)
        backend_session.capabilities = Capabilities(
            passive_battery=False,
            session_battery=True,
            session_temperature=True,
            model_detection=False,
            palettes=("BWR",),
        )
        hass.data[DOMAIN]["test_entry"]["backend"] = backend_session

        added_session_entities = []
        await async_setup_entry(hass, entry, added_session_entities.extend)

        # 3 base + 2 session battery + 1 temperature = 6 entities
        assert len(added_session_entities) == 6
        session_types = [type(e) for e in added_session_entities]
        assert ZhsunycoBatteryPercentageSensorEntity in session_types
        assert ZhsunycoBatteryVoltageSensorEntity in session_types
        assert ZhsunycoTemperatureSensorEntity in session_types

    asyncio.run(_test())
