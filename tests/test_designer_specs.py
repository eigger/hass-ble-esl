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
from custom_components.ble_esl.designer.importer import different_pixels, elements_from, payloads
from custom_components.ble_esl.designer.layout import (
    compile_payload,
    validate,
    validate_template,
)
from custom_components.ble_esl.designer.specs import (
    GEOMETRY,
    ImportProblem,
    describe,
    element_types,
    from_payload,
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


async def test_a_templated_polygon_and_a_list_template_still_export(hass, wolink_entry):
    document = spec_document(
        element(
            "p", "polygon", 5, 5, 40, 40, points="{{ '0,0;100,0;50,100' }}", fill="{{ 'black' }}"
        ),
        element("s", "sparkline", 60, 5, 80, 30, values="{{ [1, 2, 3] }}"),
    )
    result = await hass.data[KEY].export(wolink_entry, document)
    now = yaml.safe_load(result["payload"])
    live = yaml.safe_load(result["live_payload"])
    assert now[1]["values"] == [1, 2, 3]
    # The corners are as of now, everything else keeps its template.
    assert live[0]["points"] == now[0]["points"]
    assert live[0]["fill"] == "{{ 'black' }}"
    assert live[1]["values"] == "{{ [1, 2, 3] }}"
    assert any("polygon's corners are as of now" in issue for issue in result["issues"])
    assert resolve_templates(hass, live, set()) == now


@pytest.mark.parametrize("type_", element_types())
@pytest.mark.parametrize(("width", "height"), [(None, None), (30, 30), (200, 90), (17, 5)])
def test_a_payload_becomes_the_same_payload_through_its_frame(type_, width, height):
    spec, default_width, default_height = new_spec(type_)
    payload = spec_payload(spec, 7, 5, width or default_width, height or default_height)
    again, x, y, w, h = from_payload(payload)
    assert spec_payload(again, x, y, w, h) == payload


def test_row_and_column_are_a_stack_with_their_direction():
    spec, _, _, _, _ = from_payload(
        {"type": "column", "x": 3, "y": 4, "width": 50, "height": 60, "elements": []}
    )
    assert spec["type"] == "stack"
    assert spec["direction"] == "vertical"


@pytest.mark.parametrize(
    ("item", "reason"),
    [
        (
            {"type": "rectangle", "x_start": "{{ 1 }}", "y_start": 0, "x_end": 9, "y_end": 9},
            "template",
        ),
        (
            {"type": "line", "x_start": 0, "y_start": 0, "x_end": 9, "y_end": 9},
            "horizontal or vertical",
        ),
        ({"type": "text", "value": "no y", "x": 3}, "'y'"),
        ({"type": "nonsense"}, "not an imagespec element"),
        ({"type": "polygon", "points": "0,0;1"}, "points"),
        ({"x": 1}, "type"),
    ],
)
def test_what_the_designer_cannot_place_says_why(item, reason):
    with pytest.raises(ImportProblem, match=reason):
        from_payload(item)


async def test_what_the_designer_exports_it_imports_unchanged(hass, wolink_entry):
    hass.states.async_set("sensor.room", "21.5")
    document = spec_document(
        element("pie", "pie", 5, 5, 60, 60),
        element("qr", "qrcode", 80, 5, 60, 60, data="{{ states('sensor.room') }}"),
        element("box", "rectangle", 150, 5, 40, 40, fill=None),
        element("poly", "polygon", 150, 60, 41, 31),
        element("txt", "text", 5, 80, 100, 30, value="{{ states('sensor.room') }} °C"),
    )
    manager = hass.data[KEY]
    exported = await manager.export(wolink_entry, document)
    for text in (exported["live_service"], exported["live_payload"], exported["payload"]):
        result = await manager.import_yaml(wolink_entry, text)
        assert result["issues"] == []
        assert len(result["elements"]) == 5
        assert result["different_pixels"] == 0
    live = await manager.import_yaml(wolink_entry, exported["live_payload"])
    texts = {e["spec"]["type"]: e["spec"] for e in live["elements"]}
    assert texts["text"]["value"] == "{{ states('sensor.room') }} °C"


async def test_import_keeps_what_it_can_place_and_says_what_it_cannot(hass, wolink_entry):
    text = yaml.safe_dump(
        [
            {"type": "text", "value": "placed", "x": 4, "y": 4},
            {"type": "text", "value": "no y, so it flows", "x": 4},
            {"type": "line", "x_start": 0, "y_start": 0, "x_end": 20, "y_end": 20},
            {"type": "circle", "x": 60, "y": 60, "radius": 10},
        ]
    )
    result = await hass.data[KEY].import_yaml(wolink_entry, text)
    assert [e["spec"]["type"] for e in result["elements"]] == ["text", "circle"]
    assert len(result["issues"]) == 2
    assert "#2 text" in result["issues"][0]
    assert "#3 line" in result["issues"][1]


@pytest.mark.parametrize("text", ["a: [", "just text", "[1, 2]", "data: {payload: 3}"])
async def test_import_rejects_what_is_not_a_payload(hass, wolink_entry, text):
    with pytest.raises(HomeAssistantError):
        await hass.data[KEY].import_yaml(wolink_entry, text)


async def test_import_counts_the_pixels_that_differ(hass):
    preset = DevicePreset("test", "test", 250, 122, "BWR")
    items = [
        {"type": "rectangle", "x_start": 10, "y_start": 10, "x_end": 49, "y_end": 29, "fill": "red"}
    ]
    elements, imported, issues = elements_from(items, preset)
    assert issues == []
    original, rebuilt = payloads(hass, imported, elements)
    same = await hass.async_add_executor_job(different_pixels, hass, preset, original, rebuilt)
    assert same == 0
    elements[0]["x"] += 10  # what a change the designer introduced would look like
    original, rebuilt = payloads(hass, imported, elements)
    moved = await hass.async_add_executor_job(different_pixels, hass, preset, original, rebuilt)
    assert moved > 0


async def test_import_over_the_websocket(hass, wolink_entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "ble_esl/designer",
            "action": "import_yaml",
            "entry_id": wolink_entry.entry_id,
            "text": "- {type: circle, x: 40, y: 40, radius: 12}",
        }
    )
    result = await client.receive_json()
    assert result["success"]
    assert result["result"]["different_pixels"] == 0
    assert result["result"]["elements"][0]["spec"]["type"] == "circle"


