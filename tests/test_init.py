"""Setup, device registry and unload against a real Home Assistant."""

from __future__ import annotations

from bt import inject_bluetooth_service_info
from conftest import ADDRESS, IDENT, WOLINK_MFR_BYTES, device_of, setup_entry, wolink_service_info
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ble_esl.const import CONF_MODEL, CONF_PROTOCOL, DOMAIN, WRITE_LOCK


async def test_setup_creates_device_and_entities(hass: HomeAssistant, wolink_entry) -> None:
    assert wolink_entry.state is ConfigEntryState.LOADED
    data = wolink_entry.runtime_data
    assert data.address == ADDRESS
    assert data.backend.id == "wolink"
    assert data.preset.key == "290"

    device = device_of(hass)
    assert device.manufacturer == "Zhsunyco"
    assert device.model == '2.9" BWRY 296x128'
    assert device.model_id == "WOLINK"
    assert device.sw_version == "258" and device.hw_version == "772"
    assert device.name == f"Zhsunyco {IDENT}"

    registry = er.async_get(hass)
    unique_ids = {
        e.unique_id for e in er.async_entries_for_config_entry(registry, wolink_entry.entry_id)
    }
    # Coordinator-backed entities (no session battery/temperature for WOLINK)...
    for suffix in (
        "write_duration",
        "failure_count",
        "last_failure_time",
        "connectivity",
        "display_in_sync",
        "last_updated_content",
        "preview_content_image",
        "write_lock",
        "alias",
    ):
        assert f"ble_esl_{IDENT}_{suffix}" in unique_ids, suffix
    assert not any(
        uid.endswith(("_battery", "_battery_voltage", "_temperature")) for uid in unique_ids
    )
    # ...plus the passive ones fed by the advertisement.
    assert hass.states.get(f"sensor.zhsunyco_{IDENT}_battery").state == "100"
    assert hass.states.get(f"sensor.zhsunyco_{IDENT}_voltage").state == "3.0"
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_battery").state == "off"


async def test_advertisement_updates_device_versions(hass: HomeAssistant, wolink_entry) -> None:
    """process_service_info mirrors new firmware/hardware versions onto the device."""
    newer = bytes([0x12, 0x34, 0x03, 0x01, 0x05, 0x03]) + WOLINK_MFR_BYTES[6:]  # app 259, hw 773
    inject_bluetooth_service_info(hass, wolink_service_info(mfr_bytes=newer))
    await hass.async_block_till_done()

    device = device_of(hass)
    assert device.sw_version == "259" and device.hw_version == "773"
    assert wolink_entry.runtime_data.sw_version == "259"


async def test_low_battery_advertisement(hass: HomeAssistant, wolink_entry) -> None:
    low = WOLINK_MFR_BYTES[:8] + bytes([0x08, 0x98])  # 2200 mV
    inject_bluetooth_service_info(hass, wolink_service_info(mfr_bytes=low))
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.zhsunyco_{IDENT}_battery").state == "0"
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_battery").state == "on"


async def test_setup_without_prior_advertisement(hass: HomeAssistant, enable_bluetooth) -> None:
    """A tag that has not advertised yet still sets up (versions unknown)."""
    entry = await setup_entry(hass, advertise=False)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.sw_version is None
    assert hass.states.get(f"sensor.zhsunyco_{IDENT}_battery") is None


async def test_write_lock_seeded_from_entry_data(hass: HomeAssistant, enable_bluetooth) -> None:
    entry = await setup_entry(hass, data={WRITE_LOCK: True})
    assert entry.runtime_data.write_lock is True
    assert hass.states.get(f"switch.zhsunyco_{IDENT}_write_lock").state == "on"


async def test_services_registered_once_and_survive_unload(
    hass: HomeAssistant, enable_bluetooth
) -> None:
    first = await setup_entry(hass, address="66:66:54:20:00:01")
    assert hass.services.has_service(DOMAIN, "write")
    assert hass.services.has_service(DOMAIN, "write_guarded")
    second = await setup_entry(hass, address="66:66:54:20:00:02")

    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()
    assert first.state is ConfigEntryState.NOT_LOADED
    assert second.state is ConfigEntryState.LOADED
    assert hass.services.has_service(DOMAIN, "write")

    assert await hass.config_entries.async_unload(second.entry_id)
    assert hass.services.has_service(DOMAIN, "write")  # domain-level, stays registered


async def test_unload_makes_entities_unavailable(hass: HomeAssistant, wolink_entry) -> None:
    assert hass.states.get(f"switch.zhsunyco_{IDENT}_write_lock").state == "off"
    assert await hass.config_entries.async_unload(wolink_entry.entry_id)
    await hass.async_block_till_done()
    assert wolink_entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(f"switch.zhsunyco_{IDENT}_write_lock").state == "unavailable"


async def test_unknown_backend_id_fails_setup_clearly(
    hass: HomeAssistant, enable_bluetooth
) -> None:
    """Backend ids are not migrated: an entry with a stale id asks to be re-added."""
    address = "AA:BB:CC:DD:EE:42"
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=address,
        title="Poshiji DDEEEE42",
        data={CONF_PROTOCOL: "poshiji", CONF_MODEL: "psj-420"},
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert entry.error_reason_translation_key == "unknown_backend"
    assert entry.error_reason_translation_placeholders == {"protocol": "poshiji"}
