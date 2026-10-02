"""Every imagespec element the designer offers builds a valid payload and renders."""

import base64
from functools import partial
from io import BytesIO

from homeassistant.exceptions import HomeAssistantError
import imagespec
from PIL import Image, ImageChops
import pytest
import voluptuous as vol
import yaml

from custom_components.ble_esl.designer import KEY
from custom_components.ble_esl.designer.layout import (
    compile_payload,
    validate,
    validate_template,
)
from custom_components.ble_esl.designer.specs import (
    GEOMETRY,
    describe,
    element_types,
    new_spec,
    resolve_templates,
    spec_payload,
    templates_in,
)
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.renderer import render_image

FRAMES = [(None, None), (30, 30), (200, 90), (1, 1), (17, 5), (5, 17)]
# Frames an element can legitimately be too small to draw in (a diagram needs
# room for its bars), so only these must render.
ROOMY = [(None, None), (200, 90)]
# Reads the recorder, which the test Home Assistant does not run.
NEEDS_RECORDER = ("plot",)


def test_every_imagespec_element_has_a_place_in_the_designer():
    # "row" and "column" are "stack" with a direction already chosen.
    assert set(element_types()) == imagespec.known_types() - {"row", "column"}


def test_describe_lists_fields_without_the_derived_geometry():
    by_type = {item["type"]: item for item in describe()["types"]}
    assert set(by_type) == set(element_types())
    rectangle = by_type["rectangle"]
    names = {field["name"] for field in rectangle["fields"]}
    assert not names & {"x_start", "y_start", "x_end", "y_end"}
    assert {"fill", "outline", "width", "radius", "corners"} <= names
    assert by_type["text"]["category"] == "text"
    assert by_type["plot"]["fields"]


@pytest.mark.parametrize("type_", element_types())
@pytest.mark.parametrize(("width", "height"), FRAMES)
def test_element_is_valid_in_any_frame(type_, width, height):
    spec, default_width, default_height = new_spec(type_)
    payload = spec_payload(spec, 7, 5, width or default_width, height or default_height)
    assert imagespec.validate([payload]) == []


@pytest.mark.parametrize("type_", [t for t in element_types() if t not in NEEDS_RECORDER])
@pytest.mark.parametrize(("width", "height"), ROOMY)
async def test_element_renders(hass, type_, width, height):
    spec, default_width, default_height = new_spec(type_)
    payload = spec_payload(spec, 7, 5, width or default_width, height or default_height)
    preset = DevicePreset("test", "test", 250, 122, "BWRY")
    image = await hass.async_add_executor_job(partial(render_image, hass, preset, [payload]))
    assert image.size == (250, 122)


FRAME_FILLING = ("box", "line", "circle", "rect", "icon")


@pytest.mark.parametrize(
    "type_",
    [t for t in element_types() if GEOMETRY[t][0] in FRAME_FILLING and t not in NEEDS_RECORDER],
)
@pytest.mark.parametrize(("width", "height"), [(None, None), (200, 90)])
async def test_a_frame_sized_element_draws_inside_its_frame(hass, type_, width, height):
    spec, default_width, default_height = new_spec(type_)
    width, height = width or default_width, height or default_height
    payload = spec_payload(spec, 20, 15, width, height)
    preset = DevicePreset("test", "test", 250, 122, "BWRY")
    image = await hass.async_add_executor_job(partial(render_image, hass, preset, [payload]))
    drawn = ImageChops.difference(image, Image.new("RGB", image.size, "white")).getbbox()
    assert drawn is not None, "nothing was drawn"
    left, top, right, bottom = drawn
    # A pixel of slack for strokes centred on the frame's edge.
    assert left >= 19 and top >= 14, drawn
    assert right <= 20 + width + 1 and bottom <= 15 + height + 1, drawn


@pytest.mark.parametrize("type_", ["qrcode", "barcode", "datamatrix", "icon"])
def test_the_frame_sizes_codes_and_icons(type_):
    spec, _, _ = new_spec(type_)
    small = spec_payload(spec, 0, 0, 30, 30)
    large = spec_payload(spec, 0, 0, 90, 70)
    assert small != large
    assert imagespec.validate([small, large]) == []


def test_frame_supplies_the_position_keys():
    spec, _, _ = new_spec("rectangle")
    assert spec_payload(spec, 10, 20, 30, 40) | {} == {
        **{k: v for k, v in spec.items()},
        "x_start": 10,
        "y_start": 20,
        "x_end": 39,
        "y_end": 59,
    }
    circle, _, _ = new_spec("circle")
    payload = spec_payload(circle, 0, 0, 40, 20)
    assert (payload["x"], payload["y"], payload["radius"]) == (20, 10, 9)
    line, _, _ = new_spec("line")
    assert spec_payload(line, 0, 0, 50, 4)["y_start"] == 2
    assert spec_payload(line, 0, 0, 4, 50)["x_start"] == 2
    triangle, _, _ = new_spec("polygon")
    assert spec_payload(triangle, 10, 10, 41, 21)["points"] == "30,10;50,30;10,30"


