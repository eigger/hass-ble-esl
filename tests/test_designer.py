"""Editor persistence, rendering, sensor updates and lifecycle in real HA."""

import base64
from functools import partial
from io import BytesIO
from unittest.mock import patch

from homeassistant.components.automation.config import async_validate_config_item
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from PIL import Image
import pytest
import voluptuous as vol
import yaml

from custom_components.ble_esl.designer import KEY
from custom_components.ble_esl.designer.export import automation_draft, export_yaml
from custom_components.ble_esl.designer.layout import compile_payload, validate, validate_template
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.renderer import render_image


def document():
    return {
        "version": 1,
        "elements": [
            {
                "id": "temperature",
                "type": "sensor",
                "entity_id": "sensor.room_temperature",
                "x": 8,
                "y": 8,
                "width": 180,
                "height": 70,
                "font_size": 32,
                "decimals": 1,
            }
        ],
    }


def test_validation_rejects_unsupported_palette():
    preset = DevicePreset("test", "test", 250, 122, "BWR")
    doc = document()
    doc["background"] = "yellow"
    with pytest.raises(vol.Invalid, match="Background"):
        validate(doc, preset)


async def test_sensor_value_and_unavailable(hass: HomeAssistant):
    doc = validate(document(), DevicePreset("test", "test", 250, 122, "BWR"))
    hass.states.async_set(
        "sensor.room_temperature", "21.26", {"friendly_name": "Office", "unit_of_measurement": "°C"}
    )
    payload = compile_payload(hass, doc)
    assert payload[1]["value"] == "Office"
    assert payload[2]["value"] == "21.3 °C"
    hass.states.async_set("sensor.room_temperature", "unavailable", {"unit_of_measurement": "°C"})
    assert compile_payload(hass, doc)[2]["value"] == "Unavailable"


async def test_panel_preview_save_and_restore(hass: HomeAssistant, wolink_entry):
    assert "ble-esl-designer" in hass.data[DATA_PANELS]
    designer = hass.data[KEY]
    entry = wolink_entry
    hass.states.async_set(
        "sensor.room_temperature", "21.26", {"friendly_name": "Office", "unit_of_measurement": "°C"}
    )
    saved = await designer.save(entry, document())
    assert "auto_update" not in saved
    assert "interval" not in saved
    result = await designer.preview(entry, saved)
    with Image.open(BytesIO(base64.b64decode(result["png"].split(",")[1]))) as image:
        assert image.size == (296, 128)
        assert image.getextrema() != ((255, 255), (255, 255), (255, 255))
    assert result["payload"][2]["value"] == "21.3 °C"
    assert (await designer.store.async_load())[entry.entry_id] == saved
    await hass.config_entries.async_reload(entry.entry_id)
    assert designer.documents[entry.entry_id] == saved


async def test_manual_send_rewrites_and_respects_lock(
    hass: HomeAssistant, wolink_entry, tag_writer
):
    designer = hass.data[KEY]
    entry = wolink_entry
    assert (await designer.send(entry, document()))["status"] == "written"
    assert tag_writer.write_prepared.await_count == 1
    # An explicit Send rewrites the same image, e.g. after the tag was reset.
    assert (await designer.send(entry, document()))["status"] == "written"
    assert tag_writer.write_prepared.await_count == 2
    entry.runtime_data.write_lock = True
    doc = document()
    doc["elements"][0]["label"] = "Changed label"
    assert (await designer.send(entry, doc))["status"] == "locked"
    assert tag_writer.write_prepared.await_count == 2


async def test_legacy_save_never_sends_on_sensor_changes(hass, wolink_entry, tag_writer):
    designer = hass.data[KEY]
    saved = await designer.save(wolink_entry, {**document(), "auto_update": True, "interval": 10})
    assert "auto_update" not in saved
    assert "interval" not in saved
    hass.states.async_set("sensor.room_temperature", "25")
    await hass.async_block_till_done()
    assert tag_writer.write_prepared.await_count == 0
    assert (await designer.store.async_load())[wolink_entry.entry_id] == saved


async def test_websocket_list_preview_validation_and_admin(
    hass: HomeAssistant, wolink_entry, hass_ws_client
):
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "ble_esl/designer", "action": "list"})
    result = await client.receive_json()
    assert result["success"]
    assert result["result"][0]["entry_id"] == wolink_entry.entry_id
    await client.send_json(
        {
            "id": 2,
            "type": "ble_esl/designer",
            "action": "preview",
            "entry_id": wolink_entry.entry_id,
            "document": document(),
        }
    )
    result = await client.receive_json()
    assert result["success"]
    assert result["result"]["png"].startswith("data:image/png;base64,")
    await client.send_json(
        {
            "id": 3,
            "type": "ble_esl/designer",
            "action": "save",
            "entry_id": wolink_entry.entry_id,
            "document": {"version": 99, "elements": []},
        }
    )
    assert (await client.receive_json())["success"] is False


