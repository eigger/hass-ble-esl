"""Support for BLE ESL write lock switch."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import WRITE_LOCK
from .entity import BleEslEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BLE ESL write lock switch."""
    async_add_entities([BleEslWriteLockSwitch(hass, entry)])


class BleEslWriteLockSwitch(BleEslEntity, SwitchEntity):
    """Switch that locks physical writes (virtual updates still apply).

    The state is persisted in the config entry data, which async_setup_entry
    seeds into runtime_data.write_lock, so the lock is in force before this
    entity is even added.
    """

    _key = "write_lock"
    _attr_translation_key = "write_lock"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:lock"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._bind_tag(hass, entry)

    @property
    def is_on(self) -> bool:
        return self._data.write_lock

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the write lock."""
        self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the write lock."""
        self._async_set(False)

    @callback
    def _async_set(self, value: bool) -> None:
        self._data.write_lock = value
        if config_entry := self.hass.config_entries.async_get_entry(self._entry_id):
            self.hass.config_entries.async_update_entry(
                config_entry, data={**config_entry.data, WRITE_LOCK: value}
            )
        self.async_write_ha_state()
