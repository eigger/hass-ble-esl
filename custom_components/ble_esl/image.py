"""Support for a single image URL as an ImageEntity."""

from __future__ import annotations

import logging

from homeassistant.components.image import Image, ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .entity import BleEslCoordinatorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLE ESL image entities."""
    data = entry.runtime_data
    async_add_entities([
        BleEslImageEntity(hass, entry, data.image_coordinator),
        BleEslPreviewImageEntity(hass, entry, data.preview_coordinator),
    ])


class _BleEslImageBase(BleEslCoordinatorEntity[bytes], ImageEntity):
    """Image entity whose PNG bytes come from a coordinator."""

    _attr_content_type = "image/png"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[bytes],
    ) -> None:
        super().__init__(hass, entry, coordinator)
        ImageEntity.__init__(self, hass)
        self._cached_image = Image(content_type="image/png", content=coordinator.data)

    def image(self) -> bytes | None:
        """Return bytes of image."""
        return self._cached_image.content

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Updated image data for %s", self._attr_unique_id)
        self._cached_image = Image(content_type="image/png", content=self.data)
        self._attr_image_last_updated = dt_util.now()
        super()._handle_coordinator_update()


class BleEslImageEntity(_BleEslImageBase):
    """Representation of last updated image content."""

    _key = "last_updated_content"
    _attr_translation_key = "last_updated_content"



class BleEslPreviewImageEntity(_BleEslImageBase):
    """Representation of preview image content."""

    _key = "preview_content_image"
    _attr_translation_key = "preview_content"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

