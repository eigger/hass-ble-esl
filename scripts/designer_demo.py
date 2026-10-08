"""Local visual QA using the real renderer; no Bluetooth access or writes.

Run from the repository root: .venv/bin/python scripts/designer_demo.py
"""

import asyncio
import base64
from copy import deepcopy
from datetime import timedelta
from html import escape
from io import BytesIO
import json
from pathlib import Path
import sys

from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.ble_esl.designer import _preview_variable_map
from custom_components.ble_esl.designer.design_templates import (
    build as build_template,
    describe as describe_template,
    load_templates,
    parse_template,
    slug,
    template_text,
)
from custom_components.ble_esl.designer.export import automation_draft, export_yaml, plain
from custom_components.ble_esl.designer.importer import (
    convert,
    different_pixels,
    elements_from,
    parse as parse_payload,
    payloads,
)
from custom_components.ble_esl.designer.layout import (
    compile_payload,
    live_payload,
    sensor_values,
    substitute,
    validate,
    validate_template,
)
from custom_components.ble_esl.designer.rendering import render_document, snapshot_layers
from custom_components.ble_esl.designer.specs import (
    MissingTemplateParameter,
    describe,
    frozen_corners,
)
from custom_components.ble_esl.esl_ble.base import DevicePreset

ROOT = Path(__file__).resolve().parents[1]
DESIGN_TEMPLATES = load_templates()
STATES = {
    "sensor.office_temperature": {
        "entity_id": "sensor.office_temperature",
        "state": "21.3",
        "attributes": {
            "friendly_name": "Office temperature",
            "device_class": "temperature",
            "unit_of_measurement": "°C",
        },
    },
    "sensor.office_humidity": {
        "entity_id": "sensor.office_humidity",
        "state": "46",
        "attributes": {
            "friendly_name": "Office humidity",
            "device_class": "humidity",
            "unit_of_measurement": "%",
        },
    },
    "sensor.desk_power": {
        "entity_id": "sensor.desk_power",
        "state": "38.2",
        "attributes": {
            "friendly_name": "Desk power",
            "device_class": "power",
            "unit_of_measurement": "W",
        },
    },
    "binary_sensor.window": {
        "entity_id": "binary_sensor.window",
        "state": "off",
        "attributes": {"friendly_name": "Office window", "device_class": "window"},
    },
}
STATES["weather.home"] = {
    "entity_id": "weather.home",
    "state": "cloudy",
    "attributes": {"friendly_name": "Weather", "temperature": 18.5, "temperature_unit": "°C"},
}
TEMPLATES = {}
TAGS = [
    {
        "entry_id": "demo-writable",
        "title": "Demo BWR display",
        "width": 250,
        "height": 122,
        "colors": "BWR",
        "writable": True,
        "document": None,
    },
    {
        "entry_id": "demo-discovery",
        "title": "Demo BWRY display (discovery only)",
        "width": 200,
        "height": 200,
        "colors": "BWRY",
        "writable": False,
        "document": None,
    },
]
for index, tag in enumerate(TAGS):
    tag["device_id"] = f"demo-device-{index}"
    tag["entities"] = {
        key: f"{domain}.demo_{index}_{key}"
        for key, domain in {
            "alias": "text",
            "battery": "sensor",
            "battery_low": "binary_sensor",
            "last_updated_content": "image",
            "display_in_sync": "binary_sensor",
            "write_duration": "sensor",
            "last_failure_time": "sensor",
            "failure_count": "sensor",
        }.items()
    }

    def demo_state(key, value, attributes=None, tag=tag):
        entity_id = tag["entities"][key]
        STATES[entity_id] = {"entity_id": entity_id, "state": value, "attributes": attributes or {}}

    demo_state("alias", ["Living room", "Desk display"][index])
    demo_state("battery", ["85", "42"][index], {"unit_of_measurement": "%"})
    demo_state("battery_low", "off")
    demo_state(
        "last_updated_content", dt_util.utcnow().isoformat(), {"entity_picture": "/demo-image"}
    )
    demo_state("display_in_sync", "on" if index == 0 else "off")
    demo_state(
        "write_duration",
        "3.2",
        {"success": index == 0, "error": None if index == 0 else "Bluetooth connection timed out"},
    )
