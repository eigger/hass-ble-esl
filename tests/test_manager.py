"""Dashboard resolves registered entities rather than guessed HA entity IDs."""

from homeassistant.helpers import entity_registry as er

from custom_components.ble_esl.designer.manager import tag_metadata


async def test_registry_metadata_renamed_entities(hass, wolink_entry):
    registry = er.async_get(hass)
    metadata = tag_metadata(hass, wolink_entry)
    assert metadata["device_id"]
    for key in (
        "alias",
        "last_updated_content",
        "display_in_sync",
        "write_duration",
        "last_failure_time",
        "failure_count",
        "battery",
    ):
        assert metadata["entities"][key]
    alias = metadata["entities"]["alias"]
    registry.async_update_entity(alias, new_entity_id="text.custom_alias")
    assert tag_metadata(hass, wolink_entry)["entities"]["alias"] == "text.custom_alias"
    # Disabled registry entries remain discoverable; UI handles missing states.
    registry.async_update_entity(
        metadata["entities"]["battery"], disabled_by=er.RegistryEntryDisabler.USER
    )
    assert (
        tag_metadata(hass, wolink_entry)["entities"]["battery"] == metadata["entities"]["battery"]
    )
