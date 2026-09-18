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

from .const import DOMAIN
from .esl_ble.base import DevicePreset

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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


PROTOCOL_LABELS = {
    "wolink": "WOLINK",
    "picksmart": "PickSmart",
    "easytag": "easyTag",
}


def format_model_name(preset: DevicePreset | None) -> str | None:
    """Format model name with resolution."""
    if preset is None:
        return None
    res = f"{preset.width}x{preset.height}"
    if res in preset.display_name:
        return preset.display_name
    return f"{preset.display_name} {res}"


def async_get_device_info(
    hass: HomeAssistant,
    entry_id: str,
    address: str,
) -> DeviceInfo:
    """Get DeviceInfo for a BLE ESL device."""
    identifier = address.replace(":", "")[-8:]
    entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
    backend = entry_data.get("backend")
    preset = entry_data.get("preset")

    protocol_name = None
    if backend:
        protocol_name = PROTOCOL_LABELS.get(
            getattr(backend, "id", ""),
            getattr(backend, "name", str(backend)),
        )

    manufacturer = (
        entry_data.get("manufacturer")
        or protocol_name
        or "BLE ESL"
    )
    model = entry_data.get("model") or format_model_name(preset)

    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, address)},
        name=f"{protocol_name or 'ESL'} {identifier}",
        manufacturer=manufacturer,
        model=model,
        sw_version=entry_data.get("sw_version"),
        hw_version=entry_data.get("hw_version"),
    )
