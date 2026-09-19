"""Shared entity bases for BLE ESL."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from propcache.api import cached_property

from .const import DOMAIN
from .device import async_get_device_info


class BleEslEntity:
    """Mixin binding an entity to one BLE ESL tag.

    Provides the tag-scoped unique id, the shared device info and "always
    available" semantics (the tag is a push target; reachability is reported
    by the connectivity sensor, not by entity availability).

    It has no __init__ on purpose: Home Assistant entity bases do not all
    chain super().__init__(), so concrete classes call _bind_tag() after
    their base initialisers instead. List it *before* the HA base so its
    `available` takes precedence over CoordinatorEntity's.
    """

    _attr_has_entity_name = True

    hass: HomeAssistant
    _entry_id: str
    _address: str
    _identifier: str

    def _bind_tag(self, hass: HomeAssistant, entry: ConfigEntry, key: str) -> None:
        """Bind to the tag of `entry`; `key` is the unique-id suffix."""
        self.hass = hass
        self._entry_id = entry.entry_id
        self._address = hass.data[DOMAIN][entry.entry_id]["address"]
        self._identifier = self._address.replace(":", "")[-8:]
        self._attr_unique_id = f"ble_esl_{self._identifier}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        return async_get_device_info(self.hass, self._entry_id, self._address)

    @cached_property
    def available(self) -> bool:
        return True


class BleEslCoordinatorEntity[T](
    BleEslEntity, CoordinatorEntity[DataUpdateCoordinator[T]]
):
    """Tag-bound entity fed by one of the per-entry DataUpdateCoordinators."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: DataUpdateCoordinator[T],
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._bind_tag(hass, entry, key)

    @property
    def data(self) -> T:
        """Return coordinator data for this entity."""
        return self.coordinator.data