AUTOMATIONS = [
    {
        "entity_id": "automation.morning",
        "name": "Morning information",
        "state": "on",
        "id": "morning",
    },
    {
        "entity_id": "automation.temperature",
        "name": "Temperature display",
        "state": "on",
        "id": "temperature",
    },
    {"entity_id": "automation.night", "name": "Night screen", "state": "off", "id": "night"},
    {"entity_id": "automation.weekly", "name": "Weekly summary", "state": "off", "id": "weekly"},
]
AUTOMATION_LINKS = {
    "demo-writable": ["automation.morning", "automation.temperature", "automation.night"]
}
AUTOMATION_CONFIGS = {
    item["id"]: {
        "id": item["id"],
        "alias": item["name"],
        "triggers": [{"trigger": "time", "at": "07:00:00"}],
        "conditions": [
            {
                "condition": "state",
                "entity_id": "binary_sensor.window",
                "state": "off",
            }
        ],
        "actions": [
            {
                "action": "persistent_notification.create",
                "data": {"title": "Schedule", "message": "Keep this action"},
            },
            {
                "action": "ble_esl.write",
                "target": {"device_id": "demo-device-0"},
                "data": {
                    "background": "white",
                    "payload": [
                        {
                            "type": "text_fit",
                            "x": 8,
                            "y": 8,
                            "width": 220,
                            "height": 28,
                            "value": item["name"],
                            "color": "black",
                        }
                    ],
                },
            },
        ],
    }
    for item in AUTOMATIONS
}
DEFAULT_AUTOMATION_CONFIGS = deepcopy(AUTOMATION_CONFIGS)
for automation in AUTOMATIONS:
    STATES[automation["entity_id"]] = {
        "entity_id": automation["entity_id"],
        "state": automation["state"],
        "attributes": {"friendly_name": automation["name"], "id": automation["id"]},
    }


def demo_automations(entry_id):
    manual = AUTOMATION_LINKS.get(entry_id, [])
    return {
        "linked": [
            {**item, "source": "manual", "missing": False, "link_id": item["id"]}
            for item in AUTOMATIONS
            if item["entity_id"] in manual
        ],
        "available": AUTOMATIONS,
    }


CREATED_AUTOMATIONS = {}
HASS = None


async def setup_hass(app):
    global HASS
    HASS = HomeAssistant(str(ROOT))
    for state in STATES.values():
        HASS.states.async_set(state["entity_id"], state["state"], state["attributes"])


async def api(request):
    """What Home Assistant does with a failed command: the message goes to the panel."""
    try:
        return await handle(request)
    except HomeAssistantError as err:
        return web.Response(status=400, text=str(err))