async def test_temperature_compatibility_unit(hass: HomeAssistant):
    """A reported superscript-zero temperature unit must not become a missing glyph."""
    doc = validate(document(), DevicePreset("test", "test", 250, 122, "BWR"))
    hass.states.async_set("sensor.room_temperature", "21.26", {"unit_of_measurement": "⁰C"})
    assert compile_payload(hass, doc)[2]["value"] == "21.3 °C"


async def test_template_persistence_state_icons_and_scaled_rendering(hass, wolink_entry):
    from custom_components.ble_esl.designer.layout import validate_template

    designer = hass.data[KEY]
    template = {
        "width": 100,
        "height": 50,
        "document": {
            "version": 1,
            "elements": [
                {
                    "id": "on",
                    "type": "icon",
                    "icon": "mdi:window-open",
                    "state": "on",
                    "x": 0,
                    "y": 0,
                    "width": 30,
                    "height": 30,
                },
                {
                    "id": "off",
                    "type": "icon",
                    "icon": "mdi:window-closed",
                    "state": "off",
                    "x": 0,
                    "y": 0,
                    "width": 30,
                    "height": 30,
                },
                {
                    "id": "name",
                    "type": "text",
                    "text": "{{name}}",
                    "x": 35,
                    "y": 0,
                    "width": 65,
                    "height": 20,
                },
            ],
        },
    }
    await designer.save_template("binary_sensor:window", template)
    assert (await designer.template_store.async_load())[
        "binary_sensor:window"
    ] == validate_template(template)
    doc = document()
    doc["elements"][0].update(entity_id="binary_sensor.window", width=200, height=100)
    del doc["elements"][0]["decimals"]
    doc = validate(doc, DevicePreset("test", "test", 250, 122, "BWR"))
    hass.states.async_set(
        "binary_sensor.window", "off", {"device_class": "window", "friendly_name": "Window"}
    )
    payload = compile_payload(hass, doc, designer.templates)
    assert payload[0]["value"] == "mdi:window-closed"
    assert payload[0]["size"] == 60
    assert payload[1]["x"] == 78
    assert payload[1]["value"] == "Window"
    hass.states.async_set(
        "binary_sensor.window", "on", {"device_class": "window", "friendly_name": "Window"}
    )
    assert compile_payload(hass, doc, designer.templates)[0]["value"] == "mdi:window-open"
    preview = await designer.preview_template(template, "binary_sensor.window")
    with Image.open(BytesIO(base64.b64decode(preview["png"].split(",")[1]))) as image:
        assert image.size == (100, 50)


async def test_weather_forecast_and_visual_condition(hass):
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    hass.states.async_set(
        "weather.home",
        "cloudy",
        {"friendly_name": "Weather", "temperature": 18, "temperature_unit": "°C"},
    )
    doc = document()
    doc["elements"][0].update(
        entity_id="weather.home", weather_when="tomorrow", weather_field="condition"
    )
    del doc["elements"][0]["decimals"]
    doc = validate(doc, DevicePreset("test", "test", 250, 122, "BWR"))
    forecasts = {
        ("weather.home", "daily"): [
            {
                "datetime": (dt_util.now() + timedelta(days=1)).isoformat(),
                "condition": "sunny",
                "temperature": 23.5,
            }
        ]
    }
    payload = compile_payload(hass, doc, forecasts=forecasts)
    assert payload[0]["value"] == "mdi:weather-sunny"
    assert all(item.get("value") not in ("cloudy", "sunny") for item in payload)
    doc["elements"][0]["weather_field"] = "temperature"
    payload = compile_payload(hass, doc, forecasts=forecasts)
    assert payload[0]["value"] == "mdi:thermometer"
    assert payload[2]["value"] == "23.5 °C"


async def test_default_entity_icon_and_binary_state(hass):
    from custom_components.ble_esl.designer.layout import sensor_icon

    hass.states.async_set("binary_sensor.window", "off", {"device_class": "window"})
    assert sensor_icon(hass.states.get("binary_sensor.window")) == "mdi:window-closed"
    hass.states.async_set("binary_sensor.window", "on", {"device_class": "window"})
    assert sensor_icon(hass.states.get("binary_sensor.window")) == "mdi:window-open"
    hass.states.async_set(
        "sensor.temperature", "21", {"device_class": "temperature", "icon": "mdi:home-thermometer"}
    )
    assert sensor_icon(hass.states.get("sensor.temperature")) == "mdi:home-thermometer"


