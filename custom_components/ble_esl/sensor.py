"""Support for BLE ESL sensors."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, cast

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataUpdate,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from sensor_state_data import (
    SensorDeviceClass as BleEslSensorDeviceClass,
    SensorUpdate,
    Units,
)

from .const import SESSION_MAX_VOLTAGE, SESSION_MIN_VOLTAGE
from .coordinator import BleEslPassiveBluetoothDataProcessor
from .device import device_key_to_bluetooth_entity_key, hass_device_info
from .entity import BleEslCoordinatorEntity
from .esl_ble.base import battery_percent
from .types import BleEslConfigEntry

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = {
    # Signal Strength (RSSI) (dBm) — passive advertisement
    (
        BleEslSensorDeviceClass.SIGNAL_STRENGTH,
        Units.SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    ): SensorEntityDescription(
        key=f"{BleEslSensorDeviceClass.SIGNAL_STRENGTH}_{Units.SIGNAL_STRENGTH_DECIBELS_MILLIWATT}",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    # Battery Percentage (%) — passive advertisement
    (
        BleEslSensorDeviceClass.BATTERY,
        Units.PERCENTAGE,
    ): SensorEntityDescription(
        key=f"{BleEslSensorDeviceClass.BATTERY}_{Units.PERCENTAGE}",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    # Battery Voltage (V) — passive advertisement
    (
        BleEslSensorDeviceClass.VOLTAGE,
        Units.ELECTRIC_POTENTIAL_VOLT,
    ): SensorEntityDescription(
        key=f"{BleEslSensorDeviceClass.VOLTAGE}_{Units.ELECTRIC_POTENTIAL_VOLT}",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
    ),
}


def sensor_update_to_bluetooth_data_update(
    sensor_update: SensorUpdate,
) -> PassiveBluetoothDataUpdate[float | None]:
    """Convert a sensor update to a bluetooth data update."""
    return PassiveBluetoothDataUpdate(
        devices={
            device_id: hass_device_info(device_info)
            for device_id, device_info in sensor_update.devices.items()
        },
        entity_descriptions={
            device_key_to_bluetooth_entity_key(device_key): SENSOR_DESCRIPTIONS[
                (
                    description.device_class,
                    description.native_unit_of_measurement,
                )
            ]
            for device_key, description in sensor_update.entity_descriptions.items()
            if description.device_class
            and (
                description.device_class,
                description.native_unit_of_measurement,
            )
            in SENSOR_DESCRIPTIONS
        },
        entity_data={
            device_key_to_bluetooth_entity_key(device_key): cast(
                float | None, sensor_values.native_value
            )
            for device_key, sensor_values in sensor_update.entity_values.items()
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BleEslConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BLE ESL sensors."""
    data = entry.runtime_data
    processor = BleEslPassiveBluetoothDataProcessor(sensor_update_to_bluetooth_data_update)
    entry.async_on_unload(
        processor.async_add_entities_listener(BleEslBluetoothSensorEntity, async_add_entities)
    )
    entry.async_on_unload(
        data.bt_coordinator.async_register_processor(processor, SensorEntityDescription)
    )

    caps = data.backend.capabilities
    entities: list[SensorEntity] = [
        BleEslDurationSensorEntity(hass, entry, data.duration_coordinator),
        BleEslFailureCountSensorEntity(hass, entry, data.failure_coordinator),
        BleEslLastFailureTimeSensorEntity(hass, entry, data.last_failure_coordinator),
    ]
    if caps.session_battery and not caps.passive_battery:
        entities.extend(
            [
                BleEslBatteryPercentageSensorEntity(hass, entry, data.battery_coordinator),
                BleEslBatteryVoltageSensorEntity(hass, entry, data.battery_coordinator),
            ]
        )
    if caps.session_temperature:
        entities.append(BleEslTemperatureSensorEntity(hass, entry, data.temperature_coordinator))

    async_add_entities(entities)


class BleEslBluetoothSensorEntity(
    PassiveBluetoothProcessorEntity[BleEslPassiveBluetoothDataProcessor[float | None]],
    SensorEntity,
):
    """Representation of a BLE ESL passive sensor."""

    @property
    def native_value(self) -> float | None:
        """Return the native value."""
        return self.processor.entity_data.get(self.entity_key)


class BleEslBatteryPercentageSensorEntity(BleEslCoordinatorEntity[float | None], SensorEntity):
    """Representation of a BLE ESL battery percentage sensor."""

    _key = "battery"
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> int | None:
        volt = self.coordinator.data
        if volt is None:
            return None
        return battery_percent(volt, SESSION_MIN_VOLTAGE, SESSION_MAX_VOLTAGE)


class BleEslBatteryVoltageSensorEntity(BleEslCoordinatorEntity[float | None], SensorEntity):
    """Representation of a BLE ESL battery voltage sensor."""

    _key = "battery_voltage"
    _attr_translation_key = "battery_voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 1

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data


class BleEslTemperatureSensorEntity(BleEslCoordinatorEntity[int | None], SensorEntity):
    """Representation of a BLE ESL temperature sensor."""

    _key = "temperature"
    _attr_translation_key = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data


class BleEslDurationSensorEntity(BleEslCoordinatorEntity[float], SensorEntity):
    """Representation of a BLE ESL write duration sensor."""

    _key = "write_duration"
    _attr_translation_key = "write_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[float],
    ) -> None:
        super().__init__(hass, entry, coordinator)
        self._native_value: float = 0.0

    @property
    def native_value(self) -> float | None:
        return self._native_value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """The last write attempt's breakdown (attempt, success, error, and the
        per-stage timings such as connect_s / start_probes / round_trip_ms), so
        the write path can be monitored from the entity instead of debug logs.
        Each write's final duration update publishes it."""
        return self._data.last_write_timing

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Updated duration data: %s", self.data)
        self._native_value = self.data
        super()._handle_coordinator_update()


class BleEslFailureCountSensorEntity(BleEslCoordinatorEntity[int], SensorEntity):
    """Representation of a BLE ESL write failure count sensor."""

    _key = "failure_count"
    _attr_translation_key = "failure_count"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:alert-circle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data


class BleEslLastFailureTimeSensorEntity(BleEslCoordinatorEntity[datetime | None], SensorEntity):
    """Representation of a BLE ESL write last failure time sensor."""

    _key = "last_failure_time"
    _attr_translation_key = "last_failure_time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-alert"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data