async def handle(request):
    msg = await request.json()
    if msg["action"] == "specs":
        return web.json_response(describe())
    if msg["action"] == "templates":
        return web.json_response(TEMPLATES)
    if msg["action"] == "save_template":
        template = TEMPLATES[msg["key"]] = validate_template(msg["template"])
        return web.json_response(template)
    if msg["action"] == "preview_template":
        template = validate_template(msg["template"])
        preset = DevicePreset("template", "Template", template["width"], template["height"], "BWRY")
        state = HASS.states.get(msg["entity_id"])
        document = substitute(template["document"], sensor_values(state, {}), state.state, state)
        return await preview(document, preset)
    if msg["action"] == "list":
        return web.json_response(TAGS)
    if msg["action"] in ("automations", "link_automation", "unlink_automation"):
        links = AUTOMATION_LINKS.setdefault(msg["entry_id"], [])
        if msg["action"] == "link_automation" and msg["entity_id"] not in links:
            links.append(msg["entity_id"])
        elif msg["action"] == "unlink_automation" and msg["entity_id"] in links:
            links.remove(msg["entity_id"])
        return web.json_response(demo_automations(msg["entry_id"]))
    if msg["action"] == "automation_edit_source":
        tag = next(tag for tag in TAGS if tag["entry_id"] == msg["entry_id"])
        automation = next(item for item in AUTOMATIONS if item["entity_id"] == msg["entity_id"])
        return web.json_response(
            {
                "entity_id": msg["entity_id"],
                "config_id": automation["id"],
                "device_id": tag["device_id"],
                "entity_ids": list(tag["entities"].values()),
            }
        )
    tag = next(tag for tag in TAGS if tag["entry_id"] == msg["entry_id"])
    preset = DevicePreset("demo", tag["title"], tag["width"], tag["height"], tag["colors"])
    if msg["action"] == "design_templates":
        return web.json_response(
            [
                describe_template(template, preset.width, preset.height)
                for template in DESIGN_TEMPLATES.values()
            ]
        )
    template_info = None
    if msg["action"] == "apply_design_template":
        template = DESIGN_TEMPLATES.get(msg["template_id"])
        if template is None:
            return web.Response(status=400, text="There is no such design template")
        try:
            built = build_template(
                template, preset.width, preset.height, preset.colors, msg.get("parameters")
            )
        except HomeAssistantError as err:
            return web.Response(status=400, text=str(err))
        fonts = {
            value
            for name, value in built["parameters"].items()
            if template["parameters"][name]["type"] == "font"
        }
        if missing := [
            font
            for font in fonts
            if not (ROOT / "custom_components/ble_esl/fonts" / font).is_file()
        ]:
            return web.Response(status=400, text=f"Font not found: {', '.join(missing)}")
        template_info = {
            "id": template["id"],
            "layout": built["layout"],
            "scaled": built["scaled"],
            "parameters": built["parameters"],
            "automation": built["automation"],
        }
        msg = {**msg, "action": "import_payload", "payload": built["payload"]}
        msg["background"] = built["background"]
    if msg["action"] in ("import_yaml", "import_payload"):
        if msg["action"] == "import_payload":
            items, background = msg["payload"], msg.get("background")
        else:
            try:
                items, background = parse_payload(msg["text"])
            except HomeAssistantError as err:
                # Home Assistant carries the message to the panel; so does the demo.
                return web.Response(status=400, text=str(err))
        elements, imported, issues = elements_from(
            items, preset, max(0, 100 - msg.get("existing", 0))
        )
        different = None
        if elements:
            try:
                original, rebuilt = payloads(
                    HASS, imported, elements, _preview_variable_map(msg.get("preview_variables"))
                )
            except MissingTemplateParameter as err:
                return web.json_response(
                    {
                        "missing_parameters": [err.name],
                        "elements": [],
                        "issues": [],
                        "different_pixels": None,
                        "background": background,
                    }
                )
            different = await asyncio.to_thread(different_pixels, HASS, preset, original, rebuilt)
        return web.json_response(
            {
                "elements": elements,
                "issues": issues,
                "different_pixels": different,
                "background": background,
                **({"template": template_info} if template_info else {}),
            }
        )
    document = validate(msg["document"], preset)
    if msg["action"] == "convert":
        element = next((el for el in document["elements"] if el["id"] == msg["element_id"]), None)
        if element is None or element["type"] == "imagespec":
            return web.Response(status=400, text="That element cannot be converted")
        snapshots = snapshot_layers(
            HASS, {"elements": [element]}, TEMPLATES, await demo_forecasts()
        )
        state = HASS.states.get(element["entity_id"]) if element["entity_id"] else None
        elements, issues, original, rebuilt = convert(HASS, element, state, snapshots[0][1], preset)
        different = None
        if elements:
            different = await asyncio.to_thread(different_pixels, HASS, preset, original, rebuilt)
        return web.json_response(
            {"elements": elements, "issues": issues, "different_pixels": different}
        )
    if msg["action"] == "save_design_template":
        name = (msg.get("name") or "").strip()
        if not name or len(name) > 80:
            return web.Response(status=400, text="Give the template a name of up to 80 characters")
        base, number = slug(name), 2
        taken = set(DESIGN_TEMPLATES)
        unique = base
        while unique in taken:
            unique, number = f"{base}_{number}", number + 1
        forecasts = await demo_forecasts()
        payload = live_payload(HASS, document, TEMPLATES, forecasts)
        if payload is None:
            payload = compile_payload(HASS, document, TEMPLATES, forecasts)
        try:
            text = template_text(
                unique, name, preset.width, preset.height, document["background"], plain(payload)
            )
        except HomeAssistantError as err:
            return web.Response(status=400, text=str(err))
        DESIGN_TEMPLATES[unique] = {**parse_template(text), "source": "user"}
        return web.json_response({"id": unique, "yaml": text})
    if msg["action"] == "save":
        tag["document"] = document
        return web.json_response(document)
    if msg["action"] == "send":
        return web.json_response({"status": "demo_only"})
    if msg["action"] in ("export", "automation"):
        forecasts = await demo_forecasts()
        variables = _preview_variable_map(msg.get("preview_variables"))
        payload = compile_payload(HASS, document, TEMPLATES, forecasts, preview_variables=variables)
        dynamic_geometry = [
            element
            for element in document["elements"]
            if element["type"] == "imagespec" and frozen_corners(element.get("spec", {}))
        ]
        automation_edit = msg.get("automation_edit", False)
        issues = []
        if automation_edit and dynamic_geometry:
            issues.extend(
                f"blocking: {element['id']}: templated polygon corners cannot be safely saved"
                for element in dynamic_geometry
            )
            live = None
        else:
            live = live_payload(HASS, document, TEMPLATES, forecasts)
        result = export_yaml(
            payload,
            document["background"],
            tag["device_id"] if msg["action"] == "automation" else None,
            issues,
            live,
        )
        if msg["action"] == "automation":
            if not tag["writable"]:
                raise HomeAssistantError("This ESL does not support writing")
            result["automation"] = automation_draft(
                result, tag["title"], msg.get("automation_defaults")
            )
        return web.json_response(
            {
                **result,
                "payload_data": None
                if result["validation_errors"]
                else (live if live is not None else payload),
                "writable": tag["writable"],
            }
        )
    return await preview(document, preset, msg.get("preview_variables"))