async def test_weather_forecasts_use_ha_service_and_cache(hass, wolink_entry):
    from homeassistant.core import SupportsResponse

    designer = hass.data[KEY]
    doc = validate(document(), wolink_entry.runtime_data.preset)
    doc["elements"][0].update(entity_id="weather.home", weather_when="tomorrow")
    forecast = [{"datetime": "2026-10-02T12:00:00+00:00", "condition": "cloudy"}]
    calls = []

    async def get_forecasts(call):
        calls.append(dict(call.data))
        return {"weather.home": {"forecast": forecast}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    assert await designer.forecasts(doc) == {("weather.home", "daily"): forecast}
    assert await designer.forecasts(doc) == {("weather.home", "daily"): forecast}
    assert calls == [{"entity_id": "weather.home", "type": "daily"}]


def test_elements_can_extend_outside_display():
    doc = document()
    doc["elements"][0].update(x=-20, y=-10, width=300, height=160)
    result = validate(doc, DevicePreset("test", "test", 250, 122, "BWR"))
    assert result["elements"][0]["x"] == -20
    assert result["elements"][0]["width"] == 300


async def test_sensor_background_can_be_transparent(hass):
    doc = document()
    doc["elements"][0]["background"] = "transparent"
    validated = validate(doc, DevicePreset("test", "test", 250, 122, "BWR"))
    hass.states.async_set("sensor.room_temperature", "21.2", {"unit_of_measurement": "°C"})
    assert "background" not in compile_payload(hass, validated)[2]


async def test_explicit_text_line_breaks_are_preserved(hass, wolink_entry):
    doc = {
        "version": 1,
        "elements": [
            {
                "id": "text",
                "type": "text",
                "text": "A\nB",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 80,
                "font_size": 18,
            }
        ],
    }
    result = await hass.data[KEY].preview(wolink_entry, doc)
    with Image.open(BytesIO(base64.b64decode(result["png"].split(",")[1]))) as image:
        assert image.crop((0, 0, 100, 40)).getextrema() != ((255, 255), (255, 255), (255, 255))
        assert image.crop((0, 40, 100, 80)).getextrema() != ((255, 255), (255, 255), (255, 255))


def decode_png(value):
    return Image.open(BytesIO(base64.b64decode(value.split(",")[1])))


async def test_preview_is_one_render_of_the_exported_payload(hass, wolink_entry):
    doc = {
        "version": 1,
        "background": "yellow",
        "elements": [
            {
                "id": "base",
                "type": "rectangle",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 80,
                "color": "red",
            },
            {
                "id": "overlay",
                "type": "text",
                "text": "A",
                "x": -4,
                "y": 3,
                "width": 100,
                "height": 60,
                "font_size": 18,
            },
        ],
    }
    manager = hass.data[KEY]
    result = await manager.preview(wolink_entry, doc)
    preset = manager.preset(wolink_entry)
    expected = await hass.async_add_executor_job(
        partial(render_image, hass, preset, result["payload"], background="yellow")
    )
    with decode_png(result["png"]) as actual:
        assert actual.tobytes() == expected.tobytes()
        assert actual.getpixel((90, 70)) == (255, 0, 0)
    # The layers are the display's elements: stacked where they sit, they make it.
    stacked = Image.new("RGB", actual.size, "yellow")
    for element in doc["elements"]:
        left, top = result["layers"]["_offsets"].get(element["id"], (0, 0))
        with decode_png(result["layers"][element["id"]]) as layer:
            stacked.paste(layer, (element["x"] + left, element["y"] + top), layer)
    assert stacked.tobytes() == actual.tobytes()


async def test_send_writes_the_pixels_of_the_exported_payload(hass, wolink_entry, tag_writer):
    hass.states.async_set("sensor.room_temperature", "21.26", {"unit_of_measurement": "°C"})
    manager = hass.data[KEY]
    exported = await manager.export(wolink_entry, document())
    await manager.send(wolink_entry, document())
    expected = await hass.async_add_executor_job(
        partial(
            render_image,
            hass,
            manager.preset(wolink_entry),
            yaml.safe_load(exported["payload"]),
            background="white",
        )
    )
    assert tag_writer.sent_image().tobytes() == expected.tobytes()


async def test_export_yaml_is_a_ready_to_use_write_action(hass, wolink_entry):
    hass.states.async_set("sensor.room_temperature", "21.26", {"unit_of_measurement": "°C"})
    manager = hass.data[KEY]
    payload = (await manager.draw(wolink_entry, document()))[2]
    result = await manager.export(wolink_entry, document())
    assert yaml.safe_load(result["payload"]) == payload
    assert result["issues"] == []
    service = yaml.safe_load(result["service"])
    assert service["action"] == "ble_esl.write"
    assert service["data"] == {"background": "white", "payload": payload}
    assert service["target"] == {"device_id": wolink_entry.runtime_data.device_id}
    assert result["writable"] is True
    assert "&id" not in result["service"]


async def test_export_flags_what_an_automation_or_the_renderer_would_trip_on(hass, wolink_entry):
    doc = {
        "version": 1,
        "elements": [
            {"id": "icon", "type": "icon", "x": 0, "y": 0, "width": 32, "height": 32},
            {
                "id": "text",
                "type": "text",
                "text": "{{ states('sensor.x') }}",
                "x": 40,
                "y": 0,
                "width": 100,
                "height": 30,
            },
        ],
    }
    result = await hass.data[KEY].export(wolink_entry, doc)
    assert any(issue.startswith("render:") and "icon" in issue for issue in result["issues"])
    assert any("payload[1].value: contains template syntax" in i for i in result["issues"])


async def test_websocket_export(hass, wolink_entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "ble_esl/designer",
            "action": "export",
            "entry_id": wolink_entry.entry_id,
            "document": document(),
        }
    )
    result = await client.receive_json()
    assert result["success"]
    assert set(result["result"]) == {"payload", "service", "issues", "writable"}


