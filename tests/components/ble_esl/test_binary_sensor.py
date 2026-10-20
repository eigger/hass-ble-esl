"""Binary sensor changes through actual writes and previews."""

from homeassistant.core import HomeAssistant

from custom_components.ble_esl.const import DOMAIN
from tests.components.ble_esl.conftest import IDENT, device_id_of

PAYLOAD = [{"type": "text", "value": "hi", "x": 0, "y": 0}]


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
        {
            "device_id": device_id,
            "payload": [{"type": "text", "value": "something else"}],
            "dry_run": True,
        },
        blocking=True,
    )
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_display_in_sync").state == "off"
