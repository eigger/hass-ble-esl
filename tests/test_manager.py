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


async def test_registry_metadata_includes_renamed_low_battery_sensor(hass, wolink_entry):
    registry = er.async_get(hass)
    identifier = wolink_entry.runtime_data.identifier
    sensor = registry.async_get_or_create(
        "binary_sensor",
        "ble_esl",
        f"ble_esl_{identifier}_battery_low",
        config_entry=wolink_entry,
    )
    registry.async_update_entity(sensor.entity_id, new_entity_id="binary_sensor.custom_battery_low")
    assert (
        tag_metadata(hass, wolink_entry)["entities"]["battery_low"]
        == "binary_sensor.custom_battery_low"
    )


async def test_registry_metadata_resolves_passive_low_battery_warning(hass, wolink_entry):
    registry = er.async_get(hass)
    entity_id = tag_metadata(hass, wolink_entry)["entities"]["battery_low"]
    assert entity_id
    registered = registry.async_get(entity_id)
    assert registered.unique_id.startswith(f"{wolink_entry.runtime_data.address}-battery")
    assert hass.states.get(entity_id).attributes["device_class"] == "battery"
    registry.async_update_entity(entity_id, new_entity_id="binary_sensor.renamed_passive_low")
    assert (
        tag_metadata(hass, wolink_entry)["entities"]["battery_low"]
        == "binary_sensor.renamed_passive_low"
    )


async def test_automation_associations_persist_without_changing_configs(hass, wolink_entry):
    from types import SimpleNamespace

    from custom_components.ble_esl.designer.manager import AutomationLinks

    metadata = tag_metadata(hass, wolink_entry)
    config = {"actions": [{"target": {"device_id": metadata["device_id"]}}]}
    hass.states.async_set("automation.detected", "off", {"id": "123", "friendly_name": "Detected"})
    hass.states.async_set("automation.manual", "on", {"id": "456", "friendly_name": "Manual"})
    hass.data["automation"] = SimpleNamespace(
        get_entity=lambda entity_id: SimpleNamespace(
            raw_config=config if entity_id == "automation.detected" else {}
        )
    )
    links = AutomationLinks(hass)
    result = await links.update(wolink_entry, "automation.manual")
    assert [(item["entity_id"], item["source"]) for item in result["linked"]] == [
        ("automation.detected", "detected"),
        ("automation.manual", "manual"),
    ]
    assert result["linked"][0]["state"] == "off"
    assert config == {"actions": [{"target": {"device_id": metadata["device_id"]}}]}
    restored = AutomationLinks(hass)
    await restored.load()
    assert restored.links == links.links
    er.async_get(hass).async_get_or_create(
        "automation", "automation", "456", suggested_object_id="manual"
    )
    hass.states.async_remove("automation.manual")
    missing = next(
        item
        for item in restored.describe(wolink_entry)["linked"]
        if item["entity_id"] == "automation.manual"
    )
    assert missing["missing"] and missing["state"] == "unavailable"
    result = await restored.update(wolink_entry, "automation.manual", remove=True)
    assert len(result["linked"]) == 1
    result = await restored.update(wolink_entry, "automation.detected")
    assert result["linked"][0]["source"] == "manual+detected"
    result = await restored.update(wolink_entry, "automation.detected", remove=True)
    assert result["linked"][0]["source"] == "detected"


async def test_automation_entity_targets_and_templates(hass, wolink_entry):
    from custom_components.ble_esl.designer.manager import references_tag

    alias = tag_metadata(hass, wolink_entry)["entities"]["alias"]
    targets = {alias}
    assert references_tag(
        {"actions": [{"choose": [{"sequence": [{"target": {"entity_id": [alias]}}]}]}]},
        set(),
        targets,
    )
    assert not references_tag({"description": alias}, set(), targets)
    assert not references_tag({"target": {"entity_id": "{{ '" + alias + "' }}"}}, set(), targets)


async def test_automation_link_rejects_invalid_entities(hass, wolink_entry):
    from homeassistant.exceptions import HomeAssistantError
    import pytest

    from custom_components.ble_esl.designer.manager import AutomationLinks

    links = AutomationLinks(hass)
    with pytest.raises(HomeAssistantError):
        await links.update(wolink_entry, "sensor.invalid")
    with pytest.raises(HomeAssistantError):
        await links.update(wolink_entry, "automation.missing")