def test_stored_position_keys_are_ignored():
    spec, _, _ = new_spec("rectangle")
    stored = {**spec, "x_start": 500, "y_end": 9000}
    assert spec_payload(stored, 10, 20, 30, 40) == spec_payload(spec, 10, 20, 30, 40)


def test_templates_are_found_and_rendered_like_an_automation(hass):
    hass.states.async_set("sensor.room", "21.5")
    spec = {
        "type": "text",
        "value": "{{ states('sensor.room') }} °C",
        "size": "{{ 10 + 10 }}",
        "color": "black",
    }
    assert templates_in(spec) == ["{{ states('sensor.room') }} °C", "{{ 10 + 10 }}"]
    entities = set()
    resolved = resolve_templates(hass, spec, entities)
    assert resolved == {"type": "text", "value": "21.5 °C", "size": 20, "color": "black"}
    assert entities == {"sensor.room"}


def element(id_, type_, x, y, width, height, **spec):
    base, _, _ = new_spec(type_)
    return {
        "id": id_,
        "type": "imagespec",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "spec": {**base, **spec},
    }


def spec_document(*elements):
    return {"version": 1, "elements": list(elements)}


PRESET = DevicePreset("test", "test", 250, 122, "BWR")


def test_validation_accepts_an_imagespec_element_and_rejects_an_unknown_type():
    document = spec_document(element("a", "circle", 0, 0, 40, 40))
    assert validate(document, PRESET)["elements"][0]["spec"]["type"] == "circle"
    document["elements"][0]["spec"] = {"type": "nonsense"}
    with pytest.raises(vol.Invalid, match="element type"):
        validate(document, PRESET)


async def test_payload_is_ordinary_imagespec_in_display_coordinates(hass):
    hass.states.async_set("sensor.room", "21.5")
    document = validate(
        spec_document(
            element("a", "rectangle", 10, 20, 30, 40),
            element("b", "text", 50, 8, 100, 30, value="{{ states('sensor.room') }} °C"),
        ),
        PRESET,
    )
    payload = compile_payload(hass, document)
    assert payload[0]["x_start"] == 10 and payload[0]["y_end"] == 59
    assert payload[1] | {} == {"type": "text", "value": "21.5 °C", "size": 20, "x": 50, "y": 8}
    assert imagespec.validate(payload) == []


async def test_preview_export_and_tag_agree_for_imagespec_elements(hass, wolink_entry, tag_writer):
    hass.states.async_set("sensor.room", "21.5")
    document = spec_document(
        element("pie", "pie", 5, 5, 60, 60),
        element("qr", "qrcode", 80, 5, 60, 60, data="{{ states('sensor.room') }}"),
        element("box", "rectangle", 150, 5, 40, 40, fill=None),
    )
    manager = hass.data[KEY]
    preview = await manager.preview(wolink_entry, document)
    exported = await manager.export(wolink_entry, document)
    payload = yaml.safe_load(exported["payload"])
    assert [item["type"] for item in payload] == ["pie", "qrcode", "rectangle"]
    # Rendered as an automation renders a template: "21.5" arrives as a number.
    assert payload[1]["data"] == 21.5
    assert exported["issues"] == []
    expected = await hass.async_add_executor_job(
        partial(render_image, hass, manager.preset(wolink_entry), payload, background="white")
    )
    with Image.open(BytesIO(base64.b64decode(preview["png"].split(",")[1]))) as actual:
        assert actual.tobytes() == expected.tobytes()
    assert set(preview["layers"]) >= {"pie", "qr", "box"}
    await manager.send(wolink_entry, document)
    assert tag_writer.sent_image().tobytes() == expected.tobytes()


async def test_the_specs_action_describes_every_element(hass, wolink_entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "ble_esl/designer", "action": "specs"})
    result = await client.receive_json()
    assert result["success"]
    assert {item["type"] for item in result["result"]["types"]} == set(element_types())
    assert "floyd" in result["result"]["dither_methods"]


async def test_a_layer_keeps_what_a_text_draws_past_its_frame(hass, wolink_entry):
    # 40px glyphs in a 20x10 frame: the frame is nowhere near what is drawn.
    document = spec_document(element("big", "text", 10, 10, 20, 10, value="WIDE", size=40))
    layers = (await hass.data[KEY].preview(wolink_entry, document))["layers"]
    left, top, right, bottom = layers["_bounds"]["big"]
    assert right - left > 20
    assert bottom - top > 10


def test_a_polygons_corners_are_editable_in_percent_of_the_frame():
    polygon = next(item for item in describe()["types"] if item["type"] == "polygon")
    points = next(field for field in polygon["fields"] if field["name"] == "points")
    assert "percent" in points["doc"]
    spec, _, _ = new_spec("polygon")
    bad = {**spec, "points": "50,0;100"}
    with pytest.raises(HomeAssistantError, match="polygon points"):
        spec_payload(bad, 0, 0, 40, 40)


