"""Alias text entity through Home Assistant actions."""

from homeassistant.core import HomeAssistant

from tests.components.ble_esl.conftest import IDENT


async def test_alias_text_entity(hass: HomeAssistant, wolink_entry) -> None:
    """The entity pushes its own state: nothing polls it after the call."""
    for entity_id in (f"switch.zhsunyco_{IDENT}_write_lock", f"text.zhsunyco_{IDENT}_alias"):
        entity = hass.data["entity_components"][entity_id.split(".")[0]].get_entity(entity_id)
        assert entity is not None and entity.should_poll is False
    await hass.services.async_call(
        "text",
        "set_value",
        {"entity_id": f"text.zhsunyco_{IDENT}_alias", "value": "Kitchen tag"},
        blocking=True,
    )
    assert hass.states.get(f"text.zhsunyco_{IDENT}_alias").state == "Kitchen tag"
