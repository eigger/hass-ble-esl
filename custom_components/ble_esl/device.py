"""Support for BLE ESL devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothEntityKey,
)
from homeassistant.const import ATTR_HW_VERSION, ATTR_SW_VERSION
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.sensor import sensor_device_info_to_hass_device_info
from sensor_state_data import DeviceKey

from .esl_ble.base import DevicePreset

if TYPE_CHECKING:
    from .data import BleEslRuntimeData


def device_key_to_bluetooth_entity_key(
    device_key: DeviceKey,
) -> PassiveBluetoothEntityKey:
    """Convert a device key to an entity key."""
    return PassiveBluetoothEntityKey(device_key.key, device_key.device_id)


def hass_device_info(sensor_device_info):
    """Convert sensor device info to HA device info, keeping sw/hw versions."""
    device_info = sensor_device_info_to_hass_device_info(sensor_device_info)
    if sensor_device_info.sw_version is not None:
        device_info[ATTR_SW_VERSION] = sensor_device_info.sw_version
    if sensor_device_info.hw_version is not None:
        device_info[ATTR_HW_VERSION] = sensor_device_info.hw_version
    return device_info


def protocol_label(backend) -> str:
    """Short protocol name for a backend (shown as HA model_id)."""
    return backend.label


def backend_brand(backend) -> str:
    """Brand the tags are sold under (shown as HA manufacturer)."""
    return backend.brand


def format_model_name(preset: DevicePreset | None) -> str | None:
    """Model name shown in HA (None when no preset is known)."""
    return None if preset is None else preset.model_name


def build_device_info(data: BleEslRuntimeData) -> DeviceInfo:
    """DeviceInfo shared by every entity of a tag."""
    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, data.address)},
        name=f"{data.manufacturer} {data.identifier}",
        manufacturer=data.manufacturer,
        model=data.model,
        model_id=protocol_label(data.backend),
        sw_version=data.sw_version,
        hw_version=data.hw_version,
    )