def test_export_reports_what_imagespec_rejects():
    result = export_yaml([{"type": "text", "x": 1}], "white", None)
    assert result["issues"] == ["[0].value: missing required key for 'text'"]
    assert yaml.safe_load(result["service"])["target"] == {"device_id": "<your device>"}


async def test_font_awesome_icons_render(hass):
    render = partial(
        render_image,
        hass,
        DevicePreset("test", "test", 40, 40, "BW"),
        [{"type": "icon", "x": 4, "y": 4, "value": "fa:house", "size": 32}],
    )
    image = await hass.async_add_executor_job(render)
    assert image.getextrema() != ((255, 255), (255, 255), (255, 255))


async def test_numeric_template_applies_across_sensor_device_classes(hass):
    hass.states.async_set("sensor.room_temperature", "21.2", {"device_class": "temperature"})
    doc = validate(document(), DevicePreset("test", "test", 250, 122, "BWR"))
    template = validate_template(
        {
            "width": 100,
            "height": 60,
            "sensor_type": "output:numeric",
            "document": {
                "version": 1,
                "elements": [
                    {
                        "id": "value",
                        "type": "text",
                        "text": "Shared {{state}}",
                        "x": 0,
                        "y": 0,
                        "width": 100,
                        "height": 60,
                    }
                ],
            },
        }
    )
    payload = compile_payload(hass, doc, {"output:numeric": template})
    assert any(item.get("value") == "Shared 21.2" for item in payload)


async def test_image_elements_and_state_images_render(hass, wolink_entry):
    from custom_components.ble_esl.designer.rendering import png_url

    source = png_url(Image.new("RGB", (4, 4), "red"))
    doc = {
        "version": 1,
        "elements": [
            {
                "id": "picture",
                "type": "image",
                "image": source,
                "x": 4,
                "y": 5,
                "width": 20,
                "height": 20,
            }
        ],
    }
    result = await hass.data[KEY].preview(wolink_entry, doc)
    with Image.open(BytesIO(base64.b64decode(result["png"].split(",")[1]))) as image:
        assert image.getpixel((10, 10)) == (255, 0, 0)
    hass.states.async_set("binary_sensor.laundry", "on")
    template = validate_template(
        {
            "width": 30,
            "height": 30,
            "document": {
                "version": 1,
                "elements": [
                    dict(doc["elements"][0], state="on"),
                    dict(doc["elements"][0], id="off", state="off"),
                ],
            },
        }
    )
    sensor = validate(
        {
            "version": 1,
            "elements": [
                {
                    "id": "laundry",
                    "type": "sensor",
                    "entity_id": "binary_sensor.laundry",
                    "template": "output:binary",
                    "x": 0,
                    "y": 0,
                    "width": 30,
                    "height": 30,
                }
            ],
        },
        DevicePreset("test", "test", 250, 122, "BWR"),
    )
    assert len(compile_payload(hass, sensor, {"output:binary": template})) == 1


