"""An optional visual editor layered over the existing render/write pipeline."""

import asyncio
import base64
import contextlib
from functools import partial
import json
import math
import os
from pathlib import Path
import re
import tempfile
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
from ..renderer import encode_png, oriented_preset, render_image
from ..services import build_write_job_from_data, cancel_pending_write, run_ble_write
from ..yaml11 import repair_yaml11_keys
from .design_templates import (
    build as build_template,
    check_name,
    describe as describe_template,
    load_all as load_design_templates,
    pick_id,
    template_text,
)
from .export import automation_draft, export_yaml, plain
from .importer import convert, different_pixels, elements_from, parse, payloads
from .layout import (
    LiveReport,
    compile_payload,
    frozen_items,
    live_payload,
    sensor_values,
    substitute,
    unsupported_items,
    validate,
    validate_template,
)
from .manager import AutomationLinks, tag_metadata
from .rendering import render_document, snapshot_layers
from .specs import (
    MissingTemplateParameter,
    describe,
    missing_template_parameters,
    resolve_templates,
)

KEY = f"{DOMAIN}_designer"
PANEL = "ble-esl-designer"
MAX_STRUCTURED_PAYLOAD_BYTES = 5 * 1024 * 1024
MAX_PREVIEW_VARIABLE_BYTES = 64 * 1024


def _preview_variable_map(value):
    """Accept bounded JSON values for preview only, never as document data."""
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise HomeAssistantError("Preview parameters must be a JSON object")

    def safe(candidate):
        if candidate is None or isinstance(candidate, str | bool | int):
            return True
        if isinstance(candidate, float):
            return math.isfinite(candidate)
        if isinstance(candidate, list):
            return all(safe(item) for item in candidate)
        if isinstance(candidate, dict):
            return all(
                isinstance(key, str)
                and key not in ("__proto__", "prototype", "constructor")
                and safe(item)
                for key, item in candidate.items()
            )
        return False

    try:
        if not safe(value):
            raise ValueError("not finite JSON or prototype key")
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError, RecursionError) as err:
        raise HomeAssistantError("Preview parameters must contain finite JSON values") from err
    if len(encoded) > MAX_PREVIEW_VARIABLE_BYTES:
        raise HomeAssistantError("Preview parameters are too large (64 KiB maximum)")
    return value


# A payload reads the forecast a Weather: Get forecasts step fetched into ``fc``.
FORECAST_VARIABLE = "fc"
_FORECAST_ENTITY = re.compile(r"""(?<![\w.])fc\s*\[\s*\\?['"](weather\.\w+)\\?['"]\s*\]""")