def test_a_yaml_alias_is_refused():
    from custom_components.ble_esl.designer.importer import parse

    bomb = "a: &a [1, 2, 3]\nb: &b [*a, *a]\npayload: [{type: text, value: *b, x: 1, y: 1}]"
    with pytest.raises(HomeAssistantError, match="aliases"):
        parse(bomb)


def test_yaml_nested_too_deeply_is_refused_not_raised():
    from custom_components.ble_esl.designer.importer import parse

    with pytest.raises(HomeAssistantError, match="nested too deeply"):
        parse("[" * 5000 + "]" * 5000)


def test_the_alias_message_says_what_to_do():
    from custom_components.ble_esl.designer.importer import parse

    with pytest.raises(HomeAssistantError, match="write the repeated values out"):
        parse("- &a {type: circle, x: 1, y: 1, radius: 2}\n- *a")


def test_too_much_text_is_refused():
    from custom_components.ble_esl.designer.importer import parse

    with pytest.raises(HomeAssistantError, match="too much"):
        parse("- {type: text, value: " + "x" * 300_000 + ", x: 1, y: 1}")


async def test_a_display_holds_a_hundred_elements_and_import_keeps_to_it(hass, wolink_entry):
    text = yaml.safe_dump(
        [{"type": "circle", "x": 20 + i % 100, "y": 20, "radius": 3} for i in range(120)]
    )
    manager = hass.data[KEY]
    result = await manager.import_yaml(wolink_entry, text)
    assert len(result["elements"]) == 100
    assert sum("holds at most" in issue for issue in result["issues"]) == 20
    room = await manager.import_yaml(wolink_entry, text, 95)
    assert len(room["elements"]) == 5


@pytest.mark.parametrize(
    "item",
    [
        {"type": "circle", "x": float("nan"), "y": 5, "radius": 5},
        {"type": "circle", "x": 5, "y": 5, "radius": float("inf")},
        {
            "type": "line",
            "x_start": 0,
            "y_start": 5,
            "x_end": 20,
            "y_end": 5,
            "width": float("nan"),
        },
        {"type": "polygon", "points": "nan,0;10,0;5,10"},
    ],
)
def test_a_number_that_is_not_one_is_listed_not_raised(item):
    elements, _, issues = elements_from([item], PRESET)
    assert elements == []
    assert len(issues) == 1


