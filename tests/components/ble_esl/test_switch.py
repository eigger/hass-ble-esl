"""Write lock switch controls physical writes."""

from homeassistant.core import HomeAssistant

from tests.components.ble_esl.conftest import IDENT, device_id_of
from tests.components.ble_esl.test_services import call


async def test_write_lock_skips_physical_write(
    hass: HomeAssistant, wolink_entry, tag_writer
) -> None:
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": f"switch.zhsunyco_{IDENT}_write_lock"}, blocking=True
    )
    assert wolink_entry.data["write_lock"] is True  # persisted
    await call(hass, "write", device_id_of(hass))
    await call(hass, "write_guarded", device_id_of(hass))
    assert tag_writer.write_prepared.await_count == 0
    assert hass.states.get(f"image.zhsunyco_{IDENT}_preview_content").state != "unknown"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": f"switch.zhsunyco_{IDENT}_write_lock"}, blocking=True
    )
    await call(hass, "write", device_id_of(hass))
    assert tag_writer.write_prepared.await_count == 1
