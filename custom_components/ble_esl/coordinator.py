"""The BLE ESL integration coordinator."""

from __future__ import annotations

from collections.abc import Callable
from logging import Logger
from typing import TYPE_CHECKING, TypeVar

from bluetooth_sensor_state_data import BluetoothData
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.core import HomeAssistant
from sensor_state_data import SensorUpdate

if TYPE_CHECKING:
    from .types import BleEslConfigEntry

_T = TypeVar("_T")


class BleEslPassiveBluetoothProcessorCoordinator(
    PassiveBluetoothProcessorCoordinator[SensorUpdate]
):
    """Define a BLE ESL Passive Update Processor Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        address: str,
        mode: BluetoothScanningMode,
        update_method: Callable[[BluetoothServiceInfoBleak], SensorUpdate],
        device_data: BluetoothData,
        entry: BleEslConfigEntry,
        connectable: bool = False,
    ) -> None:
        """Initialize the BLE ESL Passive Update Processor Coordinator."""
        super().__init__(
            hass, logger, address, mode, update_method, connectable
        )
        self.device_data = device_data
        self.entry = entry


class BleEslPassiveBluetoothDataProcessor(
    PassiveBluetoothDataProcessor[_T, SensorUpdate]
):
    """Define a BLE ESL Passive Update Data Processor."""

    coordinator: BleEslPassiveBluetoothProcessorCoordinator