def test_numbers_written_as_text_are_numbers():
    elements, _, issues = elements_from(
        [{"type": "circle", "x": "40", "y": "30.0", "radius": "9"}], PRESET
    )
    assert issues == []
    assert (elements[0]["x"], elements[0]["y"]) == (30, 20)


@pytest.mark.parametrize(
    "line",
    [
        {"type": "line", "x_start": 10, "y_start": 5, "x_end": 11, "y_end": 5, "width": 6},
        {"type": "line", "x_start": 10, "y_start": 5, "x_end": 10, "y_end": 5, "width": 4},
        {"type": "line", "x_start": 7, "y_start": 2, "x_end": 7, "y_end": 4, "width": 8},
        {"type": "line", "x_start": 0, "y_start": 5, "x_end": 90, "y_end": 5, "width": 3},
    ],
)
def test_a_short_thick_line_stays_the_line_it_was(line):
    spec, x, y, width, height = from_payload(line)
    assert spec_payload(spec, x, y, width, height) == line


def test_an_icon_without_a_size_is_given_the_default_one():
    spec, x, y, width, height = from_payload({"type": "icon", "value": "mdi:home", "x": 4, "y": 6})
    assert (width, height) == (32, 32)
    assert spec_payload(spec, x, y, width, height)["size"] == 32


async def test_importing_templates_works_from_the_event_loop_in_debug(hass, wolink_entry):
    # Home Assistant checks that templates are rendered on the loop in debug mode.
    hass.config.debug = True
    hass.states.async_set("sensor.room", "21.5")
    text = "- {type: text, value: \"{{ states('sensor.room') }} C\", x: 5, y: 5}"
    result = await hass.data[KEY].import_yaml(wolink_entry, text)
    assert result["issues"] == []
    assert result["different_pixels"] == 0


def sensor(id_, entity_id, **fields):
    return {
        "id": id_,
        "type": "sensor",
        "entity_id": entity_id,
        "x": 8,
        "y": 8,
        "width": 180,
        "height": 70,
        "font_size": 32,
        **fields,
    }


async def test_a_numeric_sensor_converts_with_its_value_as_a_template(hass, wolink_entry):
    hass.states.async_set("sensor.room", "21.26", {"unit_of_measurement": "°C"})
    document = {"version": 1, "elements": [sensor("s", "sensor.room", decimals=1)]}
    result = await hass.data[KEY].convert(wolink_entry, document, "s")
    assert result["issues"] == []
    assert result["different_pixels"] == 0
    values = [e["spec"].get("value") for e in result["elements"]]
    template = (
        "{% set v = states('sensor.room') %}{{ v|capitalize if v in ['unavailable', 'unknown'] "
        "else ('%.1f'|format(v|float(0))) ~ ' °C' }}"
    )
    assert template in values
    types = [e["spec"]["type"] for e in result["elements"]]
    assert types.count("icon") == 1
    # The template follows the sensor: it renders to what the display showed.
    hass.states.async_set("sensor.room", "23.04", {"unit_of_measurement": "°C"})
    payload = compile_payload(hass, {"elements": result["elements"]})
    assert any(item.get("value") == "23.0 °C" for item in payload)
    # Gone, it shows what the designer shows then: no number, no unit.
    hass.states.async_set("sensor.room", "unavailable", {"unit_of_measurement": "°C"})
    payload = compile_payload(hass, {"elements": result["elements"]})
    assert any(item.get("value") == "Unavailable" for item in payload)


async def test_a_text_sensor_converts_without_rounding(hass, wolink_entry):
    hass.states.async_set("sensor.mode", "eco")
    document = {"version": 1, "elements": [sensor("s", "sensor.mode")]}
    result = await hass.data[KEY].convert(wolink_entry, document, "s")
    assert result["different_pixels"] == 0
    assert any("states('sensor.mode')" in str(e["spec"].get("value")) for e in result["elements"])


