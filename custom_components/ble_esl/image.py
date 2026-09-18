"""Support for a single image URL as an ImageEntity."""

from __future__ import annotations

import logging

from homeassistant.components.image import Image, ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util
from propcache.api import cached_property

from .const import DOMAIN
from .device import async_get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLE ESL image entities."""
    image_coordinator = hass.data[DOMAIN][entry.entry_id]["image_coordinator"]
    preview_coordinator = hass.data[DOMAIN][entry.entry_id]["preview_coordinator"]
    async_add_entities([
        BleEslImageEntity(hass, entry, image_coordinator),
        BleEslPreviewImageEntity(hass, entry, preview_coordinator),
    ])


class BleEslImageEntity(CoordinatorEntity[DataUpdateCoordinator[bytes]], ImageEntity):
    """Representation of last updated image content."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_updated_content"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: DataUpdateCoordinator[bytes]):
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"ble_esl_{self._identifier}_last_updated_content"
        self._attr_content_type = "image/png"
        self._cached_image = Image(content_type="image/png", content=coordinator.data)

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        """Entity always available."""
        return True

    @property
    def data(self) -> bytes:
        """Return coordinator data for this entity."""
        return self.coordinator.data

    def image(self) -> bytes | None:
        """Return bytes of image."""
        return self._cached_image.content

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Updated image data")
        self._cached_image = Image(content_type="image/png", content=self.data)
        self._attr_image_last_updated = dt_util.now()
        super()._handle_coordinator_update()


class BleEslPreviewImageEntity(CoordinatorEntity[DataUpdateCoordinator[bytes]], ImageEntity):
    """Representation of preview image content."""

    _attr_has_entity_name = True
    _attr_translation_key = "preview_content"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: DataUpdateCoordinator[bytes]):
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"ble_esl_{self._identifier}_preview_content_image"
        self._attr_content_type = "image/png"
        self._cached_image = Image(content_type="image/png", content=coordinator.data)

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True

    @property
    def data(self) -> bytes:
        return self.coordinator.data

    def image(self) -> bytes | None:
        return self._cached_image.content

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Updated preview image data")
        self._cached_image = Image(content_type="image/png", content=self.data)
        self._attr_image_last_updated = dt_util.now()
        super()._handle_coordinator_update()
