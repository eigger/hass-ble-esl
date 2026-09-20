"""Entity behaviour through a real Home Assistant: states, categories, session sensors."""

from __future__ import annotations

from unittest.mock import patch

from bt import inject_bluetooth_service_info, service_info
from conftest import IDENT, device_id_of, setup_entry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.ble_esl.const import DOMAIN
from custom_components.ble_esl.esl_ble.base import WriteResult
from custom_components.ble_esl.esl_ble.easytag import EasyTagBleBackend
from custom_components.ble_esl.esl_ble.easytag.const import SERVICE_UUID as EASYTAG_UUID

EASYTAG_ADDRESS = "3D:00:00:E5:7D:76"
EASYTAG_IDENT = "00e57d76"
PAYLOAD = [{"type": "text", "value": "hi", "x": 0, "y": 0}]


def registry_entry(hass: HomeAssistant, entity_id: str) -> er.RegistryEntry:
    entry = er.async_get(hass).async_get(entity_id)
    assert entry is not None, entity_id
    return entry


async def test_entity_categories_and_device_classes(hass: HomeAssistant, wolink_entry) -> None:
    diagnostic = [
        f"sensor.zhsunyco_{IDENT}_write_duration",
        f"sensor.zhsunyco_{IDENT}_failure_count",
        f"sensor.zhsunyco_{IDENT}_last_failure_time",
        f"binary_sensor.zhsunyco_{IDENT}_connectivity",
        f"binary_sensor.zhsunyco_{IDENT}_display_in_sync",
        f"image.zhsunyco_{IDENT}_preview_content",
        f"sensor.zhsunyco_{IDENT}_battery",
        f"sensor.zhsunyco_{IDENT}_voltage",
    ]
    for entity_id in diagnostic:
        assert registry_entry(hass, entity_id).entity_category is EntityCategory.DIAGNOSTIC, (
            entity_id
        )
    for entity_id in (f"switch.zhsunyco_{IDENT}_write_lock", f"text.zhsunyco_{IDENT}_alias"):
        assert registry_entry(hass, entity_id).entity_category is EntityCategory.CONFIG
    assert (
        registry_entry(hass, f"image.zhsunyco_{IDENT}_last_updated_content").entity_category is None
    )

    states = hass.states
    assert (
        states.get(f"sensor.zhsunyco_{IDENT}_write_duration").attributes["device_class"]
        == "duration"
    )
    assert (
        states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").attributes["device_class"]
        == "timestamp"
    )
    assert (
        states.get(f"binary_sensor.zhsunyco_{IDENT}_connectivity").attributes["device_class"]
        == "connectivity"
    )
    assert states.get(f"sensor.zhsunyco_{IDENT}_battery").attributes["device_class"] == "battery"
    assert states.get(f"sensor.zhsunyco_{IDENT}_voltage").attributes["unit_of_measurement"] == "V"
    # RSSI is registered but disabled by default.
    rssi = registry_entry(hass, f"sensor.zhsunyco_{IDENT}_signal_strength")
    assert rssi.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_initial_states(hass: HomeAssistant, wolink_entry) -> None:
    states = hass.states
    assert states.get(f"sensor.zhsunyco_{IDENT}_write_duration").state == "0.0"
    assert states.get(f"sensor.zhsunyco_{IDENT}_failure_count").state == "0"
    assert states.get(f"sensor.zhsunyco_{IDENT}_last_failure_time").state == "unknown"
    assert states.get(f"binary_sensor.zhsunyco_{IDENT}_connectivity").state == "off"
    assert states.get(f"binary_sensor.zhsunyco_{IDENT}_display_in_sync").state == "unknown"
    assert states.get(f"switch.zhsunyco_{IDENT}_write_lock").state == "off"
    assert states.get(f"text.zhsunyco_{IDENT}_alias").state == IDENT


async def test_alias_text_entity(hass: HomeAssistant, wolink_entry) -> None:
    await hass.services.async_call(
        "text",
        "set_value",
        {"entity_id": f"text.zhsunyco_{IDENT}_alias", "value": "Kitchen tag"},
        blocking=True,
    )
    assert hass.states.get(f"text.zhsunyco_{IDENT}_alias").state == "Kitchen tag"


async def test_display_in_sync_tracks_preview_vs_written(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    device_id = device_id_of(hass)
    await hass.services.async_call(
        DOMAIN, "write", {"device_id": device_id, "payload": PAYLOAD}, blocking=True
    )
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_display_in_sync").state == "on"

    # A dry run with a different payload changes the preview only.
    await hass.services.async_call(
        DOMAIN,
        "write",
        {"device_id": device_id, "payload": "something else", "dry_run": True},
        blocking=True,
    )
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_display_in_sync").state == "off"


async def test_easytag_session_battery_and_temperature(
    hass: HomeAssistant, enable_bluetooth
) -> None:
    """Session-polled protocols get battery/temperature entities fed by the write result."""
    inject_bluetooth_service_info(
        hass, service_info(EASYTAG_ADDRESS, name="easyTag", service_uuids=[EASYTAG_UUID])
    )
    await setup_entry(
        hass, address=EASYTAG_ADDRESS, protocol="easytag", model="3D", advertise=False
    )

    ids = {
        "battery": f"sensor.zhsunyco_{EASYTAG_IDENT}_battery",
        "voltage": f"sensor.zhsunyco_{EASYTAG_IDENT}_battery_voltage",
        "temperature": f"sensor.zhsunyco_{EASYTAG_IDENT}_temperature",
        "low": f"binary_sensor.zhsunyco_{EASYTAG_IDENT}_battery",
    }
    for entity_id in ids.values():
        assert hass.states.get(entity_id).state == "unknown", entity_id

    async def fake_write(self, ble_device, preset, prepared, **kwargs):
        await prepared
        return WriteResult(success=True, battery_mv=2600, temperature_c=21)

    with (
        patch.object(EasyTagBleBackend, "write_prepared", fake_write),
        patch.object(EasyTagBleBackend, "prepare_image", staticmethod(lambda p, i, a: i)),
        patch("custom_components.ble_esl.services.render_image") as render,
        patch(
            "custom_components.ble_esl.services.async_ble_device_from_address",
            return_value=object(),
        ),
    ):
        from PIL import Image

        render.return_value = Image.new("RGB", (296, 128), "white")
        await hass.services.async_call(
            DOMAIN,
            "write",
            {"device_id": device_id_of(hass, EASYTAG_ADDRESS), "payload": PAYLOAD},
            blocking=True,
        )

    assert hass.states.get(ids["voltage"]).state == "2.6"
    assert hass.states.get(ids["battery"]).state == "25"  # (2.6-2.5)/(2.9-2.5)
    assert hass.states.get(ids["temperature"]).state == "21"
    assert hass.states.get(ids["low"]).state == "off"
