"""Support for BLE ESL devices."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothEntityKey,
)
from homeassistant.const import (
    ATTR_HW_VERSION,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SW_VERSION,
)
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from sensor_state_data import DeviceKey, SensorDeviceInfo

from .esl_ble.base import AdvertisementInfo, DevicePreset, EslProtocol

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
    from homeassistant.core import HomeAssistant

    from .data import BleEslRuntimeData


def device_key_to_bluetooth_entity_key(
    device_key: DeviceKey,
) -> PassiveBluetoothEntityKey:
    """Convert a device key to an entity key."""
    return PassiveBluetoothEntityKey(device_key.key, device_key.device_id)


def hass_device_info(sensor_device_info: SensorDeviceInfo) -> DeviceInfo:
    """Convert sensor device info to HA device info, keeping sw/hw versions."""
    return _device_info(
        sensor_device_info.name,
        sensor_device_info.manufacturer,
        sensor_device_info.model,
        sensor_device_info.sw_version,
        sensor_device_info.hw_version,
    )


@lru_cache(maxsize=64)
def _device_info(
    name: str | None,
    manufacturer: str | None,
    model: str | None,
    sw_version: str | None,
    hw_version: str | None,
) -> DeviceInfo:
    """Return cached device info for these values, leaving None values unset."""
    device_info = DeviceInfo()
    for key, value in (
        (ATTR_NAME, name),
        (ATTR_MANUFACTURER, manufacturer),
        (ATTR_MODEL, model),
        (ATTR_SW_VERSION, sw_version),
        (ATTR_HW_VERSION, hw_version),
    ):
        if value is not None:
            device_info[key] = value
    return device_info


class PresetResolution(NamedTuple):
    """A preset resolved from configuration and the tag's last advertisement."""

    preset: DevicePreset
    service_info: BluetoothServiceInfoBleak | None
    advertisement: AdvertisementInfo | None


def resolve_preset(
    hass: HomeAssistant, protocol: EslProtocol, address: str, model_key: str | None
) -> PresetResolution:
    """Configured model -> preset, refined by what the tag last advertised.

    Used at setup and before every write, where the tag's *last seen*
    advertisement is looked up. process_service_info() is a different path
    on purpose: it receives each live advertisement and refines from that
    directly, so it must not be routed through here (that would re-read the
    last advertisement a second time).
    """
    preset = protocol.preset_for(model_key)
    service_info = async_last_service_info(hass, address, connectable=True)
    advertisement = protocol.parse_advertisement(service_info) if service_info else None
    if advertisement is not None:
        preset = protocol.refine_preset(preset, advertisement)
    return PresetResolution(preset, service_info, advertisement)


def format_model_name(preset: DevicePreset | None) -> str | None:
    """Model name shown in HA (None when no preset is known)."""
    return None if preset is None else preset.model_name


def build_device_info(data: BleEslRuntimeData) -> DeviceInfo:
    """DeviceInfo shared by every entity of a tag."""
    return DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, data.address)},
        name=f"{data.manufacturer} {data.label}",
        manufacturer=data.manufacturer,
        model=data.model,
        model_id=data.protocol.label,
        sw_version=data.sw_version,
        hw_version=data.hw_version,
    )
