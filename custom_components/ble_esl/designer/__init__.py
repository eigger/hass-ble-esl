"""An optional visual editor layered over the existing render/write pipeline."""

import asyncio
import base64
from functools import partial
from io import BytesIO
from pathlib import Path
import time

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration
import voluptuous as vol

from ..const import CONF_MODEL, DEFAULT_MODEL, DOMAIN
from ..device import resolve_preset
from ..esl_ble.base import DevicePreset
from ..renderer import render_image
from ..services import build_write_job_from_data, cancel_pending_write, run_ble_write
from .export import export_yaml
from .importer import convert, different_pixels, elements_from, parse, payloads
from .layout import (
    compile_payload,
    live_payload,
    sensor_values,
    substitute,
    validate,
    validate_template,
)
from .manager import tag_metadata
from .rendering import render_document, snapshot_layers
from .specs import describe, frozen_corners

KEY = f"{DOMAIN}_designer"
PANEL = "ble-esl-designer"


class Designer:
    """Persist layouts and render them for preview or explicit transmission."""

    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, 1, f"{DOMAIN}.designer")
        self.documents = {}
        self.template_store = Store(hass, 1, f"{DOMAIN}.sensor_templates")
        self.templates = {}
        self.forecast_cache = {}
        self.locks = {}
        self.render_lock = asyncio.Lock()
        self.panel_registered = False

    def entry(self, entry_id):
        for entry in self.hass.config_entries.async_loaded_entries(DOMAIN):
            if entry.entry_id == entry_id:
                return entry
        raise HomeAssistantError(f"Tag {entry_id} is not loaded")

    async def register_panel(self):
        """Show the sidebar panel while at least one tag is configured."""
        if self.panel_registered:
            return
        self.panel_registered = True
        integration = await async_get_integration(self.hass, DOMAIN)
        await panel_custom.async_register_panel(
            self.hass,
            PANEL,
            PANEL,
            sidebar_title="ESL Designer",
            sidebar_icon="mdi:label-outline",
            module_url=f"/ble_esl_designer/{integration.version}/panel.js",
            config={"version": str(integration.version)},
            require_admin=True,
        )

    @callback
    def remove_panel_if_unused(self, unloading_entry_id):
        if not self.panel_registered or any(
            entry.entry_id != unloading_entry_id
            for entry in self.hass.config_entries.async_loaded_entries(DOMAIN)
        ):
            return
        self.panel_registered = False
        frontend.async_remove_panel(self.hass, PANEL)

    async def save(self, entry, document):
        document = validate(document, self.preset(entry))
        self.documents[entry.entry_id] = document
        await self.store.async_save(self.documents)
        cancel_pending_write(entry.runtime_data)
        return document

    async def forecasts(self, document):
        needed = {
            (el["entity_id"], "hourly" if el["weather_when"] == "later_today" else "daily")
            for el in document["elements"]
            if el["entity_id"].startswith("weather.") and el["weather_when"] != "now"
        }
        result = {}
        for entity_id, forecast_type in needed:
            key = (entity_id, forecast_type)
            cached = self.forecast_cache.get(key)
            if not cached or time.monotonic() - cached[0] >= 600:
                response = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"entity_id": entity_id, "type": forecast_type},
                    blocking=True,
                    return_response=True,
                )
                cached = self.forecast_cache[key] = (
                    time.monotonic(),
                    response[entity_id]["forecast"],
                )
            result[key] = cached[1]
        return result

    def preset(self, entry):
        """The preset a write would use now, refined by the last advertisement."""
        options = {**entry.data, **entry.options}
        return resolve_preset(
            self.hass,
            entry.runtime_data.protocol,
            entry.runtime_data.address,
            options.get(CONF_MODEL, DEFAULT_MODEL),
        ).preset

    async def render(self, preset, document, payload, snapshots):
        # Font/image allocation is expensive on small HA hosts. Keep all designer
        # clients to one render worker at a time.
        async with self.render_lock:
            return await self.hass.async_add_executor_job(
                partial(render_document, self.hass, preset, document, payload, snapshots)
            )

    async def draw(self, entry, document):
        """Render without touching the tag's runtime data or preview entity."""
        preset = self.preset(entry)
        document = validate(document, preset)
        forecasts = await self.forecasts(document)
        snapshots = snapshot_layers(self.hass, document, self.templates, forecasts)
        # The elements' payloads in order are the document's payload: one
        # evaluation of every template serves the display and the layers.
        payload = [item for _, part in snapshots for item in part]
        image, layers = await self.render(preset, document, payload, snapshots)
        return document, image, payload, layers

    async def preview(self, entry, document):
        _, image, payload, layers = await self.draw(entry, document)
        buffer = BytesIO()
        image.save(buffer, "PNG")
        return {
            "png": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(),
            "payload": payload,
            "layers": layers,
        }

    async def export(self, entry, document):
        """The display as YAML for an automation: what the preview shows, as a payload."""
        preset = self.preset(entry)
        document = validate(document, preset)
        forecasts = await self.forecasts(document)
        payload = compile_payload(self.hass, document, self.templates, forecasts)
        issues = []
        try:
            # imagespec.validate() misses what only rendering finds, e.g. an unknown icon.
            async with self.render_lock:
                await self.hass.async_add_executor_job(
                    partial(
                        render_image, self.hass, preset, payload, background=document["background"]
                    )
                )
        except HomeAssistantError as err:
            issues.append(f"render: {err}")
        issues.extend(
            f"{element['id']}: the polygon's corners are as of now in the live YAML"
            for element in document["elements"]
            if element["type"] == "imagespec" and frozen_corners(element["spec"])
        )
        result = export_yaml(
            payload,
            document["background"],
            entry.runtime_data.device_id,
            issues,
            live_payload(self.hass, document, self.templates, forecasts),
        )
        result["writable"] = getattr(entry.runtime_data.protocol, "writable", True)
        return result

    async def import_yaml(self, entry, text, existing=0):
        """Elements for a pasted payload, and how faithfully they stand for it."""
        preset = self.preset(entry)
        items, background = parse(text)
        elements, imported, issues = elements_from(items, preset, max(0, 100 - existing))
        different = None
        if elements:
            try:
                original, rebuilt = payloads(self.hass, imported, elements)
                async with self.render_lock:
                    different = await self.hass.async_add_executor_job(
                        partial(
                            different_pixels,
                            self.hass,
                            preset,
                            original,
                            rebuilt,
                            background
                            if background in ("white", "black", "red", "yellow")
                            else "white",
                        )
                    )
            except HomeAssistantError as err:
                issues.append(f"render: {err}")
        return {
            "elements": elements,
            "issues": issues,
            "different_pixels": different,
            "background": background,
        }

    async def convert(self, entry, document, element_id):
        """One element of the old kinds as imagespec elements to edit field by field."""
        preset = self.preset(entry)
        document = validate(document, preset)
        element = next((el for el in document["elements"] if el["id"] == element_id), None)
        if element is None:
            raise HomeAssistantError("That element is not in the display")
        if element["type"] == "imagespec":
            raise HomeAssistantError("That is an imagespec element already")
        alone = {"elements": [element]}
        forecasts = await self.forecasts(alone)
        # Checked once the element is known to turn into how many: see below.
        snapshots = snapshot_layers(self.hass, alone, self.templates, forecasts)
        items = snapshots[0][1]
        if len(document["elements"]) - 1 + len(items) > 100:
            raise HomeAssistantError(
                f"Converting would make {len(document['elements']) - 1 + len(items)} elements; "
                "a display holds 100"
            )
        state = self.hass.states.get(element["entity_id"]) if element["entity_id"] else None
        elements, issues, original, rebuilt = convert(self.hass, element, state, items, preset)
        different = None
        if elements:
            try:
                async with self.render_lock:
                    different = await self.hass.async_add_executor_job(
                        partial(different_pixels, self.hass, preset, original, rebuilt)
                    )
            except HomeAssistantError as err:
                issues.append(f"render: {err}")
        return {"elements": elements, "issues": issues, "different_pixels": different}

    async def save_template(self, key, template):
        if not key or ":" not in key:
            raise HomeAssistantError("Choose a sensor type")
        self.templates[key] = validate_template(template)
        await self.template_store.async_save(self.templates)
        for entry in self.hass.config_entries.async_loaded_entries(DOMAIN):
            cancel_pending_write(entry.runtime_data)
        return self.templates[key]

    async def preview_template(self, template, entity_id):
        template = validate_template(template)
        state = self.hass.states.get(entity_id)
        if state is None:
            raise HomeAssistantError("Choose an available sample entity")
        document = substitute(template["document"], sensor_values(state, {}), state.state, state)
        snapshots = snapshot_layers(self.hass, document, {}, {})
        payload = [item for _, part in snapshots for item in part]
        preset = DevicePreset("template", "Template", template["width"], template["height"], "BWRY")
        image, layers = await self.render(preset, document, payload, snapshots)
        buffer = BytesIO()
        image.save(buffer, "PNG")
        return {
            "png": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(),
            "payload": payload,
            "layers": layers,
        }

    async def send(self, entry, document):
        if not getattr(entry.runtime_data.protocol, "writable", True):
            raise HomeAssistantError("This tag protocol does not support image writes")
        generation = entry.runtime_data.write_generation
        async with self.locks.setdefault(entry.entry_id, asyncio.Lock()):
            document, image, payload, _ = await self.draw(entry, document)
            # An advertisement can refine the preset while drawing awaits.
            # Check before build_write_job_from_data publishes the preview; it
            # resolves the preset again before its first await, so nothing can
            # change in between.
            preset = self.preset(entry)
            if (preset.width, preset.height) != image.size:
                raise HomeAssistantError("The tag's display size changed; reload the designer")
            service_data = {"payload": payload, "background": document["background"]}
            job = await build_write_job_from_data(self.hass, entry, service_data, image=image)
            # Explicit sends also restore a tag that was reset externally.
            job.prevent_duplicate_send = False
            job.generation = generation
            outcome = await run_ble_write(self.hass, job)
            return outcome.as_response()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ble_esl/designer",
        vol.Required("action"): vol.In(
            (
                "list",
                "specs",
                "save",
                "preview",
                "export",
                "import_yaml",
                "convert",
                "send",
                "templates",
                "save_template",
                "preview_template",
            )
        ),
        vol.Optional("entry_id"): str,
        vol.Optional("document"): dict,
        vol.Optional("text"): str,
        vol.Optional("existing"): vol.All(int, vol.Range(min=0, max=1000)),
        vol.Optional("element_id"): str,
        vol.Optional("template"): dict,
        vol.Optional("key"): str,
        vol.Optional("entity_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_designer(hass, connection, msg):
    designer = hass.data[KEY]
    action = msg["action"]
    if action == "specs":
        result = describe()
    elif action == "templates":
        result = designer.templates
    elif action == "save_template":
        result = await designer.save_template(msg["key"], msg["template"])
    elif action == "preview_template":
        result = await designer.preview_template(msg["template"], msg["entity_id"])
    elif action == "list":
        result = [
            {
                **tag_metadata(hass, entry),
                "entry_id": entry.entry_id,
                "title": entry.title,
                "width": (preset := designer.preset(entry)).width,
                "height": preset.height,
                "colors": preset.colors,
                "writable": getattr(entry.runtime_data.protocol, "writable", True),
                "document": designer.documents.get(entry.entry_id),
            }
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        ]
    elif action == "import_yaml":
        result = await designer.import_yaml(
            designer.entry(msg["entry_id"]), msg["text"], msg.get("existing", 0)
        )
    elif action == "convert":
        result = await designer.convert(
            designer.entry(msg["entry_id"]), msg["document"], msg["element_id"]
        )
    else:
        entry = designer.entry(msg["entry_id"])
        result = await getattr(designer, action)(entry, msg["document"])
    connection.send_result(msg["id"], result)


async def async_setup_designer(hass):
    designer = hass.data[KEY] = Designer(hass)
    designer.documents = await designer.store.async_load() or {}
    # Old designs may have opted into automatic writes. Discard those options
    # durably without validating against a possibly unavailable tag preset.
    migrated = False
    for document in designer.documents.values():
        for key in ("auto_update", "interval"):
            if key in document:
                document.pop(key)
                migrated = True
    if migrated:
        await designer.store.async_save(designer.documents)
    designer.templates = await designer.template_store.async_load() or {}
    websocket_api.async_register_command(hass, websocket_designer)
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [
            # Versioned URL so an update never serves stale cached modules.
            StaticPathConfig(
                f"/ble_esl_designer/{integration.version}",
                str(Path(__file__).parent / "frontend"),
                False,
            ),
            StaticPathConfig(
                "/ble_esl_designer_fonts", str(Path(__file__).parent.parent / "fonts"), True
            ),
        ]
    )
