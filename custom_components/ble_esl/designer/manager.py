"""Registry-backed ESL dashboard metadata and automation associations."""

from homeassistant.helpers import device_registry as dr, entity_registry as er

from ..const import DOMAIN

ENTITY_KEYS = {
    "alias": "text",
    "last_updated_content": "image",
    "display_in_sync": "binary_sensor",
    "write_duration": "sensor",
    "last_failure_time": "sensor",
    "failure_count": "sensor",
    "battery": "sensor",
}


def tag_metadata(hass, entry):
    """Resolve actual registered IDs, including renamed and disabled entities."""
    registry = er.async_get(hass)
    registered = er.async_entries_for_config_entry(registry, entry.entry_id)
    identifier = entry.runtime_data.identifier
    entities = {key: None for key in ENTITY_KEYS}
    for entity in registered:
        if entity.platform != DOMAIN:
            continue
        for key, domain in ENTITY_KEYS.items():
            if entity.domain == domain and entity.unique_id == f"ble_esl_{identifier}_{key}":
                entities[key] = entity.entity_id
        # PassiveBluetoothProcessorEntity uses address-battery[-device].
        if (
            entity.domain == "sensor"
            and (
                entity.unique_id == f"{entry.runtime_data.address}-battery"
                or entity.unique_id.startswith(f"{entry.runtime_data.address}-battery-")
            )
            and entities["battery"] is None
        ):
            entities["battery"] = entity.entity_id
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    device = next(
        (
            device
            for device in devices
            if (dr.CONNECTION_BLUETOOTH, entry.runtime_data.address) in device.connections
        ),
        None,
    )
    return {"device_id": device.id if device else None, "entities": entities}