def forecast_entities(source):
    """The weather entities a design or payload reads from ``fc``."""
    try:
        text = json.dumps(source, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return []
    return sorted(set(_FORECAST_ENTITY.findall(text)))


def forecast_step(source):
    """The step that fetches the forecasts ``source`` reads, or None."""
    entities = forecast_entities(source)
    if not entities:
        return None
    return {
        "action": "weather.get_forecasts",
        "target": {"entity_id": entities},
        "data": {"type": "daily"},
        "response_variable": FORECAST_VARIABLE,
    }


class Designer:
    """Render layouts for preview, export or explicit transmission.

    Layouts live in automations (the ``ble_esl.write`` payload); unsaved work
    stays in the browser. Per-tag layouts are not stored here.
    """

    def __init__(self, hass):
        self.hass = hass
        self.automation_links = AutomationLinks(hass)
        self.template_store = Store(hass, 1, f"{DOMAIN}.sensor_templates")
        self.templates = {}
        self.design_templates = {}
        self.forecast_cache = {}
        self.forecast_failed = {}
        self.locks = {}
        self.render_lock = asyncio.Lock()
        self.template_lock = asyncio.Lock()
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
        # Claimed before the awaits so a concurrent entry setup does not
        # register it twice; released again if registration fails.
        self.panel_registered = True
        try:
            integration = await async_get_integration(self.hass, DOMAIN)
            await panel_custom.async_register_panel(
                self.hass,
                PANEL,
                "ble-esl-manager",
                sidebar_title="ESL Manager",
                sidebar_icon="mdi:label-multiple",
                module_url=f"/ble_esl_designer/{integration.version}/manager.js",
                config={"version": str(integration.version)},
                require_admin=True,
            )
        except BaseException:
            self.panel_registered = False
            raise

    @callback
    def remove_panel_if_unused(self, unloading_entry_id):
        if not self.panel_registered or any(
            entry.entry_id != unloading_entry_id
            for entry in self.hass.config_entries.async_loaded_entries(DOMAIN)
        ):
            return
        self.panel_registered = False
        frontend.async_remove_panel(self.hass, PANEL)

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

    async def forecast_variable(self, source, variables):
        """``variables`` with the forecast ``source`` reads, fetched as the automation will.

        What the user gave wins, and an entity without a forecast leaves the
        template to its own fallback. Only the preview uses it, so a provider
        that is slow or fails never stops a render: it is waited for briefly
        and not asked again for a minute.
        """
        entities = forecast_entities(source)
        if not entities or FORECAST_VARIABLE in variables:
            return variables
        forecast = {}
        for entity_id in entities:
            key = (entity_id, "daily")
            failed = self.forecast_failed.get(entity_id)
            if failed is not None and time.monotonic() - failed < 60:
                continue
            cached = self.forecast_cache.get(key)
            if cached and time.monotonic() - cached[0] < 600:
                forecast[entity_id] = {"forecast": cached[1]}
                continue
            try:
                async with asyncio.timeout(10):
                    response = await self.hass.services.async_call(
                        "weather",
                        "get_forecasts",
                        {"entity_id": entity_id, "type": "daily"},
                        blocking=True,
                        return_response=True,
                    )
                days = response[entity_id]["forecast"]
            except Exception:
                # Kept apart from the forecasts a write uses: a failure here is not one there.
                self.forecast_failed[entity_id] = time.monotonic()
                continue
            self.forecast_failed.pop(entity_id, None)
            self.forecast_cache[key] = (time.monotonic(), days)
            forecast[entity_id] = {"forecast": days}
        forecast = {entity: value for entity, value in forecast.items() if value["forecast"]}
        if not forecast:
            return variables
        # A week is what a design shows; more would only fill the preview's size limit.
        forecast = {e: {"forecast": v["forecast"][:7]} for e, v in forecast.items()}
        try:
            return _preview_variable_map({**variables, FORECAST_VARIABLE: forecast})
        except HomeAssistantError:
            return variables

    def preset(self, entry, rotate=0):
        """The preset a write would use now, refined by the last advertisement.

        ``rotate`` is the design's orientation: the canvas is then the logical one.
        """
        options = {**entry.data, **entry.options}
        preset = resolve_preset(
            self.hass,
            entry.runtime_data.protocol,
            entry.runtime_data.address,
            options.get(CONF_MODEL, DEFAULT_MODEL),
        ).preset
        return oriented_preset(preset, rotate)

    async def render(self, preset, document, payload, snapshots):
        # Font/image allocation is expensive on small HA hosts. Keep all designer
        # clients to one render worker at a time.
        async with self.render_lock:
            return await self.hass.async_add_executor_job(
                partial(render_document, self.hass, preset, document, payload, snapshots)
            )

    async def draw(self, entry, document, preview_variables=None):
        """Render without touching the tag's runtime data or preview entity."""
        preset = self.preset(entry, document.get("rotate", 0))
        document = validate(document, preset)
        forecasts = await self.forecasts(document)
        preview_variables = await self.forecast_variable(
            document, _preview_variable_map(preview_variables)
        )
        snapshots = snapshot_layers(
            self.hass, document, self.templates, forecasts, preview_variables
        )
        # The elements' payloads in order are the document's payload: one
        # evaluation of every template serves the display and the layers.
        payload = [item for _, part in snapshots for item in part]
        image, layers = await self.render(preset, document, payload, snapshots)
        return document, image, payload, layers

    async def _png_data_url(self, image):
        """The image as a PNG data: URL, encoded off the event loop."""
        png = await self.hass.async_add_executor_job(encode_png, image)
        return "data:image/png;base64," + base64.b64encode(png).decode()

    async def preview(self, entry, document, preview_variables=None):
        _, image, payload, layers = await self.draw(entry, document, preview_variables)
        return {
            "png": await self._png_data_url(image),
            "payload": payload,
            "layers": layers,
        }

    async def export(self, entry, document, preview_variables=None):
        """The display as YAML for an automation: what the preview shows, as a payload."""
        preset = self.preset(entry, document.get("rotate", 0))
        document = validate(document, preset)
        preview_variables = await self.forecast_variable(
            document, _preview_variable_map(preview_variables)
        )
        # A payload has no forecast: an element that wants one is refused below.
        forecasts = {}
        payload = compile_payload(
            self.hass,
            document,
            self.templates,
            forecasts,
            preview_variables=preview_variables,
        )
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
        # Only the payload is saved: what a payload cannot keep live is as of now.
        report = LiveReport()
        automation_payload = live_payload(
            self.hass, document, self.templates, forecasts, preview_variables, report
        )
        frozen = frozen_items(document, report.live)
        issues.extend(f"blocking: {item}" for item in unsupported_items(document, payload))
        issues.extend(frozen)
        result = export_yaml(
            payload,
            document["background"],
            entry.runtime_data.device_id,
            issues,
            automation_payload,
            rotate=document.get("rotate", 0),
        )
        result["frozen"] = frozen
        # The designer needs the typed value when applying an edit to an existing
        # action; the YAML strings remain the public export representation.
        result["payload_data"] = (
            plain(payload if automation_payload is None else automation_payload)
            if not result["validation_errors"]
            else None
        )
        result["writable"] = getattr(entry.runtime_data.protocol, "writable", True)
        # What the payload reads from the run, that the automation has to set first.
        step = forecast_step(result["payload_data"] or payload)
        result["setup_actions"] = [step] if step else []
        return result

    async def automation(self, entry, document, preview_variables=None, defaults=None):
        """Prepare a new automation from the current, possibly unsaved design."""
        result = await self.export(entry, document, preview_variables)
        if not result["writable"]:
            raise HomeAssistantError("This ESL does not support writing")
        if not entry.runtime_data.device_id:
            raise HomeAssistantError("This ESL has no registered device")
        if defaults is None or "triggers" not in defaults:
            validated = validate(document, self.preset(entry))
            layers = snapshot_layers(
                self.hass,
                validated,
                self.templates,
                {},
                preview_variables=preview_variables,
            )
            entities = sorted(
                {
                    entity
                    for element, _ in layers
                    for entity in [element.get("entity_id"), *element.get("_template_entities", [])]
                    if entity and not entity.startswith("{{")
                }
            )
            result["input_triggers"] = bool(entities)
            defaults = {
                "mode": "queued",
                "max": 2,
                "max_exceeded": "silent",
                **(defaults or {}),
                "triggers": (
                    [
                        {
                            "trigger": "state",
                            "entity_id": entities,
                            # State changes only; skip attribute-only updates and
                            # entering unavailable/unknown, so a tag keeps its last
                            # reading and shows the new one once the entity returns.
                            "not_to": ["unavailable", "unknown"],
                        }
                    ]
                    if entities
                    else []
                ),
            }
        return {**result, "automation": automation_draft(result, entry.title, defaults)}

    @property
    def user_template_dir(self):
        return Path(self.hass.config.path("ble_esl", "templates"))

    async def _reload_design_templates(self):
        self.design_templates = await self.hass.async_add_executor_job(
            load_design_templates, self.user_template_dir
        )

    async def reload_design_templates(self):
        # Under the lock, so a reload that began before a save cannot finish after it.
        async with self.template_lock:
            await self._reload_design_templates()

    async def save_design_template(self, entry, document, name, template_id=None, overwrite=False):
        """Keep the current design as a template in the user's template folder."""
        name = check_name(name)
        exported = await self.export(entry, document)
        if exported["validation_errors"]:
            raise HomeAssistantError(
                "Fix the design first: " + "; ".join(exported["validation_errors"][:3])
            )
        preset = self.preset(entry, document.get("rotate", 0))
        background = validate(document, preset)["background"]

        def write(template_id, file_name):
            folder = self.user_template_dir
            folder.mkdir(parents=True, exist_ok=True)
            text = template_text(
                template_id, name, preset.width, preset.height, background, exported["payload_data"]
            )
            # Written beside the target and moved into place: a gallery reload
            # never reads half a file, and a symlink at the target is replaced.
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=folder, suffix=".tmp", delete=False
            ) as handle:
                try:
                    handle.write(text)
                    handle.flush()
                    # Like a hand-made file, not the private mode a temp file gets.
                    os.chmod(handle.name, 0o644)
                    os.replace(handle.name, folder / file_name)
                except BaseException:
                    with contextlib.suppress(OSError):
                        os.unlink(handle.name)
                    raise
            return text

        requested = template_id

        def save():
            folder = self.user_template_dir
            template_id, file_name = pick_id(
                name,
                requested,
                overwrite,
                self.design_templates,
                lambda candidate: (folder / candidate).exists(),
            )
            return template_id, write(template_id, file_name)

        # One save at a time: the id is chosen and the file written under the lock.
        async with self.template_lock:
            template_id, text = await self.hass.async_add_executor_job(save)
            await self._reload_design_templates()
        return {"id": template_id, "yaml": text}

    def design_template_list(self, entry, rotate=0):
        """The ready-made designs, described for this tag's display."""
        preset = self.preset(entry, rotate)
        return [
            describe_template(template, preset.width, preset.height)
            for template in self.design_templates.values()
        ]

    async def ensure_template_inputs(self, template, values, entities=None):
        """Raise when a font or an entity a template was given does not exist.

        ``entities`` limits the entity check to those parameter names (all when None).
        """
        kinds = {name: parameter["type"] for name, parameter in template["parameters"].items()}
        absent = sorted(
            value
            for name, value in values.items()
            if kinds[name] == "entity"
            and (entities is None or name in entities)
            and self.hass.states.get(value) is None
        )
        if absent:
            raise HomeAssistantError(f"Entity not found: {', '.join(absent)}")
        fonts = {value for name, value in values.items() if kinds[name] == "font"}
        missing = await self.hass.async_add_executor_job(self.missing_fonts, fonts)
        if missing:
            raise HomeAssistantError(f"Font not found: {', '.join(sorted(missing))}")

    async def preview_design_template(self, entry, template_id, parameters=None, rotate=0):
        """A design template drawn for this tag, as the real renderer shows it now.

        Values not given use their defaults; a default entity that does not
        exist is replaced by the first one of its domain, so a gallery of
        thumbnails works on any system. Nothing is imported or saved.
        """
        template = self.design_templates.get(template_id)
        if template is None:
            raise HomeAssistantError(f"There is no design template {template_id}")
        preset = self.preset(entry, rotate)
        given = dict(parameters or {})
        for name, parameter in template["parameters"].items():
            if parameter["type"] != "entity" or name in given:
                continue
            if self.hass.states.get(parameter["default"]) is None and "domain" in parameter:
                candidates = sorted(self.hass.states.async_entity_ids(parameter["domain"]))
                if candidates:
                    given[name] = candidates[0]
        built = build_template(template, preset.width, preset.height, preset.colors, given)
        # What was given must exist, as when applying; defaults are only drawn.
        await self.ensure_template_inputs(template, built["parameters"], set(given))
        payload = resolve_templates(self.hass, built["payload"], set())
        async with self.render_lock:
            image = await self.hass.async_add_executor_job(
                partial(render_image, self.hass, preset, payload, background=built["background"])
            )
        return {
            "png": await self._png_data_url(image),
            "layout": built["layout"],
            "scaled": built["scaled"],
        }

    async def apply_design_template(
        self,
        entry,
        template_id,
        parameters=None,
        existing=0,
        preview_variables=None,
        rotate=0,
    ):
        """A design template's elements for this tag, imported like a pasted payload."""
        template = self.design_templates.get(template_id)
        if template is None:
            raise HomeAssistantError(f"There is no design template {template_id}")
        preset = self.preset(entry, rotate)
        built = build_template(template, preset.width, preset.height, preset.colors, parameters)
        await self.ensure_template_inputs(template, built["parameters"])
        imported = await self.import_payload(
            entry, built["payload"], built["background"], existing, preview_variables, rotate
        )
        return {
            **imported,
            "template": {
                "id": template_id,
                "layout": built["layout"],
                "scaled": built["scaled"],
                "parameters": built["parameters"],
                "automation": built["automation"],
            },
        }

    def missing_fonts(self, fonts):
        """Font files neither bundled with the integration nor in ``www/fonts``."""
        folders = (Path(__file__).parent.parent / "fonts", Path(self.hass.config.path("www/fonts")))
        return {font for font in fonts if not any((folder / font).is_file() for folder in folders)}

    async def import_yaml(self, entry, text, existing=0, preview_variables=None, rotate=0):
        """Elements for a pasted payload, and how faithfully they stand for it."""
        items, background = parse(text)
        return await self.import_payload(
            entry, items, background, existing, preview_variables, rotate
        )

    async def import_payload(
        self, entry, items, background=None, existing=0, preview_variables=None, rotate=0
    ):
        """Import a structured automation payload without YAML size/alias handling."""
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise HomeAssistantError("The automation payload must be a list of objects")
        if len(json.dumps(items, ensure_ascii=False).encode()) > MAX_STRUCTURED_PAYLOAD_BYTES:
            raise HomeAssistantError(
                "The automation payload is too large to import (5 MiB maximum)"
            )
        items = repair_yaml11_keys(items)
        preset = self.preset(entry, rotate)
        preview_variables = await self.forecast_variable(
            items, _preview_variable_map(preview_variables)
        )
        elements, imported, issues = elements_from(items, preset, max(0, 100 - existing))
        different = None
        if elements:
            try:
                original, rebuilt = payloads(self.hass, imported, elements, preview_variables)
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
            except MissingTemplateParameter as err:
                missing = set(missing_template_parameters(self.hass, imported, preview_variables))
                missing.add(err.name)
                return {
                    "missing_parameters": sorted(missing),
                    "elements": [],
                    "issues": [],
                    "different_pixels": None,
                    "background": background,
                }
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
        preset = self.preset(entry, document.get("rotate", 0))
        document = validate(document, preset)
        element = next((el for el in document["elements"] if el["id"] == element_id), None)
        if element is None:
            raise HomeAssistantError("That element is not in the display")
        if element["type"] == "imagespec":
            raise HomeAssistantError("That is an imagespec element already")
        return await self._convert_element(preset, len(document["elements"]), element)

    async def _convert_element(self, preset, count, element):
        alone = {"elements": [element]}
        forecasts = await self.forecasts(alone)
        # Checked once the element is known to turn into how many: see below.
        snapshots = snapshot_layers(self.hass, alone, self.templates, forecasts)
        items = snapshots[0][1]
        if count - 1 + len(items) > 100:
            raise HomeAssistantError(
                f"Converting would make {count - 1 + len(items)} elements; a display holds 100"
            )
        # The same items with what follows the entity written as templates.
        report = LiveReport()
        live = compile_payload(
            self.hass, alone, self.templates, forecasts, keep_templates=True, report=report
        )
        if len(live) != len(items):
            live, report = items, LiveReport()
        frozen = frozen_items(alone, report.live)
        elements, issues, original, rebuilt = convert(self.hass, items, live, preset)
        different = None
        if elements:
            try:
                async with self.render_lock:
                    different = await self.hass.async_add_executor_job(
                        partial(different_pixels, self.hass, preset, original, rebuilt)
                    )
            except HomeAssistantError as err:
                issues.append(f"render: {err}")
        return {
            "elements": elements,
            "issues": issues,
            "different_pixels": different,
            "frozen": frozen,
        }

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
        return {
            "png": await self._png_data_url(image),
            "payload": payload,
            "layers": layers,
        }

    async def send(self, entry, document):
        if not getattr(entry.runtime_data.protocol, "writable", True):
            raise HomeAssistantError("This ESL protocol does not support image writes")
        generation = entry.runtime_data.write_generation
        async with self.locks.setdefault(entry.entry_id, asyncio.Lock()):
            document, image, payload, _ = await self.draw(entry, document)
            # An advertisement can refine the preset while drawing awaits.
            # Check before build_write_job_from_data publishes the preview; it
            # resolves the preset again before its first await, so nothing can
            # change in between.
            orientation = document.get("rotate", 0)
            preset = self.preset(entry, orientation)
            if (preset.width, preset.height) != image.size:
                raise HomeAssistantError("The ESL's display size changed; reload the designer")
            if orientation:
                image = await self.hass.async_add_executor_job(
                    lambda: image.rotate(-orientation, expand=True)
                )
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
                "preview",
                "export",
                "automation",
                "import_yaml",
                "import_payload",
                "convert",
                "send",
                "templates",
                "design_templates",
                "apply_design_template",
                "preview_design_template",
                "save_design_template",
                "save_template",
                "preview_template",
                "automations",
                "automation_edit_source",
                "link_automation",
                "unlink_automation",
            )
        ),
        vol.Optional("entry_id"): str,
        vol.Optional("rotation"): vol.In((0, 90, 180, 270)),
        vol.Optional("document"): dict,
        vol.Optional("preview_variables"): dict,
        vol.Optional("text"): str,
        vol.Optional("payload"): [dict],
        vol.Optional("background"): str,
        vol.Optional("existing"): vol.All(int, vol.Range(min=0, max=1000)),
        vol.Optional("element_id"): str,
        vol.Optional("template"): dict,
        vol.Optional("key"): str,
        vol.Optional("entity_id"): str,
        vol.Optional("link_id"): str,
        vol.Optional("template_id"): str,
        vol.Optional("name"): str,
        vol.Optional("overwrite"): bool,
        vol.Optional("parameters"): dict,
        vol.Optional("automation_defaults"): vol.Schema(
            {
                vol.Optional("alias"): str,
                vol.Optional("description"): str,
                vol.Optional("triggers"): [dict],
                vol.Optional("conditions"): [dict],
                vol.Optional("actions"): [dict],
                vol.Optional("mode"): vol.In(("single", "restart", "queued", "parallel")),
            }
        ),
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
    elif action == "preview_design_template":
        if "template_id" not in msg:
            raise HomeAssistantError("template_id is required")
        result = await designer.preview_design_template(
            designer.entry(msg["entry_id"]),
            msg["template_id"],
            msg.get("parameters"),
            msg.get("rotation", 0),
        )
    elif action == "save_design_template":
        result = await designer.save_design_template(
            designer.entry(msg["entry_id"]),
            msg["document"],
            msg.get("name"),
            msg.get("template_id"),
            msg.get("overwrite", False),
        )
    elif action == "design_templates":
        await designer.reload_design_templates()
        result = designer.design_template_list(
            designer.entry(msg["entry_id"]), msg.get("rotation", 0)
        )
    elif action == "apply_design_template":
        if "template_id" not in msg:
            raise HomeAssistantError("template_id is required")
        result = await designer.apply_design_template(
            designer.entry(msg["entry_id"]),
            msg["template_id"],
            msg.get("parameters"),
            msg.get("existing", 0),
            msg.get("preview_variables"),
            msg.get("rotation", 0),
        )
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
            }
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        ]
    elif action == "automations":
        result = designer.automation_links.describe(designer.entry(msg["entry_id"]))
    elif action == "automation_edit_source":
        result = designer.automation_links.edit_source(
            designer.entry(msg["entry_id"]), msg["entity_id"]
        )
    elif action in ("link_automation", "unlink_automation"):
        result = await designer.automation_links.update(
            designer.entry(msg["entry_id"]),
            msg["entity_id"],
            remove=action == "unlink_automation",
            link_id=msg.get("link_id"),
        )
    elif action == "import_yaml":
        result = await designer.import_yaml(
            designer.entry(msg["entry_id"]),
            msg["text"],
            msg.get("existing", 0),
            msg.get("preview_variables"),
            msg.get("rotation", 0),
        )
    elif action == "import_payload":
        result = await designer.import_payload(
            designer.entry(msg["entry_id"]),
            msg["payload"],
            msg.get("background"),
            msg.get("existing", 0),
            msg.get("preview_variables"),
            msg.get("rotation", 0),
        )
    elif action == "convert":
        result = await designer.convert(
            designer.entry(msg["entry_id"]), msg["document"], msg["element_id"]
        )
    elif action == "export":
        result = await designer.export(
            designer.entry(msg["entry_id"]),
            msg["document"],
            msg.get("preview_variables"),
        )
    elif action == "automation":
        result = await designer.automation(
            designer.entry(msg["entry_id"]),
            msg["document"],
            msg.get("preview_variables"),
            msg.get("automation_defaults"),
        )
    elif action == "preview":
        result = await designer.preview(
            designer.entry(msg["entry_id"]),
            msg["document"],
            msg.get("preview_variables"),
        )
    else:  # send
        result = await designer.send(designer.entry(msg["entry_id"]), msg["document"])
    connection.send_result(msg["id"], result)


async def async_setup_designer(hass):
    designer = hass.data[KEY] = Designer(hass)
    # Earlier versions kept one layout per tag in ".storage/ble_esl.designer".
    # It is no longer read or written; the file is left as it is.
    await designer.reload_design_templates()
    designer.templates = await designer.template_store.async_load() or {}
    await designer.automation_links.load()
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
