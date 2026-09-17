"""Support for Zhsunyco sensors."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import cast

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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util.dt import parse_datetime
from propcache.api import cached_property
from sensor_state_data import (
    SensorDeviceClass as ZhsunycoSensorDeviceClass,
    SensorUpdate,
    Units,
)

from .const import DOMAIN, SESSION_MAX_VOLTAGE, SESSION_MIN_VOLTAGE
from .coordinator import ZhsunycoPassiveBluetoothDataProcessor
from .device import (
    async_get_device_info,
    device_key_to_bluetooth_entity_key,
    hass_device_info,
)
from .types import ZhsunycoConfigEntry

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = {
    # Signal Strength (RSSI) (dBm) — passive advertisement
    (
        ZhsunycoSensorDeviceClass.SIGNAL_STRENGTH,
        Units.SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    ): SensorEntityDescription(
        key=f"{ZhsunycoSensorDeviceClass.SIGNAL_STRENGTH}_{Units.SIGNAL_STRENGTH_DECIBELS_MILLIWATT}",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    # Battery Percentage (%) — passive advertisement
    (
        ZhsunycoSensorDeviceClass.BATTERY,
        Units.PERCENTAGE,
    ): SensorEntityDescription(
        key=f"{ZhsunycoSensorDeviceClass.BATTERY}_{Units.PERCENTAGE}",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    # Battery Voltage (V) — passive advertisement
    (
        ZhsunycoSensorDeviceClass.VOLTAGE,
        Units.ELECTRIC_POTENTIAL_VOLT,
    ): SensorEntityDescription(
        key=f"{ZhsunycoSensorDeviceClass.VOLTAGE}_{Units.ELECTRIC_POTENTIAL_VOLT}",
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
    entry: ZhsunycoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Zhsunyco BLE sensors."""
    coordinator = entry.runtime_data
    processor = ZhsunycoPassiveBluetoothDataProcessor(
        sensor_update_to_bluetooth_data_update
    )
    entry.async_on_unload(
        processor.async_add_entities_listener(
            ZhsunycoBluetoothSensorEntity, async_add_entities
        )
    )
    entry.async_on_unload(
        coordinator.async_register_processor(
            processor, SensorEntityDescription
        )
    )

    backend = hass.data[DOMAIN][entry.entry_id]["backend"]
    caps = backend.capabilities

    battery_coordinator = hass.data[DOMAIN][entry.entry_id][
        "battery_coordinator"
    ]
    temperature_coordinator = hass.data[DOMAIN][entry.entry_id][
        "temperature_coordinator"
    ]
    duration_coordinator = hass.data[DOMAIN][entry.entry_id][
        "duration_coordinator"
    ]
    failure_coordinator = hass.data[DOMAIN][entry.entry_id][
        "failure_coordinator"
    ]
    last_failure_coordinator = hass.data[DOMAIN][entry.entry_id][
        "last_failure_coordinator"
    ]

    entities: list[SensorEntity] = [
        ZhsunycoDurationSensorEntity(hass, entry, duration_coordinator),
        ZhsunycoFailureCountSensorEntity(hass, entry, failure_coordinator),
        ZhsunycoLastFailureTimeSensorEntity(
            hass, entry, last_failure_coordinator
        ),
    ]

    if caps.session_battery and not caps.passive_battery:
        entities.extend([
            ZhsunycoBatteryPercentageSensorEntity(
                hass, entry, battery_coordinator
            ),
            ZhsunycoBatteryVoltageSensorEntity(
                hass, entry, battery_coordinator
            ),
        ])

    if caps.session_temperature:
        entities.append(
            ZhsunycoTemperatureSensorEntity(hass, entry, temperature_coordinator)
        )

    async_add_entities(entities)


class ZhsunycoBluetoothSensorEntity(
    PassiveBluetoothProcessorEntity[
        ZhsunycoPassiveBluetoothDataProcessor[float | None]
    ],
    SensorEntity,
):
    """Representation of a Zhsunyco BLE passive sensor."""

    @property
    def native_value(self) -> int | float | datetime | None:
        """Return the native value."""
        value = self.processor.entity_data.get(self.entity_key)
        if isinstance(value, str) and parse_datetime(value):
            value = parse_datetime(value)
        return value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available


class ZhsunycoBatteryPercentageSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[float | None]],
    SensorEntity,
):
    """Representation of a Zhsunyco battery percentage sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[float | None],
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"zhsunyco_{self._identifier}_battery"

    @property
    def native_value(self) -> int | None:
        volt = self.coordinator.data
        if volt is None:
            return None
        pct = (volt - SESSION_MIN_VOLTAGE) * 100.0 / (
            SESSION_MAX_VOLTAGE - SESSION_MIN_VOLTAGE
        )
        return max(0, min(100, round(pct)))

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True


class ZhsunycoBatteryVoltageSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[float | None]],
    SensorEntity,
):
    """Representation of a Zhsunyco battery voltage sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery_voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[float | None],
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"zhsunyco_{self._identifier}_battery_voltage"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True


class ZhsunycoTemperatureSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[int | None]],
    SensorEntity,
):
    """Representation of a Zhsunyco temperature sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[int | None],
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"zhsunyco_{self._identifier}_temperature"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True


class ZhsunycoDurationSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[float]],
    SensorEntity,
):
    """Representation of a Zhsunyco BLE write duration sensor."""

    _attr_has_entity_name = True
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
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"zhsunyco_{self._identifier}_write_duration"
        self._native_value: float = 0.0

    @property
    def native_value(self) -> float | None:
        return self._native_value

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True

    @property
    def data(self) -> float:
        return self.coordinator.data

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Updated duration data: %s", self.data)
        self._native_value = self.data
        super()._handle_coordinator_update()


class ZhsunycoFailureCountSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[int]],
    SensorEntity,
):
    """Representation of a Zhsunyco BLE write failure count sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "failure_count"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:alert-circle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[int],
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"zhsunyco_{self._identifier}_failure_count"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True


class ZhsunycoLastFailureTimeSensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[datetime | None]],
    SensorEntity,
):
    """Representation of a Zhsunyco BLE write last failure time sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_failure_time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-alert"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[datetime | None],
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"zhsunyco_{self._identifier}_last_failure_time"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True
