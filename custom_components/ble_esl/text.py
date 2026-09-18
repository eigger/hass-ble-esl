import logging

from homeassistant.components.text import RestoreText
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache.api import cached_property

from .const import DOMAIN
from .device import async_get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLE ESL text entities."""
    async_add_entities([BleEslTextEntity(hass, entry)])


class BleEslTextEntity(RestoreText):
    """Text entity for setting device alias."""

    _attr_has_entity_name = True
    _attr_translation_key = "alias"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self._entry_id = entry.entry_id
        address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._address = address
        self._identifier = address.replace(":", "")[-8:]
        self._attr_unique_id = f"ble_esl_{self._identifier}_alias"
        self._attr_native_max = 32
        self._attr_native_min = 0
        self._attr_mode = "text"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_value = f"{self._identifier}"

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        """Entity always available."""
        return True

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
