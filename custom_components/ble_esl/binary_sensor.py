"""Support for BLE ESL binary sensors."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataUpdate,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from propcache.api import cached_property
from sensor_state_data import (
    BinarySensorDeviceClass as BleEslBinarySensorDeviceClass,
    SensorUpdate,
)

from .const import DOMAIN, SESSION_MIN_VOLTAGE
from .coordinator import BleEslPassiveBluetoothDataProcessor
from .device import (
    async_get_device_info,
    device_key_to_bluetooth_entity_key,
    hass_device_info,
)
from .types import BleEslConfigEntry

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_DESCRIPTIONS = {
    # Battery low: on when the advertised voltage is at or below the level where
    # e-paper refresh becomes unreliable even though BLE still works.
    BleEslBinarySensorDeviceClass.BATTERY: BinarySensorEntityDescription(
        key=BleEslBinarySensorDeviceClass.BATTERY,
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


def sensor_update_to_bluetooth_data_update(
    sensor_update: SensorUpdate,
) -> PassiveBluetoothDataUpdate[bool | None]:
    """Convert a sensor update to a bluetooth data update."""
    return PassiveBluetoothDataUpdate(
        devices={
            device_id: hass_device_info(device_info)
            for device_id, device_info in sensor_update.devices.items()
        },
        entity_descriptions={
            device_key_to_bluetooth_entity_key(device_key): BINARY_SENSOR_DESCRIPTIONS[
                description.device_class
            ]
            for device_key, description in sensor_update.binary_entity_descriptions.items()
            if description.device_class in BINARY_SENSOR_DESCRIPTIONS
        },
        entity_data={
            device_key_to_bluetooth_entity_key(device_key): sensor_values.native_value
            for device_key, sensor_values in sensor_update.binary_entity_values.items()
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BleEslConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BLE ESL binary sensors."""
    coordinator = entry.runtime_data
    processor = BleEslPassiveBluetoothDataProcessor(
        sensor_update_to_bluetooth_data_update
    )
    entry.async_on_unload(
        processor.async_add_entities_listener(
            BleEslBluetoothBinarySensorEntity, async_add_entities
        )
    )
    entry.async_on_unload(
        coordinator.async_register_processor(
            processor, BinarySensorEntityDescription
        )
    )

    entry_data = hass.data[DOMAIN][entry.entry_id]
    connectivity_coordinator = entry_data["connectivity_coordinator"]
    image_coordinator = entry_data["image_coordinator"]
    preview_coordinator = entry_data["preview_coordinator"]
    entities: list[BinarySensorEntity] = [
        BleEslBluetoothConnectivitySensorEntity(hass, entry, connectivity_coordinator),
        BleEslDisplayInSyncBinarySensor(hass, entry, image_coordinator, preview_coordinator),
    ]

    backend = entry_data.get("backend")
    caps = backend.capabilities if backend else None
    if caps and caps.session_battery and not caps.passive_battery:
        entities.append(
            BleEslBatteryLowBinarySensor(
                hass, entry, entry_data["battery_coordinator"]
            )
        )

    async_add_entities(entities)


class BleEslBluetoothBinarySensorEntity(
    PassiveBluetoothProcessorEntity[
        BleEslPassiveBluetoothDataProcessor[bool | None]
    ],
    BinarySensorEntity,
):
    """Representation of a BLE ESL binary sensor."""

    @property
    def is_on(self) -> bool | None:
        """Return the native value."""
        return self.processor.entity_data.get(self.entity_key)


class BleEslBatteryLowBinarySensor(
    CoordinatorEntity[DataUpdateCoordinator[float | None]],
    BinarySensorEntity,
):
    """Battery-low binary sensor for session-polled battery voltage."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
        self._attr_unique_id = f"ble_esl_{self._identifier}_battery_low"

    @property
    def is_on(self) -> bool | None:
        volt = self.coordinator.data
        if volt is None:
            return None
        return volt <= SESSION_MIN_VOLTAGE

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True


class BleEslBluetoothConnectivitySensorEntity(
    CoordinatorEntity[DataUpdateCoordinator[bool]],
    BinarySensorEntity,
):
    """Representation of a BLE ESL connectivity binary sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: DataUpdateCoordinator[bool]):
        super().__init__(coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"ble_esl_{self._identifier}_connectivity"
        self._is_on = False

    @property
    def is_on(self) -> bool | None:
        """Return the native value."""
        return self._is_on

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        """Entity always available."""
        return True

    @property
    def data(self) -> bool:
        """Return coordinator data for this entity."""
        return self.coordinator.data

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Updated connectivity binary data")
        self._is_on = self.data
        super()._handle_coordinator_update()


class BleEslDisplayInSyncBinarySensor(
    CoordinatorEntity[DataUpdateCoordinator[bytes | None]],
    BinarySensorEntity,
):
    """Representation of a BLE ESL display synchronization binary sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "display_in_sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        image_coordinator: DataUpdateCoordinator[bytes | None],
        preview_coordinator: DataUpdateCoordinator[bytes | None],
    ):
        super().__init__(image_coordinator)
        self.hass = hass
        self._entry_id = entry.entry_id
        self._preview_coordinator = preview_coordinator
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"ble_esl_{self._identifier}_display_in_sync"

    @property
    def is_on(self) -> bool | None:
        img = self.coordinator.data
        pre = self._preview_coordinator.data
        if img is None or pre is None:
            return None
        return img == pre

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._preview_coordinator.async_add_listener(
                self._handle_coordinator_update
            )
        )