async def test_state_icon_mapping_selects_the_current_sensor_state(hass):
    from custom_components.ble_esl.designer.layout import substitute

    template = validate_template(
        {
            "width": 50,
            "height": 50,
            "document": {
                "version": 1,
                "elements": [
                    {
                        "id": "icon",
                        "type": "icon",
                        "x": 0,
                        "y": 0,
                        "width": 32,
                        "height": 32,
                        "icon": "{{icon}}",
                        "state_icons": {
                            "on": "mdi:washing-machine",
                            "off": "mdi:washing-machine-off",
                        },
                    }
                ],
            },
        }
    )
    for state, expected in [
        ("on", "mdi:washing-machine"),
        ("off", "mdi:washing-machine-off"),
        ("unavailable", "mdi:help"),
    ]:
        resolved = substitute(template["document"], {"icon": "mdi:help"}, state)
        assert compile_payload(hass, resolved)[0]["value"] == expected


async def test_independent_component_bindings_and_attributes(hass):
    from custom_components.ble_esl.designer.layout import bindings

    hass.states.async_set(
        "sensor.temperature",
        "21.5",
        {"unit_of_measurement": "°C", "friendly_name": "Room", "battery": 42},
    )
    hass.states.async_set("binary_sensor.laundry", "on")
    doc = validate(
        {
            "version": 1,
            "elements": [
                {
                    "id": "text",
                    "type": "text",
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 30,
                    "entity_id": "sensor.temperature",
                    "data_field": "state",
                    "decimals": 1,
                },
                {
                    "id": "name",
                    "type": "text",
                    "x": 0,
                    "y": 30,
                    "width": 100,
                    "height": 30,
                    "entity_id": "sensor.temperature",
                    "data_field": "name",
                },
                {
                    "id": "progress",
                    "type": "progress_bar",
                    "x": 0,
                    "y": 60,
                    "width": 100,
                    "height": 15,
                    "entity_id": "sensor.temperature",
                    "data_field": "attribute",
                    "attribute": "battery",
                },
                {
                    "id": "icon",
                    "type": "conditional_icon",
                    "x": 100,
                    "y": 0,
                    "width": 32,
                    "height": 32,
                    "entity_id": "binary_sensor.laundry",
                    "data_field": "state",
                    "icon_rules": [{"kind": "state", "state": "on", "icon": "mdi:washing-machine"}],
                },
            ],
        },
        DevicePreset("test", "Test", 250, 122, "BWR"),
    )
    payload = compile_payload(hass, doc)
    assert [item.get("value") for item in payload] == ["21.5", "Room", None, "mdi:washing-machine"]
    assert payload[2]["progress"] == 42
    assert bindings(doc) == {"sensor.temperature", "binary_sensor.laundry"}


def test_numeric_icon_ranges_boundaries_priority_and_fallback():
    from custom_components.ble_esl.designer.layout import conditional_icon

    component = {
        "icon_rules": [
            {"kind": "range", "min": 0, "max": 20, "icon": "mdi:snowflake"},
            {"kind": "range", "min": 20, "icon": "mdi:fire"},
            {"kind": "state", "state": "unavailable", "icon": "mdi:alert"},
        ]
    }
    for value, icon in [
        ("0", "mdi:snowflake"),
        ("19.99", "mdi:snowflake"),
        ("20", "mdi:fire"),
        ("100", "mdi:fire"),
        ("-1", "mdi:help"),
        ("unknown", "mdi:help"),
        ("unavailable", "mdi:alert"),
    ]:
        assert conditional_icon(component, value, "mdi:help") == icon
    component["icon_rules"].insert(0, {"kind": "range", "min": 10, "icon": "mdi:star"})
    assert conditional_icon(component, "20", "mdi:help") == "mdi:star"


async def test_sample_components_render_in_templates(hass):
    from custom_components.ble_esl.designer.layout import sensor_values, substitute

    hass.states.async_set("sensor.sample", "37", {"unit_of_measurement": "%"})
    state = hass.states.get("sensor.sample")
    template = validate_template(
        {
            "width": 100,
            "height": 40,
            "document": {
                "version": 1,
                "elements": [
                    {
                        "id": "value",
                        "type": "text",
                        "x": 0,
                        "y": 0,
                        "width": 100,
                        "height": 40,
                        "data_field": "state",
                    }
                ],
            },
        }
    )
    expanded = substitute(template["document"], sensor_values(state, {}), state.state, state)
    assert compile_payload(hass, expanded)[0]["value"] == "37"


async def test_content_bounds_follow_visible_sensor_content(hass, wolink_entry):
    hass.states.async_set("sensor.room_temperature", "21", {"unit_of_measurement": "°C"})
    doc = document()
    doc["elements"][0].update(show_label=False, width=240, height=100)
    result = await hass.data[KEY].preview(wolink_entry, doc)
    x0, y0, x1, y1 = result["layers"]["_bounds"]["temperature"]
    assert x1 - x0 < 240
    assert y1 - y0 < 100


