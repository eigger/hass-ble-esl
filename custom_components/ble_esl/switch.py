"""Support for BLE ESL write lock switch."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, WRITE_LOCK
from .entity import BleEslEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BLE ESL write lock switch."""
    async_add_entities([BleEslWriteLockSwitch(hass, entry)])


class BleEslWriteLockSwitch(BleEslEntity, RestoreEntity, SwitchEntity):
    """Switch that locks physical writes (virtual updates still apply)."""

    _key = "write_lock"
    _attr_translation_key = "write_lock"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:lock"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._bind_tag(hass, entry)
        self._is_on = False

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the write lock."""
        self._is_on = True
        self.hass.data[DOMAIN][self._entry_id][WRITE_LOCK] = True

        # Save to config entry data for persistence
        config_entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if config_entry:
            data = {**config_entry.data, WRITE_LOCK: True}
            self.hass.config_entries.async_update_entry(config_entry, data=data)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the write lock."""
        self._is_on = False
        self.hass.data[DOMAIN][self._entry_id][WRITE_LOCK] = False

        # Save to config entry data for persistence
        config_entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if config_entry:
            data = {**config_entry.data, WRITE_LOCK: False}
            self.hass.config_entries.async_update_entry(config_entry, data=data)

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state when added to hass."""
        await super().async_added_to_hass()

        # Restore from config entry data (most reliable for config entities)
        config_entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if config_entry and WRITE_LOCK in config_entry.data:
            self._is_on = config_entry.data[WRITE_LOCK]
        else:
            # Fallback to RestoreEntity if not in config entry
            last_state = await self.async_get_last_state()
            if last_state is not None:
                self._is_on = last_state.state == "on"
            else:
                self._is_on = False

        # Update hass.data with restored state
        self.hass.data[DOMAIN][self._entry_id][WRITE_LOCK] = self._is_on
