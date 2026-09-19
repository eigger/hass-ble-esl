"""Config-entry diagnostics through the diagnostics HTTP endpoint."""

from __future__ import annotations

from unittest.mock import patch

from bluetooth import inject_bluetooth_service_info, service_info
from conftest import ADDRESS, IDENT, device_id_of, setup_entry
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.ble_esl.const import CONF_RETRY_COUNT, DOMAIN
from custom_components.ble_esl.esl_ble.wolink.const import MANUFACTURER_ID


async def test_diagnostics_content_and_redaction(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, enable_bluetooth, tag_writer
) -> None:
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await setup_entry(hass, options={CONF_RETRY_COUNT: 2})
    await hass.services.async_call(
        DOMAIN, "write", {"device_id": device_id_of(hass), "payload": "p"}, blocking=True
    )

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    dump = str(result)
    assert ADDRESS not in dump and ADDRESS.replace(":", "") not in dump.replace(IDENT, "")
    assert result["entry"]["unique_id"] == "**REDACTED**"
    assert result["device"]["address"] == "**REDACTED**"
    assert result["device"]["identifier"] == IDENT
    assert result["entry"]["effective_options"]["retry_count"] == 2
    assert result["entry"]["effective_options"]["debounce_ms"] == 0

    assert result["backend"]["id"] == "wolink"
    assert result["backend"]["capabilities"]["passive_battery"] is True
    assert result["preset"]["key"] == "290"
    assert result["preset"]["extra"]["mirror"] is True

    adv = result["advertisement"]
    assert adv["manufacturer_data"] == {f"0x{MANUFACTURER_ID:04X}": "12340201040306050bb8"}
    assert adv["parsed"]["battery_mv"] == 3000
    assert adv["parsed"]["sw_version"] == "258"

    assert result["write_state"]["write_lock"] is False
    assert result["write_state"]["in_progress"] is False
    assert result["write_state"]["last_image_png_bytes"] > 0
    assert result["sensors"]["failure_count"] == 0
    assert result["sensors"]["connectivity"] is False


async def test_diagnostics_masks_mac_in_name_and_survives_parse_errors(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, enable_bluetooth
) -> None:
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await setup_entry(hass, advertise=False)
    # A tag that advertises its MAC as the name.
    inject_bluetooth_service_info(
        hass,
        service_info(
            ADDRESS,
            name=ADDRESS.replace(":", ""),
            manufacturer_data={MANUFACTURER_ID: bytes(10)},
        ),
    )
    await hass.async_block_till_done()

    with patch.object(
        entry.runtime_data.backend, "parse_advertisement", side_effect=ValueError("bad")
    ):
        result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["advertisement"]["name"] == "**REDACTED**"
    assert result["advertisement"]["parsed"] == {"error": "ValueError: bad"}
    assert result["advertisement"]["rssi"] == -60  # the rest of the download is intact