async def test_general_field_templates_control_color_icon_background_and_size(hass, wolink_entry):
    hass.states.async_set("sensor.power", "42", {"unit_of_measurement": "W"})
    doc = {
        "version": 1,
        "elements": [
            {
                "id": "icon",
                "type": "conditional_icon",
                "x": 0,
                "y": 0,
                "width": 32,
                "height": 32,
                "entity_id": "sensor.power",
                "data_field": "state",
                "field_templates": {
                    "color": "{{ 'red' if value | float >= 20 else 'black' }}",
                    "icon": "{{ 'mdi:fire' if value | float >= 20 else 'mdi:snowflake' }}",
                    "background": "{{ 'white' if value | float >= 40 else 'transparent' }}",
                    "width": "{{ 40 if value | float >= 20 else 32 }}",
                },
            }
        ],
    }
    result = await hass.data[KEY].preview(wolink_entry, doc)
    assert result["payload"][0]["value"] == "mdi:fire"
    assert result["payload"][0]["color"] == "red"
    assert result["layers"]["_values"]["icon"] == {
        "color": "red",
        "icon": "mdi:fire",
        "background": "white",
        "width": 40,
    }
    # The layer is what the icon draws, as the display shows it.
    left, top, right, bottom = result["layers"]["_bounds"]["icon"]
    with Image.open(BytesIO(base64.b64decode(result["layers"]["icon"].split(",")[1]))) as image:
        assert image.size == (right - left, bottom - top)


async def test_dynamic_text_is_not_overwritten_by_a_second_binding_resolution(hass, wolink_entry):
    hass.states.async_set("sensor.power", "42")
    doc = {
        "version": 1,
        "elements": [
            {
                "id": "text",
                "type": "text",
                "x": 0,
                "y": 0,
                "width": 140,
                "height": 40,
                "entity_id": "sensor.power",
                "data_field": "state",
                "field_templates": {"text": '{{ "Power: " ~ value }}'},
            }
        ],
    }
    result = await hass.data[KEY].preview(wolink_entry, doc)
    assert result["payload"][0]["value"] == "Power: 42"
    assert result["layers"]["_values"]["text"]["text"] == "Power: 42"


async def test_template_references_refresh_preview_without_sending(hass, wolink_entry, tag_writer):
    manager = hass.data[KEY]
    hass.states.async_set("sensor.other", "1")
    doc = document()
    doc["elements"][0]["field_templates"] = {
        "color": "{{ 'red' if states('sensor.other') | int > 0 else 'black' }}"
    }
    saved = await manager.save(wolink_entry, doc)
    assert (await manager.preview(wolink_entry, saved))["payload"][0]["color"] == "red"
    hass.states.async_set("sensor.other", "0")
    assert (await manager.preview(wolink_entry, saved))["payload"][0]["color"] == "black"
    assert tag_writer.write_prepared.await_count == 0


async def test_sensor_component_can_be_configured_in_a_reusable_template(hass, wolink_entry):
    """A sensor dropped into a template must preview/save without the old type ban."""
    hass.states.async_set(
        "binary_sensor.laundry_finished", "on", {"friendly_name": "Laundry finished"}
    )
    template = {
        "width": 140,
        "height": 60,
        "document": {
            "version": 1,
            "elements": [
                {
                    "id": "laundry",
                    "type": "sensor",
                    "entity_id": "binary_sensor.laundry_finished",
                    "x": 0,
                    "y": 0,
                    "width": 140,
                    "height": 60,
                    "template": "auto",
                }
            ],
        },
    }
    designer = hass.data[KEY]
    result = await designer.preview_template(template, "binary_sensor.laundry_finished")
    assert result["layers"]["_bounds"]["laundry"] is not None
    saved = await designer.save_template("custom:laundry", template)
    assert saved["document"]["elements"][0]["type"] == "sensor"
    assert (await designer.template_store.async_load())["custom:laundry"] == saved
    outer = validate(document(), wolink_entry.runtime_data.preset)
    del outer["elements"][0]["decimals"]
    outer["elements"][0].update(
        entity_id="binary_sensor.laundry_finished", template="custom:laundry"
    )
    payload = compile_payload(hass, outer, {"custom:laundry": saved})
    assert any(element["type"] == "icon" for element in payload)


async def test_preview_leaves_the_tag_preview_untouched(hass, wolink_entry):
    hass.states.async_set("sensor.room_temperature", "21.26", {"unit_of_measurement": "°C"})
    data = wolink_entry.runtime_data
    before = data.image_store.images.preview
    await hass.data[KEY].preview(wolink_entry, document())
    assert data.image_store.images.preview is before