async def test_automation_edit_source_returns_registered_targets(hass, wolink_entry):
    from types import SimpleNamespace

    from custom_components.ble_esl.const import DOMAIN
    from custom_components.ble_esl.designer.manager import AutomationLinks

    registry = er.async_get(hass)
    write_lock = registry.async_get_or_create(
        "switch",
        DOMAIN,
        "ble_esl_write_lock_extra",
        config_entry=wolink_entry,
    )
    hass.states.async_set("automation.edit_me", "off", {"id": "stored-id"})
    hass.data["automation"] = SimpleNamespace(
        get_entity=lambda entity_id: SimpleNamespace(raw_config={"actions": []})
    )
    source = AutomationLinks(hass).edit_source(wolink_entry, "automation.edit_me")
    metadata = tag_metadata(hass, wolink_entry)
    registered_ids = sorted(
        entity.entity_id
        for entity in er.async_entries_for_config_entry(registry, wolink_entry.entry_id)
    )
    assert source == {
        "entity_id": "automation.edit_me",
        "config_id": "stored-id",
        "device_id": metadata["device_id"],
        "entity_ids": registered_ids,
    }
    assert write_lock.entity_id in source["entity_ids"]


async def test_detection_with_real_ha_automation(hass, wolink_entry):
    from homeassistant.setup import async_setup_component

    from custom_components.ble_esl.designer.manager import AutomationLinks

    entity_id = tag_metadata(hass, wolink_entry)["entities"]["alias"]
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "id": "esl_test",
                    "alias": "ESL schedule",
                    "initial_state": False,
                    "triggers": [{"trigger": "event", "event_type": "esl_test_event"}],
                    "actions": [
                        {
                            "action": "text.set_value",
                            "target": {"entity_id": entity_id},
                            "data": {"value": "Scheduled"},
                        }
                    ],
                }
            ]
        },
    )
    await hass.async_block_till_done()
    result = AutomationLinks(hass).describe(wolink_entry)
    assert result["linked"] == [
        {
            "entity_id": "automation.esl_schedule",
            "name": "ESL schedule",
            "state": "off",
            "id": "esl_test",
            "source": "detected",
            "missing": False,
            "link_id": None,
        }
    ]


async def test_automation_websocket_routes(hass, wolink_entry, hass_ws_client):
    client = await hass_ws_client(hass)
    hass.states.async_set("automation.manual", "on", {"id": "abc"})
    for number, action in enumerate(("automations", "link_automation", "unlink_automation"), 1):
        await client.send_json(
            {
                "id": number,
                "type": "ble_esl/designer",
                "action": action,
                "entry_id": wolink_entry.entry_id,
                "entity_id": "automation.manual",
            }
        )
        response = await client.receive_json()
        assert response["success"]
        assert len(response["result"]["linked"]) == (1 if action == "link_automation" else 0)
    await client.send_json(
        {
            "id": 4,
            "type": "ble_esl/designer",
            "action": "link_automation",
            "entry_id": wolink_entry.entry_id,
            "entity_id": "sensor.invalid",
        }
    )
    assert not (await client.receive_json())["success"]


async def test_manual_association_follows_registry_rename_and_never_reuses_id(hass, wolink_entry):
    from custom_components.ble_esl.designer.manager import AutomationLinks

    registry = er.async_get(hass)
    original = registry.async_get_or_create(
        "automation", "automation", "original", suggested_object_id="original"
    )
    hass.states.async_set(original.entity_id, "on", {"id": "original"})
    links = AutomationLinks(hass)
    await links.update(wolink_entry, original.entity_id)
    registry.async_update_entity(original.entity_id, new_entity_id="automation.renamed")
    hass.states.async_remove(original.entity_id)
    hass.states.async_set("automation.renamed", "off", {"id": "original"})
    registry.async_get_or_create(
        "automation", "automation", "replacement", suggested_object_id="original"
    )
    hass.states.async_set("automation.original", "on", {"id": "replacement"})
    restored = AutomationLinks(hass)
    await restored.load()
    linked = restored.describe(wolink_entry)["linked"]
    assert len(linked) == 1 and linked[0]["entity_id"] == "automation.renamed"
    assert linked[0]["link_id"] == original.id
    registry.async_remove("automation.renamed")
    hass.states.async_remove("automation.renamed")
    missing = links.describe(wolink_entry)["linked"][0]
    assert missing["missing"] and missing["link_id"] == original.id
    await links.update(wolink_entry, "automation.original")
    assert len(links.describe(wolink_entry)["linked"]) == 2
    await links.update(wolink_entry, missing["entity_id"], remove=True, link_id=missing["link_id"])
    linked = links.describe(wolink_entry)["linked"]
    assert len(linked) == 1 and not linked[0]["missing"] and linked[0]["id"] == "replacement"


async def test_manual_config_id_fallback_survives_rename(hass, wolink_entry):
    from custom_components.ble_esl.designer.manager import AutomationLinks

    hass.states.async_set("automation.original", "on", {"id": "stable"})
    links = AutomationLinks(hass)
    await links.update(wolink_entry, "automation.original")
    hass.states.async_remove("automation.original")
    hass.states.async_set("automation.renamed", "off", {"id": "stable"})
    hass.states.async_set("automation.original", "on", {"id": "different"})
    restored = AutomationLinks(hass)
    await restored.load()
    linked = restored.describe(wolink_entry)["linked"]
    assert len(linked) == 1 and linked[0]["entity_id"] == "automation.renamed"
