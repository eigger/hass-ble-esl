"""Preview and written image entities through the real write action."""

from homeassistant.core import HomeAssistant

from tests.components.ble_esl.conftest import IDENT, device_id_of
from tests.components.ble_esl.test_services import call


async def test_dry_run_only_updates_preview(hass: HomeAssistant, wolink_entry, tag_writer) -> None:
    await call(hass, "write", device_id_of(hass), dry_run=True)
    assert tag_writer.write_prepared.await_count == 0
    assert hass.states.get(f"image.zhsunyco_{IDENT}_preview_content").state != "unknown"
    assert hass.states.get(f"image.zhsunyco_{IDENT}_last_updated_content").state == "unknown"
    assert wolink_entry.runtime_data.last_image_data is None  # not counted as sent
