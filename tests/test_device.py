"""Tests for BLE ESL device info helper and device registry updates."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.ble_esl import process_service_info
from custom_components.ble_esl.const import DOMAIN
from custom_components.ble_esl.device import async_get_device_info
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.esl_ble.wolink import WolinkProtocol
from custom_components.ble_esl.esl_ble.wolink.const import MANUFACTURER_ID


def test_async_get_device_info():
    """Verify async_get_device_info retrieves model, sw_version, and hw_version."""
    hass = MagicMock()
    entry_id = "test_entry"
    address = "66:66:54:20:00:55"

    preset = DevicePreset(
        key="290",
        display_name="2.9\" BWRY",
        width=296,
        height=128,
        colors="BWRY",
    )

    backend = WolinkProtocol()
    hass.data = {
        DOMAIN: {
            entry_id: {
                "backend": backend,
                "preset": preset,
                "sw_version": "258",
                "hw_version": "772",
            }
        }
    }

    dev_info = async_get_device_info(hass, entry_id, address)
    assert dev_info["name"] == "WOLINK 54200055"
    assert dev_info["manufacturer"] == "WOLINK"
    assert dev_info["model"] == "2.9\" BWRY 296x128"
    assert dev_info["sw_version"] == "258"
    assert dev_info["hw_version"] == "772"
    assert ("bluetooth", address) in dev_info["connections"]


def test_process_service_info_updates_device_registry():
    """Verify process_service_info updates device registry with sw/hw/model."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"

    backend = WolinkProtocol()
    preset = backend.presets()["290"]
    parser = backend.create_parser(preset=preset)

    coordinator = MagicMock()
    coordinator.device_data = parser
    entry.runtime_data = coordinator

    device_registry = MagicMock()

    hass.data = {
        DOMAIN: {
            "test_entry": {
                "backend": backend,
                "preset": preset,
                "device_id": "mock_device_id_123",
                "sw_version": None,
                "hw_version": None,
                "model": None,
                "manufacturer": None,
            }
        }
    }

    service_info = MagicMock()
    service_info.address = "66:66:54:20:00:55"
    service_info.service_uuids = []
    # PID=0x1234, AppVer=0x0102(258), HwVer=0x0304(772), DispVer=0x0506, Bat=3000mV (0x0BB8)
    service_info.manufacturer_data = {
        MANUFACTURER_ID: bytes([0x12, 0x34, 0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x0B, 0xB8])
    }

    update = process_service_info(hass, entry, device_registry, service_info)
    assert update is not None

    entry_data = hass.data[DOMAIN]["test_entry"]
    assert entry_data["sw_version"] == "258"
    assert entry_data["hw_version"] == "772"
    assert entry_data["model"] == "2.9\" BWRY 296x128"
    assert entry_data["manufacturer"] == "WOLINK"

    device_registry.async_update_device.assert_called_once_with(
        "mock_device_id_123",
        sw_version="258",
        hw_version="772",
        model="2.9\" BWRY 296x128",
        manufacturer="WOLINK",
    )
