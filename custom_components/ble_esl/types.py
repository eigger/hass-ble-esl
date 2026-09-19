"""Type aliases for the BLE ESL integration."""

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .data import BleEslRuntimeData

type BleEslConfigEntry = ConfigEntry[BleEslRuntimeData]
