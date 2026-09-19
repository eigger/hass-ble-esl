"""Support for BLE ESL devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothEntityKey,
)
from homeassistant.const import ATTR_HW_VERSION, ATTR_SW_VERSION
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.sensor import sensor_device_info_to_hass_device_info
from sensor_state_data import DeviceKey

from .esl_ble.base import AdvertisementInfo, BleBackend, DevicePreset

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
    from homeassistant.core import HomeAssistant

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


class PresetResolution(NamedTuple):
    """A preset resolved from configuration and the tag's last advertisement."""

    preset: DevicePreset
    service_info: BluetoothServiceInfoBleak | None
    advertisement: AdvertisementInfo | None


def resolve_preset(
    hass: HomeAssistant, backend: BleBackend, address: str, model_key: str | None
) -> PresetResolution:
    """Configured model -> preset, refined by what the tag last advertised.

    Used at setup and before every write, where the tag's *last seen*
    advertisement is looked up. process_service_info() is a different path
    on purpose: it receives each live advertisement and refines from that
    directly, so it must not be routed through here (that would re-read the
    last advertisement a second time).
    """
    preset = backend.preset_for(model_key)
    service_info = async_last_service_info(hass, address, connectable=True)
    advertisement = backend.parse_advertisement(service_info) if service_info else None
    if advertisement is not None:
        preset = backend.refine_preset(preset, advertisement)
    return PresetResolution(preset, service_info, advertisement)


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
        model_id=data.backend.label,
        sw_version=data.sw_version,
        hw_version=data.hw_version,
    )