def test_validation_names_what_is_wrong_with_an_element():
    for bad in ({"type": ["circle"]}, {"type": "row"}, {"type": "nonsense"}):
        document = spec_document({**element("a", "circle", 0, 0, 40, 40), "spec": bad})
        with pytest.raises(vol.Invalid, match="element type"):
            validate(document, PRESET)
    star = element("s", "star_rating", 0, 0, 80, 20)
    del star["spec"]["rating"]
    with pytest.raises(vol.Invalid, match="star_rating"):
        validate(spec_document(star), PRESET)
    # An element waiting on a template is checked once the template is rendered.
    star["spec"]["rating"] = "{{ 3 }}"
    validate(spec_document(star), PRESET)


def test_sensor_templates_cannot_hold_imagespec_elements():
    template = {
        "width": 100,
        "height": 60,
        "sensor_type": "output:numeric",
        "document": spec_document(element("a", "circle", 0, 0, 40, 40)),
    }
    with pytest.raises(vol.Invalid, match="imagespec"):
        validate_template(template)


async def test_the_preview_knows_which_entities_a_template_reads(hass, wolink_entry):
    hass.states.async_set("sensor.room", "21.5")
    document = spec_document(
        element("t", "text", 5, 5, 100, 30, value="{{ states('sensor.room') }}")
    )
    layers = (await hass.data[KEY].preview(wolink_entry, document))["layers"]
    assert layers["_dependencies"]["t"] == ["sensor.room"]


@pytest.mark.parametrize("type_", ["multiline", "rich_text"])
async def test_text_blocks_start_inside_their_frame(hass, type_):
    spec, width, height = new_spec(type_)
    payload = spec_payload(spec, 20, 30, width, height)
    preset = DevicePreset("test", "test", 250, 122, "BWRY")
    image = await hass.async_add_executor_job(partial(render_image, hass, preset, [payload]))
    top, bottom = ImageChops.difference(image, Image.new("RGB", image.size, "white")).getbbox()[
        1::2
    ]
    assert top >= 29, "drawn above the frame"
    assert bottom <= 30 + height + 1, "drawn below the frame"


def test_a_template_in_one_field_does_not_excuse_a_missing_required_one():
    star = element("s", "star_rating", 0, 0, 80, 20, size="{{ 12 }}")
    del star["spec"]["rating"]
    with pytest.raises(vol.Invalid, match="star_rating rating"):
        validate(spec_document(star), PRESET)


async def test_a_layer_is_placed_where_the_editor_holds_the_element(hass, wolink_entry):
    # A field template moves the element on the display; its layer is still
    # positioned from the frame in the document.
    rectangle = {
        "id": "moved",
        "type": "rectangle",
        "x": 10,
        "y": 10,
        "width": 40,
        "height": 20,
        "color": "red",
        "field_templates": {"x": "{{ 120 }}"},
    }
    document = {"version": 1, "elements": [rectangle]}
    result = await hass.data[KEY].preview(wolink_entry, document)
    with Image.open(BytesIO(base64.b64decode(result["png"].split(",")[1]))) as shown:
        stacked = Image.new("RGB", shown.size, "white")
        left, top = result["layers"]["_offsets"]["moved"]
        with Image.open(
            BytesIO(base64.b64decode(result["layers"]["moved"].split(",")[1]))
        ) as layer:
            stacked.paste(layer, (10 + left, 10 + top), layer)
        assert stacked.tobytes() == shown.tobytes()


def test_a_template_does_not_hide_a_misspelt_key_or_a_wrong_value_elsewhere():
    circle = element("c", "circle", 0, 0, 40, 40)
    circle["spec"]["colour"] = "{{ 'red' }}"
    with pytest.raises(vol.Invalid, match="colour"):
        validate(spec_document(circle), PRESET)
    polygon = element("p", "polygon", 0, 0, 40, 40, points="{{ '0,0;100,0;50,100' }}")
    validate(spec_document(polygon), PRESET)
    polygon["spec"]["bogus"] = 1
    with pytest.raises(vol.Invalid, match="bogus"):
        validate(spec_document(polygon), PRESET)


async def test_the_live_export_keeps_templates_and_renders_to_the_same_payload(hass, wolink_entry):
    hass.states.async_set("sensor.room", "21.5")
    document = spec_document(
        element(
            "t", "text", 5, 5, 100, 30, value="{{ states('sensor.room') }} °C", size="{{ 10 + 10 }}"
        ),
        element("r", "rectangle", 5, 40, 60, 20),
    )
    result = await hass.data[KEY].export(wolink_entry, document)
    now = yaml.safe_load(result["payload"])
    live = yaml.safe_load(result["live_payload"])
    assert now[0]["value"] == "21.5 °C"
    assert live[0]["value"] == "{{ states('sensor.room') }} °C"
    assert live[0]["size"] == "{{ 10 + 10 }}"
    # What the automation will render is what the designer shows now.
    assert resolve_templates(hass, live, set()) == now
    service = yaml.safe_load(result["live_service"])
    assert service["action"] == "ble_esl.write"
    assert service["data"]["payload"] == live


async def test_there_is_no_live_export_without_templates(hass, wolink_entry):
    document = spec_document(element("r", "rectangle", 5, 40, 60, 20))
    result = await hass.data[KEY].export(wolink_entry, document)
    assert "live_payload" not in result
    assert "live_service" not in result