async def test_missing_attribute_and_non_numeric_state_render(hass, wolink_entry):
    hass.states.async_set("media_player.tv", "off", {"friendly_name": "TV"})
    hass.states.async_set("sensor.room_temperature", "calibrating", {"unit_of_measurement": "°C"})
    doc = document()
    doc["elements"] += [
        {
            "id": "title",
            "type": "text",
            "entity_id": "media_player.tv",
            "data_field": "attribute",
            "attribute": "media_title",
            "x": 0,
            "y": 80,
            "width": 100,
            "height": 20,
        },
        {
            "id": "bar",
            "type": "progress_bar",
            "entity_id": "media_player.tv",
            "data_field": "state",
            "x": 0,
            "y": 100,
            "width": 100,
            "height": 10,
        },
    ]
    result = await hass.data[KEY].preview(wolink_entry, doc)
    assert result["payload"][2]["value"] == "calibrating °C"
    assert not any(item["type"] == "progress_bar" for item in result["payload"])


async def test_panel_follows_loaded_tags(hass, wolink_entry):
    assert "ble-esl-designer" in hass.data[DATA_PANELS]
    await hass.config_entries.async_unload(wolink_entry.entry_id)
    assert "ble-esl-designer" not in hass.data[DATA_PANELS]
    await hass.config_entries.async_setup(wolink_entry.entry_id)
    assert "ble-esl-designer" in hass.data[DATA_PANELS]


async def test_send_refuses_a_resized_tag_before_publishing(hass, wolink_entry, tag_writer):
    hass.states.async_set("sensor.room_temperature", "21.26", {"unit_of_measurement": "°C"})
    manager = hass.data[KEY]
    data = wolink_entry.runtime_data
    before = data.image_store.images.preview
    small = DevicePreset("small", "Small", 200, 96, "BWR")
    drawn = await manager.draw(wolink_entry, document())
    with (
        patch.object(manager, "draw", return_value=drawn),
        patch.object(manager, "preset", return_value=small),
        pytest.raises(HomeAssistantError, match="display size changed"),
    ):
        await manager.send(wolink_entry, document())
    assert data.image_store.images.preview is before
    assert tag_writer.write_prepared.await_count == 0


def _compiled(hass, *elements):
    base = {"x": 4, "y": 5, "width": 40, "height": 30}
    document = validate(
        {
            "version": 1,
            "elements": [
                {"id": f"e{index}", **base, **element} for index, element in enumerate(elements)
            ],
        },
        DevicePreset("t", "T", 100, 100, "BWR"),
    )
    return compile_payload(hass, document)


async def test_native_element_properties_reach_the_payload(hass):
    payload = _compiled(
        hass,
        {
            "type": "text",
            "text": "hi",
            "valign": "middle",
            "max_lines": 2,
            "padding": 3,
            "font": "a.ttf",
        },
        {"type": "ellipse", "filled": False, "line_width": 3},
        {"type": "rounded_rectangle", "radius": 7},
        {"type": "icon", "icon": "mdi:home", "stroke_width": 2, "stroke_fill": "red"},
        {
            "type": "image",
            "image": "data:image/png;base64,AAAA",
            "rotate": 90,
            "circle": True,
            "dither": "atkinson",
        },
        {
            "type": "progress_bar",
            "value": 50,
            "direction": "up",
            "show_percentage": True,
            "radius": 4,
        },
        {"type": "gauge", "value": 50, "thickness": 5, "show_value": False},
        {"type": "rectangle", "dither": False},
    )
    text, ellipse, rounded, icon, image, bar, gauge, rectangle = payload
    assert text["valign"] == "middle"
    assert text["max_lines"] == 2
    assert text["padding"] == 3
    assert text["font"] == "a.ttf"
    assert "fill" not in ellipse
    assert ellipse["width"] == 3
    assert rounded["radius"] == 7
    assert (icon["stroke_width"], icon["stroke_fill"]) == (2, "red")
    assert (image["rotate"], image["circle"], image["dither"]) == (90, True, "atkinson")
    assert (bar["direction"], bar["show_percentage"], bar["radius"]) == ("up", True, 4)
    assert (gauge["width"], gauge["show_value"]) == (5, False)
    assert rectangle["dither"] is False


async def test_native_element_defaults_are_unchanged(hass):
    text, ellipse, image, gauge = _compiled(
        hass,
        {"type": "text", "text": "hi"},
        {"type": "ellipse"},
        {"type": "image", "image": "data:image/png;base64,AAAA"},
        {"type": "gauge", "value": 5},
    )
    assert {"valign", "padding", "font", "dither"}.isdisjoint(text)
    assert ellipse["fill"] == "black"
    assert "width" not in ellipse
    assert image["dither"] is True
    assert gauge["show_value"] is True
    assert "width" not in gauge