@pytest.mark.parametrize(
    ("entity_id", "state", "attributes"),
    [
        ("sensor.gone", "unavailable", {}),
        ("binary_sensor.door", "on", {"device_class": "door"}),
        ("weather.home", "sunny", {"temperature": 20}),
    ],
)
async def test_a_sensor_that_is_not_a_plain_value_converts_as_it_stands(
    hass, wolink_entry, entity_id, state, attributes
):
    hass.states.async_set(entity_id, state, attributes)
    document = {"version": 1, "elements": [sensor("s", entity_id)]}
    result = await hass.data[KEY].convert(wolink_entry, document, "s")
    assert result["elements"]
    assert result["different_pixels"] == 0
    assert not any("{{" in str(e["spec"]) for e in result["elements"])


async def test_a_shape_converts_to_the_same_shape(hass, wolink_entry):
    document = {
        "version": 1,
        "elements": [
            {
                "id": "r",
                "type": "rounded_rectangle",
                "x": 10,
                "y": 10,
                "width": 60,
                "height": 30,
                "color": "red",
            }
        ],
    }
    result = await hass.data[KEY].convert(wolink_entry, document, "r")
    assert [e["spec"]["type"] for e in result["elements"]] == ["rectangle"]
    assert result["different_pixels"] == 0


async def test_only_an_element_of_the_old_kinds_can_be_converted(hass, wolink_entry):
    manager = hass.data[KEY]
    document = spec_document(element("a", "circle", 0, 0, 40, 40))
    with pytest.raises(HomeAssistantError, match="already"):
        await manager.convert(wolink_entry, document, "a")
    with pytest.raises(HomeAssistantError, match="not in the display"):
        await manager.convert(wolink_entry, document, "nope")


async def test_convert_over_the_websocket(hass, wolink_entry, hass_ws_client):
    hass.states.async_set("sensor.room", "5")
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "ble_esl/designer",
            "action": "convert",
            "entry_id": wolink_entry.entry_id,
            "element_id": "s",
            "document": {"version": 1, "elements": [sensor("s", "sensor.room")]},
        }
    )
    result = await client.receive_json()
    assert result["success"]
    assert result["result"]["different_pixels"] == 0
    assert result["result"]["elements"]


@pytest.mark.parametrize(
    ("state", "attributes", "fields", "reason"),
    [
        ("21.5", {}, {"decimals": 2}, "bare number"),
        ("21.50", {}, {}, "bare number"),
        ("21.5", {"unit_of_measurement": "ft'"}, {}, "misread"),
        ("21.5", {"unit_of_measurement": 'in"'}, {}, "misread"),
    ],
)
async def test_a_value_that_a_template_would_change_stays_text(
    hass, wolink_entry, state, attributes, fields, reason
):
    hass.states.async_set("sensor.odd", state, attributes)
    document = {"version": 1, "elements": [sensor("s", "sensor.odd", **fields)]}
    result = await hass.data[KEY].convert(wolink_entry, document, "s")
    assert result["different_pixels"] == 0
    assert not any("{" in str(e["spec"].get("value", "")) for e in result["elements"])
    assert any(reason in issue for issue in result["issues"])


async def test_converting_cannot_pass_the_hundred_elements_a_display_holds(hass, wolink_entry):
    hass.states.async_set("sensor.room", "5", {"unit_of_measurement": "W"})
    shapes = [
        {"id": f"r{i}", "type": "rectangle", "x": i, "y": 0, "width": 4, "height": 4}
        for i in range(99)
    ]
    document = {"version": 1, "elements": [*shapes, sensor("s", "sensor.room")]}
    with pytest.raises(HomeAssistantError, match="holds 100"):
        await hass.data[KEY].convert(wolink_entry, document, "s")


@pytest.mark.parametrize("unit", ["{{ 7*7 }}", "{#x", "{% if %}"])
async def test_a_unit_that_is_template_syntax_is_left_out_not_executed(hass, wolink_entry, unit):
    hass.states.async_set("sensor.odd", "21.5", {"unit_of_measurement": unit})
    document = {"version": 1, "elements": [sensor("s", "sensor.odd")]}
    result = await hass.data[KEY].convert(wolink_entry, document, "s")
    assert any("template syntax" in issue for issue in result["issues"])
    assert not any(templates_in(e["spec"]) for e in result["elements"])
    # The value text is missing from what it draws: the comparison says so.
    assert result["different_pixels"] > 0
