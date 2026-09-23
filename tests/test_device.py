"""Device-info helpers and preset resolution."""

from __future__ import annotations

from unittest.mock import MagicMock

from bt import service_info
from conftest import ADDRESS, IDENT, device_of, setup_entry
from homeassistant.core import HomeAssistant

from custom_components.ble_esl import device
from custom_components.ble_esl.device import build_device_info
from custom_components.ble_esl.esl_ble.picksmart import PickSmartBleBackend
from custom_components.ble_esl.esl_ble.picksmart.const import MANUFACTURER_ID as PS_ID


async def test_build_device_info_matches_registry(hass: HomeAssistant, enable_bluetooth) -> None:
    entry = await setup_entry(hass)
    info = build_device_info(entry.runtime_data)
    registered = device_of(hass)
    assert info["name"] == f"Zhsunyco {IDENT}" == registered.name
    assert info["manufacturer"] == "Zhsunyco" == registered.manufacturer
    assert info["model"] == '2.9" BWRY 296x128' == registered.model
    assert info["model_id"] == "WOLINK" == registered.model_id
    assert info["sw_version"] == "513" and info["hw_version"] == "1027"
    assert ("bluetooth", ADDRESS) in info["connections"]


def test_resolve_preset_refines_from_last_advertisement(monkeypatch) -> None:
    """Configured model -> preset, then the advertisement's model (PickSmart) wins."""
    backend = PickSmartBleBackend()
    info = service_info(
        "AA:BB:CC:DD:EE:FF",
        manufacturer_data={PS_ID: bytes([0x33, 0x1A, 0x81, 0x01, 0x40])},  # device 0x0033
    )
    monkeypatch.setattr(device, "async_last_service_info", lambda *a, **k: info)

    resolved = device.resolve_preset(MagicMock(), backend, info.address, "0x0028")
    assert resolved.preset.key == "0x0033"  # advertisement is authoritative
    assert resolved.service_info is info
    assert resolved.advertisement.raw["device_id"] == 0x33

    monkeypatch.setattr(device, "async_last_service_info", lambda *a, **k: None)
    resolved = device.resolve_preset(MagicMock(), backend, info.address, "bogus")
    assert resolved.preset is next(iter(backend.presets().values()))
    assert resolved.service_info is None and resolved.advertisement is None
