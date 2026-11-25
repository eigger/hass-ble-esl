"""Device-info helpers and preset resolution."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from custom_components.ble_esl import device
from custom_components.ble_esl.device import _device_info, build_device_info
from custom_components.ble_esl.esl_ble.picksmart import PickSmartProtocol
from custom_components.ble_esl.esl_ble.picksmart.const import MANUFACTURER_ID as PS_ID
from tests.components.ble_esl.bt import service_info
from tests.components.ble_esl.conftest import ADDRESS, IDENT, device_of, setup_entry


async def test_build_device_info_matches_registry(hass: HomeAssistant, enable_bluetooth) -> None:
    entry = await setup_entry(hass)
    info = build_device_info(entry.runtime_data)
    registered = device_of(hass)
    assert info == DeviceInfo(
        connections={(CONNECTION_BLUETOOTH, ADDRESS)},
        name=f"Zhsunyco {IDENT}",
        manufacturer="Zhsunyco",
        model='2.9" BWRY 296x128',
        model_id="WOLINK",
        sw_version="513",
        hw_version="1027",
    )
    assert registered.name == f"Zhsunyco {IDENT}"
    assert registered.manufacturer == "Zhsunyco"
    assert registered.model == '2.9" BWRY 296x128'
    assert registered.model_id == "WOLINK"
    assert registered.sw_version == "513" and registered.hw_version == "1027"


def test_device_info_from_sensor_values_omits_unset_fields() -> None:
    """Unset values are left out (never None), on TypedDict and dataclass alike."""
    assert _device_info("Tag", "Acme", "M1", "1.0", "2.0") == DeviceInfo(
        name="Tag", manufacturer="Acme", model="M1", sw_version="1.0", hw_version="2.0"
    )
    assert _device_info("Tag", None, None, None, None) == DeviceInfo(name="Tag")
    assert _device_info(None, "Acme", None, "1.0", None) == DeviceInfo(
        manufacturer="Acme", sw_version="1.0"
    )
    assert _device_info(None, None, None, None, None) == DeviceInfo()
    assert _device_info("Tag", "Acme", None, None, None) is _device_info(
        "Tag", "Acme", None, None, None
    )


def test_resolve_preset_refines_from_last_advertisement(monkeypatch) -> None:
    """Configured model -> preset, then the advertisement's model (PickSmart) wins."""
    protocol = PickSmartProtocol()
    info = service_info(
        "AA:BB:CC:DD:EE:FF",
        manufacturer_data={PS_ID: bytes([0x33, 0x1A, 0x81, 0x01, 0x40])},  # device 0x0033
    )
    monkeypatch.setattr(device, "async_last_service_info", lambda *a, **k: info)

    resolved = device.resolve_preset(MagicMock(), protocol, info.address, "0x0028")
    assert resolved.preset.key == "0x0033"  # advertisement is authoritative
    assert resolved.service_info is info
    assert resolved.advertisement.raw["device_id"] == 0x33

    monkeypatch.setattr(device, "async_last_service_info", lambda *a, **k: None)
    resolved = device.resolve_preset(MagicMock(), protocol, info.address, "bogus")
    assert resolved.preset is next(iter(protocol.presets().values()))
    assert resolved.service_info is None and resolved.advertisement is None
