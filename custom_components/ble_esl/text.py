import logging

from homeassistant.components.text import RestoreText, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import BleEslEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLE ESL text entities."""
    async_add_entities([BleEslTextEntity(hass, entry)])


class BleEslTextEntity(BleEslEntity, RestoreText):
    """Text entity for setting device alias."""

    _key = "alias"
    _attr_translation_key = "alias"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_max = 32
    _attr_native_min = 0
    _attr_mode = TextMode.TEXT

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._bind_tag(hass, entry)
        self._attr_native_value = self._identifier

    def set_value(self, value: str) -> None:
        """Change the selected option."""
        self._attr_native_value = value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_text_data := await self.async_get_last_text_data()) is None:
            return
        _LOGGER.debug("Restored state: %s", last_text_data)
        self._attr_native_max = last_text_data.native_max
        self._attr_native_min = last_text_data.native_min
        self._attr_native_value = last_text_data.native_value