async def demo_forecasts():
    return {
        ("weather.home", kind): [
            {
                "datetime": (dt_util.now() + timedelta(days=day)).isoformat(),
                "condition": "sunny",
                "temperature": 22.5,
                "templow": 15,
                "precipitation_probability": 20,
            }
            for day in range(4)
        ]
        for kind in ("daily", "hourly")
    }


async def preview(document, preset, preview_variables=None):
    forecasts = await demo_forecasts()
    variables = _preview_variable_map(preview_variables)
    snapshots = snapshot_layers(HASS, document, TEMPLATES, forecasts, variables)
    payload = [item for _, part in snapshots for item in part]
    image, layers = await asyncio.to_thread(
        render_document, HASS, preset, document, payload, snapshots
    )
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return web.json_response(
        {
            "png": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(),
            "payload": payload,
            "layers": layers,
        }
    )


async def reset(request):
    CREATED_AUTOMATIONS.clear()
    """Fresh saved state, so each browser project starts alike."""
    AUTOMATION_CONFIGS.clear()
    AUTOMATION_CONFIGS.update(deepcopy(DEFAULT_AUTOMATION_CONFIGS))
    TEMPLATES.clear()
    AUTOMATION_LINKS.clear()
    AUTOMATION_LINKS["demo-writable"] = [
        "automation.morning",
        "automation.temperature",
        "automation.night",
    ]
    for tag in TAGS:
        tag["document"] = None
    return web.json_response({})


async def index(request):
    return web.FileResponse(ROOT / "tests/frontend/demo.html")


async def states(request):
    return web.json_response(STATES)


app = web.Application()
app.on_startup.append(setup_hass)
app.router.add_get("/", index)


async def demo_image(request):
    preset = DevicePreset("demo", "demo", 250, 122, "BWR")
    payload = [
        {
            "type": "text_fit",
            "x": 12,
            "y": 12,
            "width": 226,
            "height": 32,
            "value": "Living room",
            "color": "red",
        },
        {"type": "text_fit", "x": 12, "y": 52, "width": 226, "height": 54, "value": "21.3 °C"},
    ]
    image, _ = await asyncio.to_thread(
        render_document, HASS, preset, {"background": "white", "elements": []}, payload, []
    )
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return web.Response(body=buffer.getvalue(), content_type="image/png")


async def create_automation(request):
    config = await request.json()
    CREATED_AUTOMATIONS[request.match_info["automation_id"]] = config
    AUTOMATION_CONFIGS[request.match_info["automation_id"]] = config
    return web.json_response({"result": "ok"})


async def get_automation(request):
    config = AUTOMATION_CONFIGS.get(request.match_info["automation_id"])
    if config is None:
        raise web.HTTPNotFound()
    return web.json_response(config)


async def automation_preview(request):
    config = CREATED_AUTOMATIONS.get(request.match_info["automation_id"])
    if config is None:
        raise web.HTTPNotFound()
    return web.Response(
        text='<meta charset="utf-8"><title>Automation preview</title>'
        "<h1>자동화 생성 데모</h1><p>Home Assistant에는 저장되지 않습니다.</p>"
        '<a href="/?manager&lang=ko">ESL 매니저</a><pre>'
        + escape(json.dumps(config, ensure_ascii=False, indent=2))
        + "</pre>",
        content_type="text/html",
    )


app.router.add_post("/api/config/automation/config/{automation_id}", create_automation)
app.router.add_get("/api/config/automation/config/{automation_id}", get_automation)
app.router.add_get("/config/automation/edit/{automation_id}", automation_preview)
app.router.add_get("/demo-image", demo_image)
app.router.add_get("/states", states)
app.router.add_post("/api/designer", api)
app.router.add_post("/reset", reset)
app.router.add_static("/ble_esl_designer_fonts", ROOT / "custom_components/ble_esl/fonts")
app.router.add_static("/frontend", ROOT / "custom_components/ble_esl/designer/frontend")
if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8765)