def test_native_element_properties_are_validated():
    preset = DevicePreset("t", "T", 100, 100, "BW")
    element = {"id": "a", "type": "text", "x": 0, "y": 0, "width": 10, "height": 10}
    validate({"version": 1, "elements": [{**element, "valign": "bottom"}]}, preset)
    for bad in ({"valign": "side"}, {"max_lines": 0}, {"stroke_fill": "red"}, {"direction": "x"}):
        with pytest.raises(vol.Invalid):
            validate({"version": 1, "elements": [{**element, **bad}]}, preset)


async def test_dither_values_are_normalised_and_checked(hass):
    blank, zero, named = _compiled(
        hass,
        {"type": "image", "image": "data:image/png;base64,AAAA", "dither": ""},
        {"type": "rectangle", "dither": 0},
        {"type": "rectangle", "dither": "bayer8"},
    )
    off, on = _compiled(
        hass,
        {"type": "rectangle", "dither": "off"},
        {"type": "rectangle", "dither": 1.0},
    )
    assert (off["dither"], on["dither"]) == (False, True)
    assert blank["dither"] is True
    assert zero["dither"] is False
    assert named["dither"] == "bayer8"
    with pytest.raises(vol.Invalid):
        _compiled(hass, {"type": "rectangle", "dither": "bogus"})


async def test_sensor_template_scales_pixel_settings_and_passes_dither(hass):
    hass.states.async_set("sensor.t", "5")
    template = validate_template(
        {
            "width": 100,
            "height": 100,
            "document": {
                "version": 1,
                "elements": [
                    {
                        "id": "n",
                        "type": "rounded_rectangle",
                        "x": 0,
                        "y": 0,
                        "width": 100,
                        "height": 100,
                        "line_width": 10,
                        "radius": 20,
                    }
                ],
            },
        }
    )
    document = validate(
        {
            "version": 1,
            "elements": [
                {
                    "id": "s",
                    "type": "sensor",
                    "entity_id": "sensor.t",
                    "x": 0,
                    "y": 0,
                    "width": 50,
                    "height": 50,
                    "template": "default",
                    "dither": "atkinson",
                }
            ],
        },
        DevicePreset("t", "T", 100, 100, "BW"),
    )
    (item,) = compile_payload(hass, document, {"default": template})
    assert (item["width"], item["radius"]) == (5, 10)
    assert item["dither"] == "atkinson"


async def test_loaded_legacy_designs_are_migrated_durably(hass, wolink_entry, tag_writer):
    from custom_components.ble_esl.designer import Designer, async_setup_designer

    store = Designer(hass).store
    legacy = {**document(), "auto_update": True, "interval": 10}
    await store.async_save({"unloaded_tag": legacy})
    # Registration is unrelated to persisted document migration.
    with (
        patch("custom_components.ble_esl.designer.websocket_api.async_register_command"),
        patch("custom_components.ble_esl.designer.async_get_integration"),
        patch("homeassistant.components.http.HomeAssistantHTTP.async_register_static_paths"),
    ):
        await async_setup_designer(hass)
    migrated = await store.async_load()
    assert "auto_update" not in migrated["unloaded_tag"]
    assert "interval" not in migrated["unloaded_tag"]
    assert migrated["unloaded_tag"]["elements"] == legacy["elements"]
    assert tag_writer.write_prepared.await_count == 0


async def test_automation_draft_uses_current_design_and_registered_device(hass, wolink_entry):
    designer = hass.data[KEY]
    result = await designer.automation(wolink_entry, document())
    config = result["automation"]
    assert config["triggers"] == []
    assert config["conditions"] == []
    assert config["actions"][0]["target"] == {"device_id": wolink_entry.runtime_data.device_id}
    assert config["actions"][0]["data"]["payload"] == yaml.safe_load(result["payload"])
    assert config["actions"][0]["action"] == "ble_esl.write"
    assert config["alias"] == wolink_entry.title
    assert "id" not in config
    await async_validate_config_item(hass, "designer-test", {**config, "id": "designer-test"})


def test_automation_draft_preserves_jinja_instead_of_exported_snapshot():
    live = [{"type": "text", "value": "{{ states('sensor.room') }}", "x": 0, "y": 0}]
    exported = export_yaml([{**live[0], "value": "21"}], "white", "current-device", live=live)
    config = automation_draft(exported, "Room")
    assert config["actions"][0]["data"]["payload"] == live
