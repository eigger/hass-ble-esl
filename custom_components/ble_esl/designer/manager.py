"""Registry-backed ESL dashboard metadata and automation associations."""

import asyncio

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.storage import Store

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


def references_tag(config, device_ids, entity_ids):
    """Find literal direct targets; templates and unrelated strings are excluded."""
    if isinstance(config, dict):
        for key, value in config.items():
            if key in ("device_id", "entity_id"):
                targets = device_ids if key == "device_id" else entity_ids
                values = value if isinstance(value, list) else [value]
                if any(isinstance(item, str) and item in targets for item in values):
                    return True
            if references_tag(value, device_ids, entity_ids):
                return True
    elif isinstance(config, list):
        return any(references_tag(item, device_ids, entity_ids) for item in config)
    return False


class AutomationLinks:
    """Associate automations without writing or executing HA automation configs."""

    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, 1, f"{DOMAIN}.automation_links")
        self.links = {}
        self.lock = asyncio.Lock()

    def reference(self, entity_id):
        registered = er.async_get(self.hass).async_get(entity_id)
        state = self.hass.states.get(entity_id)
        return {
            "entity_id": entity_id,
            "registry_id": registered.id if registered else None,
            "config_id": registered.unique_id
            if registered
            else state.attributes.get("id")
            if state
            else None,
        }

    @staticmethod
    def link_id(reference):
        return reference.get("registry_id") or reference.get("config_id") or reference["entity_id"]

    def resolve(self, reference):
        if registry_id := reference.get("registry_id"):
            registered = er.async_get(self.hass).async_get(registry_id)
            return registered.entity_id if registered else None
        if config_id := reference.get("config_id"):
            return next(
                (
                    state.entity_id
                    for state in self.hass.states.async_all("automation")
                    if state.attributes.get("id") == config_id
                ),
                None,
            )
        # A removed legacy ID without a stable identity is never rebound.
        return None

    async def load(self):
        loaded = await self.store.async_load() or {}
        self.links = {
            entry_id: [self.reference(item) if isinstance(item, str) else item for item in items]
            for entry_id, items in loaded.items()
        }

    def describe(self, entry):
        registry = er.async_get(self.hass)
        entity_ids = {
            entity.entity_id
            for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        device_ids = {
            device.id
            for device in dr.async_entries_for_config_entry(dr.async_get(self.hass), entry.entry_id)
        }
        references = self.links.get(entry.entry_id, [])
        manual = {self.resolve(ref): ref for ref in references if self.resolve(ref)}
        component = self.hass.data.get("automation")
        available = []
        linked = []
        for state in self.hass.states.async_all("automation"):
            automation = component.get_entity(state.entity_id) if component else None
            config = getattr(automation, "raw_config", None)
            detected = references_tag(config, device_ids, entity_ids)
            details = {
                "entity_id": state.entity_id,
                "name": state.name,
                "state": state.state,
                "id": state.attributes.get("id"),
            }
            available.append(details)
            if state.entity_id in manual or detected:
                linked.append(
                    {
                        **details,
                        "source": "manual+detected"
                        if detected and state.entity_id in manual
                        else "detected"
                        if detected
                        else "manual",
                        "missing": False,
                        "link_id": self.link_id(manual[state.entity_id])
                        if state.entity_id in manual
                        else None,
                    }
                )
        live = {item["entity_id"] for item in available}
        for reference in references:
            entity_id = self.resolve(reference)
            if entity_id in live:
                continue
            registered = registry.async_get(reference.get("registry_id") or "")
            linked.append(
                {
                    "entity_id": entity_id or reference["entity_id"],
                    "name": (registered.name or registered.original_name or registered.entity_id)
                    if registered
                    else reference["entity_id"],
                    "state": "unavailable",
                    "id": reference.get("config_id"),
                    "source": "manual",
                    "missing": True,
                    "link_id": self.link_id(reference),
                }
            )
        available.sort(key=lambda item: (item["name"].casefold(), item["entity_id"]))
        linked.sort(key=lambda item: (item["name"].casefold(), item["entity_id"]))
        return {"linked": linked, "available": available}

    async def update(self, entry, entity_id, *, remove=False, link_id=None):
        if not entity_id.startswith("automation."):
            raise HomeAssistantError("Select an automation entity")
        if not remove and self.hass.states.get(entity_id) is None:
            raise HomeAssistantError("Automation is not available")
        async with self.lock:
            links = list(self.links.get(entry.entry_id, []))
            if remove:
                matches = (
                    [ref for ref in links if self.link_id(ref) == link_id]
                    if link_id
                    else [
                        ref for ref in links if (self.resolve(ref) or ref["entity_id"]) == entity_id
                    ]
                )
                if len(matches) > 1:
                    raise HomeAssistantError("Select the association to unlink")
                links = [ref for ref in links if ref not in matches]
            else:
                reference = self.reference(entity_id)
                if not reference["registry_id"] and not reference["config_id"]:
                    raise HomeAssistantError("Automation has no stable ID")
                if not any(self.link_id(ref) == self.link_id(reference) for ref in links):
                    links.append(reference)
            self.links[entry.entry_id] = links
            await self.store.async_save(self.links)
        return self.describe(entry)
