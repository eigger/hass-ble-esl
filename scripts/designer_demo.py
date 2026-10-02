"""Local visual QA using the real renderer; no Bluetooth access or writes.

Run from the repository root: .venv/bin/python scripts/designer_demo.py
"""

import asyncio
import base64
from datetime import timedelta
from io import BytesIO
from pathlib import Path
import sys

from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.ble_esl.designer.export import export_yaml
from custom_components.ble_esl.designer.layout import (
    compile_payload,
    live_payload,
    sensor_values,
    substitute,
    validate,
    validate_template,
)
from custom_components.ble_esl.designer.rendering import render_document, snapshot_layers
from custom_components.ble_esl.designer.specs import describe
from custom_components.ble_esl.esl_ble.base import DevicePreset

ROOT = Path(__file__).resolve().parents[1]
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
HASS = None


async def setup_hass(app):
    global HASS
    HASS = HomeAssistant(str(ROOT))
    for state in STATES.values():
        HASS.states.async_set(state["entity_id"], state["state"], state["attributes"])


async def api(request):
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
    tag = next(tag for tag in TAGS if tag["entry_id"] == msg["entry_id"])
    preset = DevicePreset("demo", tag["title"], tag["width"], tag["height"], tag["colors"])
    document = validate(msg["document"], preset)
    if msg["action"] == "save":
        tag["document"] = document
        return web.json_response(document)
    if msg["action"] == "send":
        return web.json_response({"status": "demo_only"})
    if msg["action"] == "export":
        forecasts = await demo_forecasts()
        payload = compile_payload(HASS, document, TEMPLATES, forecasts)
        live = live_payload(HASS, document, TEMPLATES, forecasts)
        result = export_yaml(payload, document["background"], None, (), live)
        return web.json_response({**result, "writable": tag["writable"]})
    return await preview(document, preset)


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


async def preview(document, preset):
    forecasts = await demo_forecasts()
    snapshots = snapshot_layers(HASS, document, TEMPLATES, forecasts)
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
    """Fresh saved state, so each browser project starts alike."""
    TEMPLATES.clear()
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
app.router.add_get("/states", states)
app.router.add_post("/api/designer", api)
app.router.add_post("/reset", reset)
app.router.add_static("/ble_esl_designer_fonts", ROOT / "custom_components/ble_esl/fonts")
app.router.add_static("/frontend", ROOT / "custom_components/ble_esl/designer/frontend")
if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8765)
