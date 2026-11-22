"""Design templates: format, parameter substitution, layouts and the designer API."""

from unittest.mock import patch

from homeassistant.components.automation.config import async_validate_config_item
from homeassistant.exceptions import HomeAssistantError
import pytest
import voluptuous as vol
import yaml

from custom_components.ble_esl.designer import KEY
from custom_components.ble_esl.designer.design_templates import (
    TEMPLATE_DIR,
    build,
    choose_layout,
    coerce_value,
    describe,
    load_templates,
    parse_template,
    resolve_parameters,
    substitute,
)
from custom_components.ble_esl.designer.importer import (
    different_pixels,
    elements_from,
    payloads,
)
from custom_components.ble_esl.designer.specs import resolve_templates
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.renderer import render_image

TEMPLATES = load_templates()
# Cover the palette matrix and the largest layout in both orientations.
RENDER_CASES = [
    (width, height, colors)
    for width, height in [(250, 128), (296, 128), (400, 300), (800, 480)]
    for colors in ("BW", "BWR", "BWRY")
] + [(1600, 1200, "BWR"), (1200, 1600, "BWR")]

MINIMAL = """
template: 1
id: sample
name: Sample
layouts:
  "250x128":
    - {type: text, value: "${label}", x: 10, y: 20, size: 20, color: "${ink}"}
parameters:
  label: {type: string, default: Hello}
  ink: {type: color, default: red}
"""


def test_every_bundled_template_loads():
    files = sorted(TEMPLATE_DIR.glob("*.yaml"))
    assert files
    assert len(TEMPLATES) == len(files)


def test_categories_in_gallery_and_legacy_templates():
    assert len(TEMPLATES) == 19
    assert all(template["categories"] for template in TEMPLATES.values())
    for key in ("calendar_weather", "date_weather"):
        assert set(describe(TEMPLATES[key], 250, 128)["categories"]) == {"weather", "schedule"}
    legacy = parse_template(MINIMAL)
    assert describe(legacy, 250, 128)["categories"] == []
    with pytest.raises(vol.Invalid):
        parse_template(MINIMAL + "\ncategories: [unknown]\n")


def seed_entities(hass, template):
    """States for the entities a template's parameters default to."""
    for parameter in template["parameters"].values():
        if parameter["type"] == "entity":
            hass.states.async_set(
                parameter["default"],
                "partlycloudy",
                {
                    "friendly_name": "Home",
                    "temperature": 21.5,
                    "temperature_unit": "°C",
                    "humidity": 55,
                },
            )


def stable_template_payloads(hass, imported, elements):
    """Compare geometry with the same clock on both sides of the round trip."""
    from homeassistant.util import dt as dt_util

    now = dt_util.now()
    with patch.object(dt_util, "now", return_value=now):
        return payloads(hass, imported, elements)


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
@pytest.mark.parametrize(("width", "height", "colors"), RENDER_CASES)
async def test_bundled_template_imports_and_draws_exactly(hass, template_id, width, height, colors):
    preset = DevicePreset("test", "test", width, height, colors)
    seed_entities(hass, TEMPLATES[template_id])
    built = build(TEMPLATES[template_id], width, height, colors)
    elements, imported, issues = elements_from(built["payload"], preset)
    assert issues == []
    assert len(elements) == len(built["payload"])
    original, rebuilt = stable_template_payloads(hass, imported, elements)
    assert different_pixels(hass, preset, original, rebuilt, built["background"]) == 0
    for item in original:
        for key in ("x", "x_start", "x_end"):
            assert 0 <= item.get(key, 0) <= width
        for key in ("y", "y_start", "y_end"):
            assert 0 <= item.get(key, 0) <= height


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
async def test_bundled_automation_is_a_valid_home_assistant_automation(hass, template_id):
    template = TEMPLATES[template_id]
    seed_entities(hass, template)
    built = build(template, 250, 128, "BWR")
    if built["automation"] is None:
        pytest.skip("no automation")
    config = {
        **built["automation"],
        "alias": built["automation"].get("alias", "x"),
        "actions": [
            *built["automation"].get("actions", []),
            {"action": "ble_esl.write", "data": {"payload": built["payload"]}},
        ],
    }
    assert await async_validate_config_item(hass, "x", config)


def test_substitute_keeps_the_type_of_a_lone_reference():
    values = {"n": 5, "name": "A", "flag": True}
    assert substitute("${n}", values) == 5
    assert substitute("${name}-${n}", values) == "A-5"
    assert substitute({"a": ["${flag}", "x ${flag}"]}, values) == {"a": [True, "x true"]}


def test_parameters_are_checked():
    template = parse_template(MINIMAL)
    assert resolve_parameters(template, {"label": "Hi"}, "BWR")["label"] == "Hi"
    with pytest.raises(HomeAssistantError, match="Unknown"):
        resolve_parameters(template, {"nope": 1}, "BWR")
    for bad in ("{{ x }}", "it's", 'a"b', "a\\b", "a\nb"):
        with pytest.raises(HomeAssistantError, match="label"):
            resolve_parameters(template, {"label": bad}, "BWR")
    with pytest.raises(HomeAssistantError, match="ink"):
        resolve_parameters(template, {"ink": "purple"}, "BWR")


def test_unsupported_color_falls_back_to_black():
    template = parse_template(MINIMAL)
    assert resolve_parameters(template, {}, "BWR")["ink"] == "red"
    assert resolve_parameters(template, {}, "BW")["ink"] == "black"


def test_value_coercion():
    time = {"type": "time", "default": "12:00"}
    assert coerce_value("t", time, "07:30", None) == "07:30:00"
    with pytest.raises(vol.Invalid):
        coerce_value("t", time, "25:00", None)
    number = {"type": "number", "default": 1, "min": 0, "max": 10}
    with pytest.raises(vol.Invalid):
        coerce_value("n", number, 11, None)
    with pytest.raises(vol.Invalid):
        coerce_value("n", number, True, None)
    with pytest.raises(vol.Invalid):
        coerce_value("f", {"type": "font", "default": "a.ttf"}, "../a.ttf", None)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (("${label}", "${missing}"), "undeclared"),
        (("template: 1", "template: 2"), "template"),
        (("type: string", "type: nope"), "type"),
    ],
)
def test_invalid_templates_are_rejected(change, message):
    text = MINIMAL.replace(*change)
    with pytest.raises(vol.Invalid, match=message):
        parse_template(text)


def test_yaml_aliases_are_refused(tmp_path):
    (tmp_path / "a.yaml").write_text(MINIMAL.replace("size: 20,", "size: &s 20,", 1) + "x: *s\n")
    with pytest.raises(ValueError, match="aliases"):
        parse_template((tmp_path / "a.yaml").read_text())
    assert load_templates(tmp_path) == {}


def test_trailing_newline_is_not_accepted():
    with pytest.raises(vol.Invalid):
        coerce_value("t", {"type": "time", "default": "12:00"}, "12:00\n", None)
    with pytest.raises(vol.Invalid):
        coerce_value("f", {"type": "font", "default": "a.ttf"}, "a.ttf\n", None)


def test_scaling_moves_every_geometry_key():
    text = """
template: 1
id: boxes
name: Boxes
layouts:
  "250x128":
    - {type: rectangle, x_start: 10, y_start: 10, x_end: 240, y_end: 118, fill: red}
    - {type: line, x_start: 0, y_start: 64, x_end: 250, y_end: 64}
    - {type: multiline, x: 5, start_y: 20, value: "a", delimiter: ",", offset_y: 10}
    - {type: dlimg, url: x, x: 0, y: 0, xsize: 50, ysize: 20}
"""
    items = build(parse_template(text), 500, 256, "BWR")["payload"]
    assert items[0] == {**items[0], "x_start": 20, "y_start": 20, "x_end": 480, "y_end": 236}
    assert (items[1]["x_start"], items[1]["x_end"]) == (0, 500)
    assert items[2]["start_y"] == 40
    assert (items[3]["xsize"], items[3]["ysize"]) == (100, 40)
    # Centred: a wider display shifts the whole layout, not just the end corner.
    wide = build(parse_template(text), 296, 128, "BWR")["payload"][0]
    assert (wide["x_start"], wide["x_end"]) == (33, 263)


def test_scaling_covers_other_lengths_and_keeps_counts():
    text = """
template: 1
id: more
name: More
layouts:
  "250x128":
    - {type: rectangle_pattern, x_start: 0, y_start: 0, x_end: 250, y_end: 128, x_size: 10,
       y_size: 10, x_repeat: 3, y_repeat: 2, x_offset: 4, y_offset: 4}
    - {type: text, value: a, x: 0, y: 0, max_width: 200, max_lines: 2, size: 20, rotation: 90}
    - {type: rectangle, x_start: 0, y_start: 0, x_end: 5, y_end: 5, width: 1, outline: black}
"""
    template = parse_template(text)
    pattern, label, box = build(template, 500, 256, "BWR")["payload"]
    assert (pattern["x_size"], pattern["x_offset"]) == (20, 8)
    assert (pattern["x_repeat"], pattern["y_repeat"]) == (3, 2)
    assert (label["max_width"], label["max_lines"], label["rotation"]) == (400, 2, 90)
    small = build(template, 125, 64, "BWR")["payload"][2]
    assert small["width"] == 1  # a 1px outline never shrinks to nothing
    assert box["width"] == 2


def test_scaling_leaves_data_and_module_counts_alone():
    text = """
template: 1
id: data
name: Data
layouts:
  "250x128":
    - {type: sparkline, x: 0, y: 0, width: 100, height: 40, values: [1, 2, 3], min: 0, max: 5}
    - {type: gauge, x: 50, y: 50, radius: 40, min_value: 0, max_value: 100, progress: 30}
    - {type: table, x: 0, y: 0, rows: [[42, 7]]}
    - {type: qrcode, data: 12345, x: 0, y: 0, width: 50, height: 50, border: 2}
    - {type: barcode, data: 8801234567890, dither: 1, x: 0, y: 0, width: 80, height: 30, module_width: 0.2}
    - {type: stack, direction: row, width: 100, height: 20, elements: [{type: text, value: a, grow: 2}]}
"""
    spark, gauge, table, qr, barcode, stack = build(parse_template(text), 125, 64, "BWR")["payload"]
    assert (spark["values"], spark["max"], spark["width"]) == ([1, 2, 3], 5, 50)
    assert (gauge["max_value"], gauge["progress"], gauge["radius"]) == (100, 30, 20)
    assert table["rows"] == [[42, 7]]
    assert (qr["border"], qr["width"], qr["data"]) == (2, 25, 12345)
    assert (barcode["module_width"], barcode["data"], barcode["dither"]) == (0.2, 8801234567890, 1)
    # A group or stack without a position is centred with the rest.
    assert (stack["x"], stack["elements"][0]["grow"]) == (0, 2)
    wide = build(parse_template(text), 296, 128, "BWR")["payload"][-1]
    assert wide["x"] == 23


def test_polygon_inside_a_group_is_not_scaled():
    text = MINIMAL.replace(
        "- {type: text,",
        "- {type: group, x: 0, y: 0, width: 50, height: 50, elements: "
        "[{type: polygon, points: '0,0 10,0 5,10', fill: red}]}\n    - {type: text,",
    )
    template = parse_template(text)
    with pytest.raises(HomeAssistantError, match="polygon"):
        build(template, 400, 300, "BWR")


def test_polygon_layouts_are_not_scaled():
    text = MINIMAL.replace(
        "- {type: text,",
        "- {type: polygon, points: '0,0 10,0 5,10', fill: red} # \n    - {type: text,",
    )
    template = parse_template(text)
    assert build(template, 250, 128, "BWR")["payload"][0]["type"] == "polygon"
    with pytest.raises(HomeAssistantError, match="polygon"):
        build(template, 400, 300, "BWR")


def test_design_parameter_cannot_belong_to_the_automation():
    text = MINIMAL.replace("label: {type: string,", "label: {group: automation, type: string,")
    with pytest.raises(vol.Invalid, match="automation"):
        parse_template(text)


def test_nearest_layout_is_scaled_and_centred():
    template = parse_template(MINIMAL)
    assert choose_layout(template, 250, 128) == ("250x128", True)
    built = build(template, 500, 256, "BWR")
    assert built["scaled"] is True
    item = built["payload"][0]
    assert (item["x"], item["y"], item["size"]) == (20, 40, 40)
    wide = build(template, 296, 128, "BWR")["payload"][0]
    assert wide["x"] == 10 + 23  # centred: (296 - 250) / 2


def test_load_skips_broken_and_duplicate_files(tmp_path, caplog):
    (tmp_path / "a.yaml").write_text(MINIMAL)
    (tmp_path / "b.yaml").write_text(MINIMAL)
    (tmp_path / "c.yaml").write_text("template: 1\n")
    assert list(load_templates(tmp_path)) == ["sample"]
    assert "duplicate id" in caplog.text


async def test_websocket_lists_and_applies_a_template(hass, wolink_entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "ble_esl/designer",
            "action": "design_templates",
            "entry_id": wolink_entry.entry_id,
        }
    )
    listed = (await client.receive_json())["result"]
    assert "date" in {item["id"] for item in listed}

    await client.send_json(
        {
            "id": 2,
            "type": "ble_esl/designer",
            "action": "apply_design_template",
            "entry_id": wolink_entry.entry_id,
            "template_id": "date",
            "parameters": {"time": "18:30"},
        }
    )
    result = (await client.receive_json())["result"]
    assert len(result["elements"]) == 2
    assert result["different_pixels"] == 0
    assert result["template"]["automation"]["triggers"] == [{"trigger": "time", "at": "18:30:00"}]

    await client.send_json(
        {
            "id": 3,
            "type": "ble_esl/designer",
            "action": "automation",
            "entry_id": wolink_entry.entry_id,
            "document": {"version": 1, "elements": result["elements"], "background": "white"},
            "automation_defaults": result["template"]["automation"],
        }
    )
    draft = (await client.receive_json())["result"]["automation"]
    assert draft["triggers"] == [{"trigger": "time", "at": "18:30:00"}]
    # The date template names no alias: the new automation takes the tag's title.
    assert draft["alias"] == wolink_entry.title
    assert draft["actions"][0]["action"] == "ble_esl.write"
    assert "{{ now()" in yaml.dump(draft["actions"])

    await client.send_json(
        {
            "id": 4,
            "type": "ble_esl/designer",
            "action": "apply_design_template",
            "entry_id": wolink_entry.entry_id,
        }
    )
    assert (await client.receive_json())["error"]["message"] == "template_id is required"


async def test_applying_rejects_unknown_template_and_missing_font(hass, wolink_entry):
    designer = hass.data[KEY]
    with pytest.raises(HomeAssistantError, match="no design template"):
        await designer.apply_design_template(wolink_entry, "nope")
    with pytest.raises(HomeAssistantError, match="Font not found"):
        await designer.apply_design_template(wolink_entry, "date", {"font": "Missing.ttf"})


async def test_short_weekday_list_renders_instead_of_failing(hass, wolink_entry):
    result = await hass.data[KEY].apply_design_template(
        wolink_entry, "date", {"weekdays": "Mon,Tue"}
    )
    assert result["issues"] == []
    assert result["different_pixels"] == 0


def test_forbidden_characters_are_refused():
    wifi = TEMPLATES["wifi"]
    for bad in ("a;b", "a:b", "a,b"):
        with pytest.raises(HomeAssistantError, match="ssid"):
            resolve_parameters(wifi, {"ssid": bad}, "BWR")
    assert resolve_parameters(wifi, {"ssid": "Home Net"}, "BWR")["ssid"] == "Home Net"
    for bad in ("a;b", "a:b", "a,b"):
        with pytest.raises(HomeAssistantError, match="password"):
            resolve_parameters(wifi, {"password": bad}, "BWR")
    with pytest.raises(HomeAssistantError, match="at least 1"):
        resolve_parameters(wifi, {"ssid": ""}, "BWR")
    built = build(wifi, 250, 128, "BWR", {"ssid": "Home", "password": "pw", "security": "WEP"})
    assert built["payload"][2]["data"] == "WIFI:T:WEP;S:Home;P:pw;H:false;;"
    hidden = build(wifi, 250, 128, "BWR", {"security": "SAE", "hidden": "true"})
    assert hidden["payload"][2]["data"] == "WIFI:T:SAE;S:ssid;P:password;H:true;;"


def _frame(item):
    left = item.get("x", item.get("x_start", 0))
    top = item.get("y", item.get("y_start", 0))
    right = item.get("x_end", left + item.get("width", 0))
    bottom = item.get("y_end", top + item.get("height", 0))
    return left, top, right, bottom


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
def test_boxes_stay_on_the_display_in_every_exact_layout(template_id):
    template = TEMPLATES[template_id]
    for size in template["layouts"]:
        width, height = (int(part) for part in size.split("x"))
        built = build(template, width, height, "BWRY")
        assert built["scaled"] is False
        for item in built["payload"]:
            if item["type"] in ("text_fit", "qrcode", "rectangle"):
                left, top, right, bottom = _frame(item)
                assert 0 <= left < right <= width, (size, item)
                assert 0 <= top < bottom <= height, (size, item)


def test_wifi_text_does_not_overlap_the_qr_code():
    for size in TEMPLATES["wifi"]["layouts"]:
        width, height = (int(part) for part in size.split("x"))
        items = build(TEMPLATES["wifi"], width, height, "BWR")["payload"]
        qr = next(_frame(item) for item in items if item["type"] == "qrcode")
        for item in items:
            if item["type"] == "text_fit":
                left, top, right, bottom = _frame(item)
                assert left >= qr[2] or right <= qr[0] or top >= qr[3] or bottom <= qr[1], size


def test_message_text_and_line_count_are_applied():
    built = build(TEMPLATES["message"], 250, 128, "BWR", {"text": "Hi", "lines": 3})
    assert (built["payload"][0]["value"], built["payload"][0]["max_lines"]) == ("Hi", 3)


def _text_document(value="Hello"):
    return {
        "version": 1,
        "background": "white",
        "elements": [
            {
                "id": "t",
                "type": "imagespec",
                "x": 5,
                "y": 6,
                "width": 120,
                "height": 30,
                "spec": {"type": "text_fit", "value": value, "color": "black"},
            }
        ],
    }


async def test_saved_design_becomes_a_user_template(hass, wolink_entry, tmp_path):
    hass.config.config_dir = str(tmp_path)
    designer = hass.data[KEY]
    saved = await designer.save_design_template(
        wolink_entry, _text_document("{{ now().year }}"), "My Year"
    )
    assert saved["id"] == "my_year"
    path = designer.user_template_dir / "my_year.yaml"
    assert path.is_file()
    template = designer.design_templates["my_year"]
    assert template["source"] == "user"
    preset = designer.preset(wolink_entry)
    built = build(template, preset.width, preset.height, preset.colors)
    assert built["scaled"] is False
    assert built["payload"][0]["value"] == "{{ now().year }}"
    # A second save under the same name never overwrites by accident.
    again = await designer.save_design_template(wolink_entry, _text_document(), "My Year")
    assert again["id"] == "my_year_2"
    with pytest.raises(HomeAssistantError, match="already exists"):
        await designer.save_design_template(
            wolink_entry, _text_document(), "My Year", template_id="my_year"
        )
    await designer.save_design_template(
        wolink_entry, _text_document("v2"), "My Year", template_id="my_year", overwrite=True
    )
    assert (await designer.apply_design_template(wolink_entry, "my_year"))["elements"]


async def test_saving_refuses_bad_names_ids_and_references(hass, wolink_entry, tmp_path):
    hass.config.config_dir = str(tmp_path)
    designer = hass.data[KEY]
    for name in ("", "   ", "x" * 81, "a\nb"):
        with pytest.raises(HomeAssistantError, match="name"):
            await designer.save_design_template(wolink_entry, _text_document(), name)
    with pytest.raises(HomeAssistantError, match="bundled"):
        await designer.save_design_template(wolink_entry, _text_document(), "Date", "date")
    # Saved by name only, a bundled id is simply taken: the new one gets a suffix.
    named = await designer.save_design_template(wolink_entry, _text_document(), "Date")
    assert named["id"] == "date_2"
    with pytest.raises(HomeAssistantError, match="cannot be saved"):
        await designer.save_design_template(wolink_entry, _text_document("${x}"), "Ref")
    with pytest.raises(HomeAssistantError, match="lowercase"):
        await designer.save_design_template(
            wolink_entry, _text_document(), "Path", template_id="../evil"
        )
    assert not list(designer.user_template_dir.glob("*evil*"))


def test_user_templates_cannot_replace_bundled_ones(tmp_path, caplog):
    from custom_components.ble_esl.designer.design_templates import load_all

    (tmp_path / "date.yaml").write_text(MINIMAL.replace("id: sample", "id: date"))
    (tmp_path / "mine.yaml").write_text(MINIMAL)
    templates = load_all(tmp_path)
    assert templates["date"]["source"] == "bundled"
    assert templates["sample"]["source"] == "user"
    assert "already bundled" in caplog.text


def test_slug_makes_a_valid_id():
    from custom_components.ble_esl.designer.design_templates import slug

    assert slug("My Year!") == "my_year"
    assert slug("날짜") == "design"
    assert slug("3 days") == "design_3_days"
    assert parse_template(MINIMAL.replace("id: sample", f"id: {slug('3 days')}"))


async def test_saving_never_overwrites_files_that_did_not_load(hass, wolink_entry, tmp_path):
    hass.config.config_dir = str(tmp_path)
    designer = hass.data[KEY]
    folder = designer.user_template_dir
    folder.mkdir(parents=True)
    (folder / "draft.yaml").write_text("template: 1\nid: draft\n")  # invalid, still being edited
    (folder / "draft_2.yaml").write_text("template: 1\n")
    saved = await designer.save_design_template(wolink_entry, _text_document(), "Draft")
    assert saved["id"] == "draft_3"
    assert (folder / "draft.yaml").read_text() == "template: 1\nid: draft\n"
    with pytest.raises(HomeAssistantError, match="already exists"):
        await designer.save_design_template(
            wolink_entry, _text_document(), "Draft", template_id="draft"
        )


async def test_id_defined_in_another_file_is_not_taken_over(hass, wolink_entry, tmp_path):
    hass.config.config_dir = str(tmp_path)
    designer = hass.data[KEY]
    folder = designer.user_template_dir
    folder.mkdir(parents=True)
    (folder / "aaa.yaml").write_text(MINIMAL)
    await designer.reload_design_templates()
    assert designer.design_templates["sample"]["file"] == "aaa.yaml"
    with pytest.raises(HomeAssistantError, match=r"aaa\.yaml"):
        await designer.save_design_template(
            wolink_entry, _text_document(), "Sample", template_id="sample", overwrite=True
        )
    # By name the taken id just gets a suffix, so nothing is hidden by a duplicate.
    assert (await designer.save_design_template(wolink_entry, _text_document(), "Sample"))[
        "id"
    ] == "sample_2"


async def test_concurrent_saves_get_distinct_ids(hass, wolink_entry, tmp_path):
    import asyncio

    hass.config.config_dir = str(tmp_path)
    designer = hass.data[KEY]
    results = await asyncio.gather(
        *(designer.save_design_template(wolink_entry, _text_document(), "Same") for _ in range(4))
    )
    assert sorted(item["id"] for item in results) == ["same", "same_2", "same_3", "same_4"]
    assert not list(designer.user_template_dir.glob("*.tmp"))


def test_long_names_keep_ids_valid():
    from custom_components.ble_esl.designer.design_templates import ID_PATTERN, pick_id, slug

    for name in ("9" * 50, "a" * 80, "날짜"):
        base = slug(name)
        assert ID_PATTERN.fullmatch(f"{base}_99"), name
        picked, _ = pick_id(name, None, False, {}, lambda file_name: False)
        assert ID_PATTERN.fullmatch(picked)


def test_oversized_user_file_is_skipped_unread(tmp_path, caplog):
    (tmp_path / "big.yaml").write_text("x" * (256 * 1024 + 1))
    assert load_templates(tmp_path) == {}
    assert "too large" in caplog.text


async def test_explicit_id_never_replaces_a_file_holding_another_template(
    hass, wolink_entry, tmp_path
):
    hass.config.config_dir = str(tmp_path)
    designer = hass.data[KEY]
    folder = designer.user_template_dir
    folder.mkdir(parents=True)
    (folder / "other.yaml").write_text(MINIMAL)  # defines id "sample"
    await designer.reload_design_templates()
    for overwrite in (False, True):
        with pytest.raises(HomeAssistantError, match="holds the template sample"):
            await designer.save_design_template(
                wolink_entry, _text_document(), "Other", "other", overwrite=overwrite
            )
    assert "sample" in (folder / "other.yaml").read_text()


async def test_saved_file_is_readable_and_leaves_no_temporary_file(hass, wolink_entry, tmp_path):
    hass.config.config_dir = str(tmp_path)
    designer = hass.data[KEY]
    await designer.save_design_template(wolink_entry, _text_document(), "Perm")
    assert (designer.user_template_dir / "perm.yaml").stat().st_mode & 0o777 == 0o644
    with (
        patch("custom_components.ble_esl.designer.os.replace", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        await designer.save_design_template(wolink_entry, _text_document(), "Full")
    assert not list(designer.user_template_dir.glob("*.tmp"))


def test_entity_parameters_are_checked():
    weather = TEMPLATES["weather_now"]
    values = resolve_parameters(weather, {"weather": "weather.office"}, "BWR")
    assert values["weather"] == "weather.office"
    for bad in (
        "sensor.office",
        "weather",
        "weather.",
        "Weather.home",
        "weather.a'b",
        "weather.a b",
    ):
        with pytest.raises(HomeAssistantError, match="weather"):
            resolve_parameters(weather, {"weather": bad}, "BWR")


async def test_weather_template_follows_the_chosen_entity(hass, wolink_entry):
    designer = hass.data[KEY]
    seed_entities(hass, TEMPLATES["weather_now"])
    hass.states.async_set(
        "weather.office", "rainy", {"friendly_name": "Office", "temperature": 7, "humidity": 90}
    )
    result = await designer.apply_design_template(
        wolink_entry, "weather_now", {"weather": "weather.office", "interval": "10"}
    )
    assert result["issues"] == [] and result["different_pixels"] == 0
    assert result["template"]["automation"]["triggers"] == [
        {"trigger": "time_pattern", "minutes": "/10"}
    ]
    values = [element["spec"].get("value") for element in result["elements"]]
    assert any("weather.office" in str(value) for value in values)
    with pytest.raises(HomeAssistantError, match=r"Entity not found: weather\.nowhere"):
        await designer.apply_design_template(
            wolink_entry, "weather_now", {"weather": "weather.nowhere"}
        )


WEATHER_CONDITIONS = [
    "clear-night",
    "cloudy",
    "exceptional",
    "fog",
    "hail",
    "lightning",
    "lightning-rainy",
    "partlycloudy",
    "pouring",
    "rainy",
    "snowy",
    "snowy-rainy",
    "sunny",
    "windy",
    "windy-variant",
    "unknown",
    "unavailable",
]


@pytest.mark.parametrize(("width", "height"), [(250, 128), (400, 300)])
async def test_weather_template_draws_every_condition(hass, width, height):
    weather = TEMPLATES["weather_now"]
    preset = DevicePreset("test", "test", width, height, "BWR")
    built = build(weather, width, height, "BWR")
    for condition in WEATHER_CONDITIONS:
        hass.states.async_set(
            "weather.home", condition, {"friendly_name": "Home", "temperature": 3, "humidity": 4}
        )
        elements, imported, issues = elements_from(built["payload"], preset)
        assert issues == [], condition
        original, rebuilt = stable_template_payloads(hass, imported, elements)
        assert different_pixels(hass, preset, original, rebuilt) == 0, condition


@pytest.mark.parametrize(
    ("attributes", "temperature", "humidity"),
    [
        ({}, "--", ""),
        ({"temperature": 21.5, "humidity": 55}, "21.5", "55%"),
        ({"temperature": 103.0}, "103", ""),
        ({"temperature": -12.34, "humidity": 0}, "-12.3", "0%"),
        ({"temperature": "warm"}, "--", ""),
        ({"temperature": float("nan"), "humidity": float("nan")}, "--", ""),
        ({"temperature": float("inf"), "humidity": float("-inf")}, "--", ""),
        ({"temperature": True, "humidity": True}, "--", ""),
    ],
)
async def test_weather_values_are_formatted_and_never_say_none(
    hass, attributes, temperature, humidity
):
    from custom_components.ble_esl.designer.specs import resolve_templates

    hass.states.async_set("weather.home", "sunny", attributes)
    payload = build(TEMPLATES["weather_now"], 400, 300, "BWR")["payload"]
    # Home Assistant turns a result that is only a number back into one.
    shown = [str(item["value"]) for item in resolve_templates(hass, payload, set())]
    assert temperature in shown and humidity in shown
    assert not any("None" in str(value) for value in shown)


async def test_preview_draws_a_template_at_the_tags_size(hass, wolink_entry):
    import base64
    from io import BytesIO

    from PIL import Image

    designer = hass.data[KEY]
    preset = designer.preset(wolink_entry)
    result = await designer.preview_design_template(wolink_entry, "message", {"text": "Hi"})
    assert result["png"].startswith("data:image/png;base64,")
    image = Image.open(BytesIO(base64.b64decode(result["png"].split(",", 1)[1])))
    assert image.size == (preset.width, preset.height)
    assert image.convert("L").getextrema() == (0, 255)  # something was drawn
    with pytest.raises(HomeAssistantError, match="no design template"):
        await designer.preview_design_template(wolink_entry, "nope")
    with pytest.raises(HomeAssistantError, match="ssid"):
        await designer.preview_design_template(wolink_entry, "wifi", {"ssid": "a;b"})


async def test_preview_uses_an_existing_entity_when_the_default_is_missing(hass, wolink_entry):
    designer = hass.data[KEY]
    hass.states.async_set(
        "weather.forecast_home",
        "rainy",
        {"friendly_name": "Real", "temperature": 7, "humidity": 80},
    )
    seen = []
    original = designer.hass.async_add_executor_job

    async def spy(func, *args):
        seen.append(func)
        return await original(func, *args)

    with patch.object(designer.hass, "async_add_executor_job", spy):
        result = await designer.preview_design_template(wolink_entry, "weather_now")
    assert result["png"].startswith("data:image/png")
    render = next(func for func in seen if getattr(func, "func", None) is render_image)
    payload = render.args[2]
    assert any("Real" in str(item.get("value", "")) for item in payload)


async def test_websocket_preview_requires_a_template_id(hass, wolink_entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "ble_esl/designer",
            "action": "preview_design_template",
            "entry_id": wolink_entry.entry_id,
        }
    )
    assert (await client.receive_json())["error"]["message"] == "template_id is required"


async def test_preview_refuses_what_apply_would_refuse(hass, wolink_entry):
    designer = hass.data[KEY]
    with pytest.raises(HomeAssistantError, match=r"Font not found: Missing\.ttf"):
        await designer.preview_design_template(wolink_entry, "message", {"font": "Missing.ttf"})
    with pytest.raises(HomeAssistantError, match=r"Entity not found: weather\.nowhere"):
        await designer.preview_design_template(
            wolink_entry, "weather_now", {"weather": "weather.nowhere"}
        )


def _values(rendered):
    return [item["value"] for item in rendered if "value" in item]


async def test_forecast_template_reads_the_forecast_its_automation_fetches(hass):
    built = build(TEMPLATES["weather_forecast"], 400, 300, "BWR")
    day = {"datetime": "2026-11-02T12:00:00+00:00", "condition": "rainy"}
    fc = {
        "weather.home": {
            "forecast": [
                {**day, "condition": "sunny"},
                {**day, "temperature": 18.4, "templow": 9},
                {**day, "condition": "cloudy", "temperature": 20, "templow": 11},
                {**day, "condition": "snowy", "temperature": 2, "templow": -3},
            ]
        }
    }
    values = _values(resolve_templates(hass, built["payload"], set(), {"fc": fc}))
    assert {"18°", "9°", "20°", "-3°", "weather-rainy", "weather-snowy"} <= set(values)
    # Without the fetched forecast the template still draws, with placeholders.
    blank = _values(resolve_templates(hass, built["payload"], set(), None))
    assert "--°" in blank
    # The first step of the automation fetches the forecast the write reads as `fc`.
    first = built["automation"]["actions"][0]
    assert first["action"] == "weather.get_forecasts"
    assert first["response_variable"] == "fc"
    assert first["target"] == {"entity_id": "weather.home"}


async def test_template_steps_come_before_the_write_in_a_new_automation(hass, wolink_entry):
    built = build(TEMPLATES["weather_forecast"], 296, 128, "BWR")
    preset = DevicePreset("test", "test", 296, 128, "BWR")
    elements, _, issues = elements_from(built["payload"], preset)
    assert issues == []
    result = await hass.data[KEY].automation(
        wolink_entry,
        {"version": 1, "elements": elements, "background": "white"},
        defaults=built["automation"],
    )
    actions = result["automation"]["actions"]
    assert [step["action"] for step in actions] == ["weather.get_forecasts", "ble_esl.write"]


async def _weather_forecast_service(hass):
    from homeassistant.core import SupportsResponse

    calls = []
    forecast = [
        {"datetime": "2026-11-02T12:00:00+00:00", "condition": "sunny"},
        {
            "datetime": "2026-11-03T12:00:00+00:00",
            "condition": "rainy",
            "temperature": 18.4,
            "templow": 9,
        },
        {
            "datetime": "2026-11-04T12:00:00+00:00",
            "condition": "cloudy",
            "temperature": 20,
            "templow": 11,
        },
        {
            "datetime": "2026-11-05T12:00:00+00:00",
            "condition": "snowy",
            "temperature": 2,
            "templow": -3,
        },
    ]

    async def get_forecasts(call):
        calls.append(dict(call.data))
        # Like the real service: one entity id or a list of them.
        ids = call.data["entity_id"]
        ids = [ids] if isinstance(ids, str) else ids
        return {entity: {"forecast": forecast} for entity in ids}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    return calls


async def test_applying_the_forecast_template_previews_the_real_forecast(hass, wolink_entry):
    calls = await _weather_forecast_service(hass)
    hass.states.async_set("weather.home", "sunny", {"temperature": 20})
    designer = hass.data[KEY]
    result = await designer.apply_design_template(wolink_entry, "weather_forecast")
    assert result["issues"] == [] and result["different_pixels"] == 0
    assert calls and calls[0]["type"] == "daily"
    # The preview draws the fetched forecast, not the placeholders.
    document = {"version": 1, "elements": result["elements"], "background": "white"}
    preview = await designer.preview(wolink_entry, document)
    texts = [item.get("value") for item in preview["payload"]]
    assert "18°" in texts and "weather-rainy" in texts
    # What the preview supplied never ends up in the saved payload.
    saved = await designer.export(wolink_entry, document)
    assert "fc[" in str(saved["payload_data"]) and "18°" not in str(saved["payload_data"])
    # And the payload says which step has to fetch it.
    assert saved["setup_actions"] == [
        {
            "action": "weather.get_forecasts",
            "target": {"entity_id": ["weather.home"]},
            "data": {"type": "daily"},
            "response_variable": "fc",
        }
    ]


async def test_a_new_automation_gets_the_forecast_step_once(hass, wolink_entry):
    await _weather_forecast_service(hass)
    hass.states.async_set("weather.home", "sunny", {"temperature": 20})
    designer = hass.data[KEY]
    applied = await designer.apply_design_template(wolink_entry, "weather_forecast")
    document = {"version": 1, "elements": applied["elements"], "background": "white"}
    # Without the template's own steps (e.g. the design was added to a display).
    bare = await designer.automation(wolink_entry, document)
    assert [a["action"] for a in bare["automation"]["actions"]] == [
        "weather.get_forecasts",
        "ble_esl.write",
    ]
    # With them: still one fetch, the template's.
    withtemplate = await designer.automation(
        wolink_entry, document, defaults=applied["template"]["automation"]
    )
    assert [a["action"] for a in withtemplate["automation"]["actions"]] == [
        "weather.get_forecasts",
        "ble_esl.write",
    ]


async def test_a_design_that_reads_no_forecast_needs_no_step(hass, wolink_entry):
    saved = await hass.data[KEY].export(
        wolink_entry, {"version": 1, "elements": [], "background": "white"}
    )
    assert saved["setup_actions"] == []


def test_the_forecast_scan_reads_a_template_the_way_it_runs():
    from custom_components.ble_esl.designer import forecast_entities

    assert forecast_entities({"v": "{{ fc ['weather.a'].forecast }}"}) == ["weather.a"]
    assert forecast_entities({"v": '{{ fc["weather.b_2"] }}'}) == ["weather.b_2"]
    # Not the variable the forecast step sets.
    assert forecast_entities({"v": "{{ states.fc['weather.z'] }} {{ my_fc['weather.y'] }}"}) == []


async def test_a_failing_forecast_provider_never_stops_a_preview(hass, wolink_entry):
    from homeassistant.core import SupportsResponse

    calls = []

    async def get_forecasts(call):
        calls.append(1)
        raise TimeoutError("provider is down")

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    hass.states.async_set("weather.home", "sunny", {"temperature": 20})
    designer = hass.data[KEY]
    applied = await designer.apply_design_template(wolink_entry, "weather_forecast")
    document = {"version": 1, "elements": applied["elements"], "background": "white"}
    preview = await designer.preview(wolink_entry, document)
    assert "--°" in [item.get("value") for item in preview["payload"]]
    saved = await designer.export(wolink_entry, document)
    assert saved["validation_errors"] == []
    # A failure is remembered for a while, not asked again at every render.
    assert len(calls) == 1


def test_a_step_for_other_entities_is_not_taken_for_the_one_the_payload_needs():
    from custom_components.ble_esl.designer.export import automation_draft

    def step(*entities):
        return {
            "action": "weather.get_forecasts",
            "target": {"entity_id": list(entities)},
            "data": {"type": "daily"},
            "response_variable": "fc",
        }

    exported = {
        "service": "action: ble_esl.write\ndata:\n  payload: []\n",
        "setup_actions": [step("weather.home", "weather.office")],
    }
    # The template's step covers only one of them: the payload's covers both.
    draft = automation_draft(exported, "x", {"actions": [step("weather.home")]})
    assert [a["action"] for a in draft["actions"]] == [
        "weather.get_forecasts",
        "weather.get_forecasts",
        "ble_esl.write",
    ]
    # One that already covers them all is enough.
    draft = automation_draft(exported, "x", {"actions": [step("weather.office", "weather.home")]})
    assert [a["action"] for a in draft["actions"]] == ["weather.get_forecasts", "ble_esl.write"]


async def test_a_failed_preview_fetch_does_not_hide_the_forecast_from_a_write(hass, wolink_entry):
    from custom_components.ble_esl.designer import forecast_entities  # noqa: F401

    designer = hass.data[KEY]
    designer.forecast_failed[("weather.home", "daily")] = __import__("time").monotonic()
    # The preview skips a provider that just failed ...
    assert await designer.forecast_variable({"v": "{{ fc['weather.home'] }}"}, {}) == {}
    # ... and what a write reads is untouched by it.
    assert ("weather.home", "daily") not in designer.forecast_cache


def _shown(hass, template_id, width=400, height=300, given=None):
    """What a template's payload says once Home Assistant has rendered its templates."""
    built = build(TEMPLATES[template_id], width, height, "BWR", given)
    return resolve_templates(hass, built["payload"], set())


def _texts(rendered):
    return [str(item["value"]) for item in rendered if item["type"] == "text_fit"]


@pytest.mark.parametrize(
    ("state", "shown"),
    [
        ("23.456", "23.5"),
        ("20.0", "20"),
        ("100", "100"),
        ("-0.04", "0"),
        ("unavailable", "unavailable"),
        ("nan", "nan"),
    ],
)
async def test_sensor_card_formats_the_value(hass, state, shown):
    hass.states.async_set(
        "sensor.temperature", state, {"friendly_name": "Room", "unit_of_measurement": "°C"}
    )
    texts = _texts(_shown(hass, "sensor_card"))
    assert texts == ["Room", shown, "°C"]


async def test_sensor_card_title_and_missing_entity(hass):
    hass.states.async_set("sensor.temperature", "5", {"friendly_name": "Room"})
    texts = _texts(_shown(hass, "sensor_card", given={"title": "Kitchen"}))
    assert texts == ["Kitchen", "5", ""]
    # An entity that does not exist leaves empty text, never "None".
    texts = _texts(_shown(hass, "sensor_card", given={"sensor": "sensor.nowhere"}))
    assert texts == ["", "unknown", ""]


async def test_calendar_next_shows_the_event_its_times_and_place(hass):
    event = {
        "message": "Dentist",
        "all_day": False,
        "start_time": "2026-11-02 14:30:00",
        "location": "Seoul",
    }
    hass.states.async_set("calendar.home", "on", event)
    texts = _texts(_shown(hass, "calendar_next", given={"date_format": "%d.%m."}))
    assert texts == ["Next event", "Dentist", "02.11. 14:30", "Seoul"]
    hass.states.async_set("calendar.home", "on", {**event, "all_day": True})
    assert _texts(_shown(hass, "calendar_next"))[2] == "11/02"


async def test_calendar_next_without_an_event_says_so(hass):
    hass.states.async_set("calendar.home", "off", {"friendly_name": "Home"})
    texts = _texts(_shown(hass, "calendar_next", given={"empty_text": "Free"}))
    assert texts == ["Next event", "Free", "", ""]
    hass.states.async_set("calendar.home", "off", {"message": "x", "start_time": "garbage"})
    assert _texts(_shown(hass, "calendar_next"))[2] == ""


def _progress_bar(rendered):
    return next(item for item in rendered if item["type"] == "progress_bar")


@pytest.mark.parametrize(
    ("state", "percent"),
    [("63.4", 63), ("0", 0), ("150", 100), ("-5", 0), ("unavailable", 0), ("nan", 0)],
)
async def test_print_progress_stays_between_zero_and_a_hundred(hass, state, percent):
    hass.states.async_set("sensor.print_progress", state)
    rendered = _shown(hass, "print_progress")
    assert _progress_bar(rendered)["progress"] == percent
    assert f"{percent}%" in _texts(rendered)


async def test_print_progress_shows_status_and_finish_time(hass):
    hass.states.async_set("sensor.print_progress", "10")
    hass.states.async_set("sensor.print_status", "running")
    hass.states.async_set("sensor.print_end_time", "2026-11-01T18:45:00+00:00")
    texts = _texts(_shown(hass, "print_progress", given={"time_format": "%Y"}))
    assert texts[-2:] == ["running", "Finish 2026"]
    hass.states.async_set("sensor.print_end_time", "unavailable")
    assert _texts(_shown(hass, "print_progress"))[-1] == "Finish --"


@pytest.mark.parametrize(
    ("days", "shown", "color"),
    [
        (30, "D-30", "black"),
        (7, "D-7", "red"),
        (1, "D-1", "red"),
        (0, "D-Day", "red"),
        (-3, "D+3", "red"),
    ],
)
async def test_countdown_counts_the_days_and_warns_when_close(hass, days, shown, color):
    from datetime import date, timedelta

    from homeassistant.util import dt as dt_util

    target = (dt_util.now().date() + timedelta(days=days)).isoformat()
    assert date.fromisoformat(target)
    rendered = _shown(hass, "countdown", given={"target": target})
    assert _texts(rendered)[1] == shown
    assert rendered[1]["color"] == color


@pytest.mark.parametrize("target", ["not a date", "2026-13-45", "01/01/2027"])
async def test_countdown_with_a_bad_date_shows_dashes(hass, target):
    rendered = _shown(hass, "countdown", given={"target": target})
    assert _texts(rendered)[1] == "--"
    assert rendered[1]["color"] == "black"


async def test_date_weather_shows_the_day_and_the_weather(hass):
    hass.states.async_set("weather.home", "sunny", {"temperature": 21.5, "temperature_unit": "°C"})
    for size in ((250, 128), (400, 300)):
        rendered = _shown(hass, "date_weather", *size, given={"weekdays": "a,b,c,d,e,f,g"})
        values = [str(item["value"]) for item in rendered if "value" in item]
        assert "21.5°C" in values
        assert "weather-sunny" in values
        assert not any("None" in value for value in values)
    # Too few weekday names leave the weekday empty instead of failing.
    from homeassistant.util import dt as dt_util

    short = _texts(_shown(hass, "date_weather", given={"weekdays": "a"}))
    assert short[1] == ("a" if dt_util.now().weekday() == 0 else "")
    hass.states.async_set("weather.home", "unavailable", {})
    assert "--" in _texts(_shown(hass, "date_weather"))


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
async def test_every_automation_option_is_a_valid_home_assistant_automation(hass, template_id):
    template = TEMPLATES[template_id]
    seed_entities(hass, template)
    choices = {
        name: parameter["options"]
        for name, parameter in template["parameters"].items()
        if parameter["type"] == "select" and parameter["group"] == "automation"
    }
    for name, options in choices.items():
        for option in options:
            built = build(template, 250, 128, "BWR", {name: option})
            config = {
                **built["automation"],
                "alias": "x",
                "actions": [
                    *built["automation"].get("actions", []),
                    {"action": "ble_esl.write", "data": {"payload": built["payload"]}},
                ],
            }
            assert await async_validate_config_item(hass, "x", config), (name, option)


async def test_outdoor_weather_reads_dated_forecasts_and_keeps_missing_slots_blank(hass):
    from datetime import timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = dt_util.start_of_local_day()

    def date(hour):
        return (today + timedelta(hours=hour)).isoformat()

    hass.states.async_set(
        "weather.home",
        "cloudy",
        {
            "temperature": -2,
            "temperature_unit": "°C",
            "apparent_temperature": -5,
            "wind_speed": 18,
            "wind_speed_unit": "km/h",
        },
    )
    hass.states.async_set("sensor.snow_today", "2.5", {"unit_of_measurement": "cm"})
    hass.states.async_set("sun.sun", "above_horizon", {"next_setting": date(17)})
    variables = {
        "fc": {
            "weather.home": {
                "forecast": [
                    {"datetime": date(-12), "temperature": 99, "templow": 98},
                    {"datetime": date(12), "condition": "snowy", "temperature": 2, "templow": -5},
                    {"datetime": date(36), "condition": "sunny", "temperature": 5, "templow": -2},
                ]
            }
        },
        "fc_hourly": {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": date(7),
                        "condition": "snowy",
                        "temperature": -3,
                        "precipitation_probability": 70,
                    },
                    {
                        "datetime": date(8),
                        "condition": "snowy",
                        "temperature": -2,
                        "precipitation_probability": 80,
                    },
                    {
                        "datetime": date(10),
                        "condition": "cloudy",
                        "temperature": 0,
                        "precipitation_probability": 0,
                    },
                    {"datetime": date(19), "condition": "cloudy", "temperature": -1},
                ]
            }
        },
    }
    built = build(
        TEMPLATES["weather_outdoor"], 960, 640, "BWR", {"snowfall_sensor": "sensor.snow_today"}
    )
    with freeze_time(today + timedelta(hours=6), real_asyncio=True):
        rendered = resolve_templates(hass, built["payload"], set(), variables)
    values = _values(rendered)
    assert {
        "-2°C",
        "-5°C",
        "18 km/h",
        "최저 -5° / 최고 2°",
        "07~08시 눈 80%",
        "미끄럼 주의",
        "weather-snowy",
        "0%",
        "예상 적설",
        "2.5 cm",
        "17:00",
    } <= set(values)
    assert "99°" not in values and "—" in values
    series = [item["values"] for item in rendered if item["type"] == "sparkline"]
    assert series == [[-3.0, 0.0], [], [], [], []]


@pytest.mark.parametrize(
    ("hourly", "daily", "expected"),
    [
        ([(7, "cloudy", 90)], {}, "07시 강수 90%"),
        ([(7, "cloudy", 20)], {}, "강수 20%"),
        ([(7, "sunny", 0)], {}, "예보 정보 없음"),
        ([(7, "sunny", 0)], {"condition": "rainy", "precipitation_probability": 60}, "오늘 비 60%"),
        ([(hour, "sunny", 0) for hour in range(6, 24)], {"condition": "rainy"}, "비·눈 예보 없음"),
    ],
)
async def test_outdoor_weather_uses_partial_forecast_cautiously(hass, hourly, daily, expected):
    from datetime import timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = dt_util.start_of_local_day()

    def at(hour):
        return (today + timedelta(hours=hour)).isoformat()

    forecasts = {
        "fc_hourly": {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": at(hour),
                        "condition": condition,
                        "precipitation_probability": chance,
                    }
                    for hour, condition, chance in hourly
                ]
            },
        },
        "fc": {"weather.home": {"forecast": [{"datetime": at(12), **daily}]}},
    }
    built = build(TEMPLATES["weather_outdoor"], 212, 104, "BWR")
    with freeze_time(today + timedelta(hours=6), real_asyncio=True):
        values = _values(resolve_templates(hass, built["payload"], set(), forecasts))
    assert expected in values


@pytest.mark.parametrize(("width", "height"), [(400, 300), (300, 400), (800, 480)])
def test_outdoor_weather_weekly_temperatures_stay_in_their_columns(width, height):
    from itertools import pairwise

    items = build(TEMPLATES["weather_outdoor"], width, height, "BWR")["payload"]
    ranges = [
        item for item in items if item["type"] == "text_fit" and "row.templow" in item["value"]
    ]
    assert len(ranges) == 7
    assert all(item["max_lines"] == 1 and item["fit"] == "shrink" for item in ranges)
    assert all(a["x"] + a["width"] < b["x"] for a, b in pairwise(ranges))


async def test_outdoor_weather_automation_fetches_both_forecasts_once(hass, wolink_entry):
    from homeassistant.core import SupportsResponse

    calls = []

    async def get_forecasts(call):
        calls.append(call.data["type"])
        if call.data["type"] == "hourly":
            raise HomeAssistantError("Hourly data unavailable")
        return {"weather.home": {"forecast": []}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    seed_entities(hass, TEMPLATES["weather_outdoor"])
    designer = hass.data[KEY]
    applied = await designer.apply_design_template(wolink_entry, "weather_outdoor")
    assert applied["issues"] == [] and applied["different_pixels"] == 0
    document = {"version": 1, "elements": applied["elements"], "background": "white"}
    preview = await designer.preview(wolink_entry, document)
    assert "예보 정보 없음" in _values(preview["payload"])
    # The failed hourly lookup is cooled down independently of the daily response.
    assert calls == ["daily", "hourly"]
    for defaults in (None, applied["template"]["automation"]):
        result = await designer.automation(wolink_entry, document, defaults=defaults)
        actions = result["automation"]["actions"]
        assert [action["action"] for action in actions] == [
            "weather.get_forecasts",
            "weather.get_forecasts",
            "ble_esl.write",
        ]
        assert [step["data"]["type"] for step in actions[:2]] == ["daily", "hourly"]
        assert all(step["continue_on_error"] for step in actions[:2])


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
@pytest.mark.parametrize("size", sorted(TEMPLATES["weather_outdoor"]["layouts"]))
def test_bundled_templates_import_at_all_gallery_sizes(template_id, size):
    width, height = map(int, size.split("x"))
    preset = DevicePreset("gallery", "gallery", width, height, "BWR")
    built = build(TEMPLATES[template_id], width, height, "BWR")
    assert built["layout"] == size and not built["scaled"]
    elements, _, issues = elements_from(built["payload"], preset)
    assert issues == []
    assert len(elements) == len(built["payload"])


async def test_large_calendar_adds_end_time_and_optional_details(hass):
    event = {
        "message": "Project review",
        "start_time": "2026-11-02 14:30:00",
        "end_time": "2026-11-02 16:00:00",
        "location": "Studio 2",
        "description": "Bring the drawings.",
    }
    hass.states.async_set("calendar.home", "on", event)
    assert {"11/02 14:30 - 16:00", "Bring the drawings."} <= set(
        _texts(_shown(hass, "calendar_next", 800, 480))
    )
    hass.states.async_set("calendar.home", "on", {**event, "all_day": True})
    assert "11/02" in _texts(_shown(hass, "calendar_next", 480, 800))
    assert not any("16:00" in value for value in _texts(_shown(hass, "calendar_next", 480, 800)))


async def test_large_forecast_uses_seven_days_with_precipitation(hass):
    forecast = [
        {
            "temperature": index + 10,
            "templow": index + 3,
            "condition": "partlycloudy",
            "precipitation_probability": index * 10,
        }
        for index in range(7)
    ]
    built = build(TEMPLATES["weather_forecast"], 960, 640, "BW")
    shown = _texts(
        resolve_templates(
            hass, built["payload"], set(), {"fc": {"weather.home": {"forecast": forecast}}}
        )
    )
    assert {"3° / 10°", "9° / 16°", "0%", "60%"} <= set(shown)


async def test_large_sensor_optional_second_reading_and_compact_message(hass):
    hass.states.async_set("sensor.temperature", "24", {"unit_of_measurement": "°C"})
    hass.states.async_set(
        "sensor.humidity", "47", {"friendly_name": "Humidity", "unit_of_measurement": "%"}
    )
    values = _texts(_shown(hass, "sensor_card", 800, 480, {"secondary_sensor": "sensor.humidity"}))
    assert {"24", "°C", "Humidity", "47 %"} <= set(values)
    given = {"text": "Welcome", "subtitle": "Front desk"}
    assert _texts(_shown(hass, "message", 296, 128, given)) == ["Welcome"]
    assert _texts(_shown(hass, "message", 800, 480, given)) == ["Welcome", "Front desk"]


async def test_large_wifi_does_not_print_a_hidden_network_name(hass):
    given = {"ssid": "Private network", "security": "SAE", "hidden": "true"}
    layout = _shown(hass, "wifi", 480, 800, given)
    assert "Private network" not in _texts(layout)
    assert "WPA3" in _texts(layout)
    assert "S:Private network;" in next(item["data"] for item in layout if item["type"] == "qrcode")


@pytest.mark.parametrize(
    ("short", "long", "detail"), [(300, 400, False), (480, 648, True), (480, 800, True)]
)
async def test_gallery_information_tier_is_preserved_when_rotating(hass, short, long, detail):
    hass.states.async_set("sensor.temperature", "24", {"unit_of_measurement": "°C"})
    hass.states.async_set(
        "sensor.humidity", "47", {"friendly_name": "Humidity", "unit_of_measurement": "%"}
    )
    options = {"secondary_sensor": "sensor.humidity"}
    for width, height in ((short, long), (long, short)):
        values = _texts(_shown(hass, "sensor_card", width, height, options))
        assert ("47 %" in values) is detail


def test_gallery_parses_bundled_layouts_once_but_loads_user_edits(tmp_path):
    from custom_components.ble_esl.designer import design_templates as module

    module._bundled_templates.cache_clear()
    path = tmp_path / "sample.yaml"
    path.write_text(MINIMAL, encoding="utf-8")
    try:
        with patch.object(module, "load_templates", wraps=module.load_templates) as parse:
            originals = module.load_all(tmp_path)
            originals["date"]["layouts"].clear()
            path.write_text(MINIMAL.replace("Sample", "Updated"), encoding="utf-8")
            refreshed = module.load_all(tmp_path)
            assert refreshed["date"]["layouts"]
            assert refreshed["sample"]["name"] == "Updated"
            assert [call.args for call in parse.call_args_list] == [(), (tmp_path,), (tmp_path,)]
    finally:
        module._bundled_templates.cache_clear()


async def test_compact_weather_keeps_humidity_and_update_clock_in_both_orientations(hass):
    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    now = dt_util.now().replace(hour=7, minute=15)
    hass.states.async_set(
        "weather.home", "sunny", {"humidity": 55, "temperature": 15, "temperature_unit": "°C"}
    )
    with freeze_time(now, real_asyncio=True):
        for size in ((296, 128), (128, 296), (300, 400)):
            assert {"55%", "07:15"} <= set(_texts(_shown(hass, "weather_now", *size)))


async def test_date_shows_week_bar_from_4_2_inches(hass):
    from datetime import datetime

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    now = datetime(2026, 11, 19, 9, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with freeze_time(now, real_asyncio=True):
        for size in ((400, 300), (300, 400)):
            texts = _texts(
                _shown(hass, "date", *size, given={"weekdays": "Mon,Tue,Wed,Thu,Fri,Sat,Sun"})
            )
            assert any("ISO W" in t for t in texts)
            assert {"Mon", "Sun", "16", "22"} <= set(texts)


async def test_weather_forecast_4_2_shows_5_days_and_skips_yesterday_when_current(hass):
    from datetime import datetime, timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = datetime(2026, 11, 19, 9, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    fc = {
        "weather.home": {
            "forecast": [
                {
                    "datetime": (today + timedelta(days=offset)).isoformat(),
                    "condition": "sunny",
                    "temperature": 99 if offset == -1 else 10 + offset,
                    "templow": 98 if offset == -1 else 2 + offset,
                    "precipitation_probability": 25 if offset >= 1 else 0,
                }
                for offset in range(-1, 6)
            ]
        }
    }
    with freeze_time(today, real_asyncio=True):
        built = build(TEMPLATES["weather_forecast"], 400, 300, "BWR")
        vals = _values(resolve_templates(hass, built["payload"], set(), {"fc": fc}))
        assert "99°" not in vals and "98°" not in vals
        assert {"11°", "3°", "15°", "7°", "25%"} <= set(vals)


async def test_weather_forecast_250x128_and_non_numeric_edge_cases(hass):
    from datetime import datetime, timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = datetime(2026, 11, 19, 9, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    fc_yesterday = {
        "weather.home": {
            "forecast": [
                {
                    "datetime": (today - timedelta(days=1)).isoformat(),
                    "condition": "sunny",
                    "temperature": 99,
                    "templow": 98,
                },
                {
                    "datetime": today.isoformat(),
                    "condition": "cloudy",
                    "temperature": 12,
                    "templow": 4,
                },
                {
                    "datetime": (today + timedelta(days=1)).isoformat(),
                    "condition": "rainy",
                    "temperature": 15,
                    "templow": 7,
                },
            ]
        }
    }
    with freeze_time(today, real_asyncio=True):
        vals_250 = _values(
            resolve_templates(
                hass,
                build(TEMPLATES["weather_forecast"], 250, 128, "BWR")["payload"],
                set(),
                {"fc": fc_yesterday},
            )
        )
        assert "99°" not in vals_250 and "98°" not in vals_250
        assert {"15°", "7°", "weather-rainy"} <= set(vals_250)

        # Edge cases: NaN/inf/bool temperatures, invalid/None datetime, and None forecast entry.
        edge_fc = {
            "weather.home": {
                "forecast": [
                    {"datetime": None, "temperature": True, "templow": False},
                    {
                        "datetime": "not-a-date",
                        "temperature": float("nan"),
                        "templow": float("inf"),
                    },
                    {"datetime": today.isoformat(), "temperature": 10, "templow": 2},
                ]
            }
        }
        for size in ((250, 128), (800, 480)):
            vals_edge = _values(
                resolve_templates(
                    hass,
                    build(TEMPLATES["weather_forecast"], *size, "BWR")["payload"],
                    set(),
                    {"fc": edge_fc},
                )
            )
            assert "--°" in vals_edge or "--° / --°" in vals_edge
            assert "1°" not in vals_edge and "0°" not in vals_edge

        vals_none = _values(
            resolve_templates(
                hass,
                build(TEMPLATES["weather_forecast"], 250, 128, "BWR")["payload"],
                set(),
                {"fc": {"weather.home": None}},
            )
        )
        assert "--°" in vals_none


async def test_sensor_card_warn_above_highlights_and_respects_bw_fallback(hass):
    hass.states.async_set("sensor.temperature", "32.4", {"unit_of_measurement": "°C"})
    rendered_bwr = resolve_templates(
        hass,
        build(TEMPLATES["sensor_card"], 400, 300, "BWR", {"warn_above": "30"})["payload"],
        set(),
    )
    assert next(item for item in rendered_bwr if str(item.get("value")) == "32.4")["color"] == "red"

    rendered_bw = resolve_templates(
        hass,
        build(TEMPLATES["sensor_card"], 400, 300, "BW", {"warn_above": "30"})["payload"],
        set(),
    )
    assert (
        next(item for item in rendered_bw if str(item.get("value")) == "32.4")["color"] == "black"
    )

    rendered_ok = resolve_templates(
        hass,
        build(TEMPLATES["sensor_card"], 400, 300, "BWR", {"warn_above": "35"})["payload"],
        set(),
    )
    assert (
        next(item for item in rendered_ok if str(item.get("value")) == "32.4")["color"] == "black"
    )

    # White warn_color stays visible (black), negative thresholds work, and non-numeric thresholds/states do not crash.
    rendered_white = resolve_templates(
        hass,
        build(
            TEMPLATES["sensor_card"], 400, 300, "BWRY", {"warn_above": "-5", "warn_color": "white"}
        )["payload"],
        set(),
    )
    assert (
        next(item for item in rendered_white if str(item.get("value")) == "32.4")["color"]
        == "black"
    )

    for warn_above in ("", "abc", "nan", "inf"):
        rendered_safe = resolve_templates(
            hass,
            build(TEMPLATES["sensor_card"], 400, 300, "BWR", {"warn_above": warn_above})["payload"],
            set(),
        )
        assert (
            next(item for item in rendered_safe if str(item.get("value")) == "32.4")["color"]
            == "black"
        )

    for bad_state in ("inf", "nan", "unavailable"):
        hass.states.async_set("sensor.temperature", bad_state, {"unit_of_measurement": "°C"})
        rendered_bad = resolve_templates(
            hass,
            build(TEMPLATES["sensor_card"], 400, 300, "BWR", {"warn_above": "30"})["payload"],
            set(),
        )
        assert (
            next(item for item in rendered_bad if str(item.get("value")) == bad_state)["color"]
            == "black"
        )


async def test_print_progress_shows_optional_nozzle_and_bed_temps_on_large_tags(hass):
    hass.states.async_set("sensor.print_progress", "55")
    hass.states.async_set("sensor.print_status", "printing")
    hass.states.async_set("sensor.print_end_time", "2026-11-19T18:45:00+00:00")
    hass.states.async_set("sensor.nozzle_temp", "210.4")
    hass.states.async_set("sensor.bed_temp", "60.2")
    texts_with = _texts(
        _shown(
            hass,
            "print_progress",
            800,
            480,
            {"nozzle_sensor": "sensor.nozzle_temp", "bed_sensor": "sensor.bed_temp"},
        )
    )
    assert "210° / 60°" in texts_with
    assert "—" in _texts(_shown(hass, "print_progress", 800, 480))

    # Single sensor supplied and non-sensor IDs.
    assert "210° / —" in _texts(
        _shown(hass, "print_progress", 800, 480, {"nozzle_sensor": "sensor.nozzle_temp"})
    )
    assert "—" in _texts(
        _shown(hass, "print_progress", 800, 480, {"nozzle_sensor": "binary_sensor.door"})
    )

    # Non-numeric sensor states (unavailable, nan, inf) never raise OverflowError.
    for bad in ("unavailable", "nan", "inf"):
        hass.states.async_set("sensor.nozzle_temp", bad)
        hass.states.async_set("sensor.bed_temp", bad)
        assert "— / —" in _texts(
            _shown(
                hass,
                "print_progress",
                800,
                480,
                {"nozzle_sensor": "sensor.nozzle_temp", "bed_sensor": "sensor.bed_temp"},
            )
        )


async def test_calendar_next_renders_upcoming_events_on_large_tags(hass, wolink_entry):
    from homeassistant.core import SupportsResponse

    hass.states.async_set("calendar.home", "on", {"message": "Fallback"})
    events = [
        {
            "summary": "Standup",
            "start": "2026-11-22T09:30:00+09:00",
            "end": "2026-11-22T10:00:00+09:00",
            "location": "Room A",
        },
        {
            "summary": "Design Review",
            "start": "2026-11-22T14:00:00+09:00",
            "end": "2026-11-22T15:00:00+09:00",
        },
        {
            "summary": "Release Day",
            "start": "2026-11-23",
            "end": "2026-11-25",
        },
    ]
    built = build(TEMPLATES["calendar_next"], 800, 480, "BWR")
    rendered = resolve_templates(
        hass, built["payload"], set(), {"events": {"calendar.home": {"events": events}}}
    )
    texts = _texts(rendered)
    assert "Standup" in texts and "Room A" in texts
    assert any("Design Review" in t for t in texts)
    assert any("Release Day" in t for t in texts)
    # Multi-line regression guard: event 2 and 3 sit in separate single-line boxes and render cleanly.
    assert not any("Design Review" in t and "Release Day" in t for t in texts)
    render_image(hass, DevicePreset("test", "test", 800, 480, "BWR"), rendered)

    # Multi-day all-day event formatting (exclusive end 11/25 -> 11/23 - 11/24 without 00:00) and mixed tz bounds.
    all_day_texts = _texts(
        resolve_templates(
            hass,
            built["payload"],
            set(),
            {"events": {"calendar.home": {"events": [events[2]]}}},
        )
    )
    assert "11/23 - 11/24" in all_day_texts and not any("00:00" in t for t in all_day_texts)

    mixed_tz = [{"summary": "Mixed", "start": "2026-11-23", "end": "2026-11-23T12:00:00+09:00"}]
    mixed_texts = _texts(
        resolve_templates(
            hass,
            built["payload"],
            set(),
            {"events": {"calendar.home": {"events": mixed_tz}}},
        )
    )
    assert "Mixed" in mixed_texts and "11/23" in mixed_texts

    # Empty events fall back to calendar entity attributes.
    assert "Fallback" in _texts(
        resolve_templates(
            hass, built["payload"], set(), {"events": {"calendar.home": {"events": []}}}
        )
    )

    # Designer preview, export setup_actions, and automation draft support calendar.get_events on 5.8"+,
    # while small <480px layouts omit it.
    small_elements, _, _ = elements_from(
        build(TEMPLATES["calendar_next"], 250, 128, "BWR")["payload"],
        DevicePreset("small", "small", 250, 128, "BWR"),
    )
    small_saved = await hass.data[KEY].export(
        wolink_entry, {"version": 1, "elements": small_elements, "background": "white"}
    )
    assert small_saved["setup_actions"] == []

    calls = []

    async def get_events(call):
        calls.append(dict(call.data))
        ids = call.data["entity_id"]
        ids = [ids] if isinstance(ids, str) else ids
        return {entity: {"events": events} for entity in ids}

    hass.services.async_register(
        "calendar", "get_events", get_events, supports_response=SupportsResponse.ONLY
    )
    designer = hass.data[KEY]
    large_elements, _, issues = elements_from(
        built["payload"], DevicePreset("large", "large", 800, 480, "BWR")
    )
    assert issues == []
    large_doc = {"version": 1, "elements": large_elements, "background": "white"}
    preview = await designer.preview(wolink_entry, large_doc)
    assert "Standup" in _texts(preview["payload"]) and calls
    saved = await designer.export(wolink_entry, large_doc)
    assert saved["setup_actions"] == [
        {
            "action": "calendar.get_events",
            "target": {"entity_id": ["calendar.home"]},
            "data": {"duration": {"days": 7}},
            "response_variable": "events",
            "continue_on_error": True,
        }
    ]
    auto = await designer.automation(wolink_entry, large_doc)
    assert [step["action"] for step in auto["automation"]["actions"]] == [
        "calendar.get_events",
        "ble_esl.write",
    ]
    # Re-applying with defaults already containing calendar.get_events does not duplicate the step.
    auto_dedup = await designer.automation(
        wolink_entry, large_doc, defaults={"actions": saved["setup_actions"]}
    )
    assert [step["action"] for step in auto_dedup["automation"]["actions"]] == [
        "calendar.get_events",
        "ble_esl.write",
    ]


def test_demo_payload_variables_supports_calendar_get_events():
    from scripts.designer_demo import demo_payload_variables

    payload = build(TEMPLATES["calendar_next"], 800, 480, "BWR")["payload"]
    variables = demo_payload_variables(payload, {})
    assert "events" in variables
    assert variables["events"]["calendar.home"]["events"]
    assert all(
        "summary" in ev and "start" in ev for ev in variables["events"]["calendar.home"]["events"]
    )


@pytest.mark.parametrize(
    ("condition", "daily_row", "short_alert", "long_alert"),
    [
        (
            "rainy",
            {"temperature": 13, "templow": 6, "precipitation_probability": 80, "precipitation": 12},
            "우산 80%",
            "우산 챙기기",
        ),
        (
            "snowy",
            {"temperature": 1, "templow": -6, "precipitation_probability": 70, "precipitation": 3},
            "눈 70%",
            "눈길 주의",
        ),
        (
            "sunny",
            {"temperature": 18, "templow": 4, "precipitation_probability": 10},
            "일교차 14°",
            "일교차 주의",
        ),
    ],
)
async def test_commute_weather_under_4_inches_alerts_and_metrics(
    hass, condition, daily_row, short_alert, long_alert
):
    from datetime import timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = dt_util.start_of_local_day() + timedelta(hours=7, minutes=30)
    hass.states.async_set(
        "weather.home",
        condition,
        {
            "temperature": 11,
            "temperature_unit": "°C",
            "apparent_temperature": 9,
            "humidity": 82,
            "wind_speed": 4.2,
            "wind_speed_unit": "m/s",
        },
    )
    variables = {
        "fc": {
            "weather.home": {
                "forecast": [{"datetime": (today + timedelta(hours=4)).isoformat(), **daily_row}]
            }
        }
    }
    with freeze_time(today, real_asyncio=True):
        built_250 = build(TEMPLATES["weather_commute"], 250, 128, "BWR")
        vals_250 = _values(resolve_templates(hass, built_250["payload"], set(), variables))
        assert {short_alert, f"{daily_row['templow']}°", f"{daily_row['temperature']}°"} <= set(
            vals_250
        )

        built_296 = build(TEMPLATES["weather_commute"], 296, 128, "BWR")
        vals_296 = _values(resolve_templates(hass, built_296["payload"], set(), variables))
        assert {
            short_alert,
            long_alert,
            f"{daily_row['templow']}° / {daily_row['temperature']}°",
        } <= set(vals_296)

        built_384 = build(TEMPLATES["weather_commute"], 384, 184, "BWR")
        vals_384 = _values(resolve_templates(hass, built_384["payload"], set(), variables))
        assert {
            long_alert,
            f"{daily_row['templow']}°",
            f"{daily_row['temperature']}°",
        } <= set(vals_384)
        assert any("강수 " in str(v) or "일교차 " in str(v) for v in vals_384)


async def test_commute_weather_4_inches_and_above_shows_weekly_forecast(hass):
    from datetime import datetime, timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    thursday = datetime(2026, 11, 19, 7, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    hass.states.async_set(
        "weather.home",
        "rainy",
        {
            "temperature": 11,
            "temperature_unit": "°C",
            "apparent_temperature": 9,
            "humidity": 82,
            "wind_speed": 4.2,
            "wind_speed_unit": "m/s",
        },
    )
    daily = [
        {
            "datetime": (thursday + timedelta(days=offset, hours=5)).isoformat(),
            "condition": "rainy" if offset in (0, 4) else "sunny",
            "temperature": 13 + offset,
            "templow": 6 + offset,
            "precipitation_probability": 80 if offset == 0 else (75 if offset == 4 else 10),
            "precipitation": 12 if offset == 0 else 0,
        }
        for offset in range(8)
    ]
    variables = {"fc": {"weather.home": {"forecast": daily}}}

    with freeze_time(thursday, real_asyncio=True):
        rendered_42 = resolve_templates(
            hass, build(TEMPLATES["weather_commute"], 400, 300, "BWR")["payload"], set(), variables
        )
        vals_42 = _values(rendered_42)
        assert {"우산 챙기기", "금", "토", "일", "월", "화", "75%"} <= set(vals_42)
        assert "수" not in vals_42
        weekend_items = [item for item in rendered_42 if item.get("value") in ("토", "일")]
        assert weekend_items and all(item["color"] == "red" for item in weekend_items)

        vals_75 = _values(
            resolve_templates(
                hass,
                build(TEMPLATES["weather_commute"], 800, 480, "BWR")["payload"],
                set(),
                variables,
            )
        )
        assert {"• 우산 필수 (80%)", "주간 비·눈: 월(75%)", "수"} <= set(vals_75)
        assert "목" not in vals_75

        vals_102 = _values(
            resolve_templates(
                hass,
                build(TEMPLATES["weather_commute"], 960, 640, "BWR")["payload"],
                set(),
                variables,
            )
        )
        assert {"7일 주간 예보", "목", "주간 비·눈: 월(75%)"} <= set(vals_102)


async def test_commute_weather_handles_unavailable_non_numeric_and_stale_forecasts(hass):
    from datetime import timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = dt_util.start_of_local_day() + timedelta(hours=7, minutes=30)
    hass.states.async_set(
        "weather.home",
        "unavailable",
        {
            "temperature": float("nan"),
            "temperature_unit": "°C",
            "apparent_temperature": True,
            "humidity": "unknown",
            "wind_speed": float("inf"),
        },
    )
    stale_fc = {
        "fc": {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": (today - timedelta(days=1)).isoformat(),
                        "temperature": 99,
                        "templow": 98,
                        "condition": "sunny",
                    }
                ]
            }
        }
    }
    with freeze_time(today, real_asyncio=True):
        for variables in ({}, stale_fc):
            built = build(TEMPLATES["weather_commute"], 296, 128, "BWR")
            vals = _values(resolve_templates(hass, built["payload"], set(), variables))
            assert {"예보 정보 없음", "예보 없음"} <= set(vals)
            assert "99°" not in vals and "우산 불필요" not in vals
            built_384 = build(TEMPLATES["weather_commute"], 384, 184, "BWR")
            vals_384 = _values(resolve_templates(hass, built_384["payload"], set(), variables))
            assert {"예보 정보 없음", "예보 대기 중"} <= set(vals_384)

        built_42 = build(TEMPLATES["weather_commute"], 400, 300, "BWR")
        vals_42 = _values(resolve_templates(hass, built_42["payload"], set(), stale_fc))
        assert "예보 정보 없음" in vals_42
        assert "weather-cloudy-alert" in vals_42
        assert "weather-cloudy" not in vals_42


async def test_commute_weather_units_and_precipitation_formatting(hass):
    from datetime import timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = dt_util.start_of_local_day() + timedelta(hours=7, minutes=30)

    def render_size(state_attrs, daily_row, size=(296, 128)):
        hass.states.async_set("weather.home", "sunny", state_attrs)
        fc = {
            "fc": {
                "weather.home": {
                    "forecast": [
                        {"datetime": (today + timedelta(hours=4)).isoformat(), **daily_row}
                    ]
                }
            }
        }
        built = build(TEMPLATES["weather_commute"], size[0], size[1], "BWR")
        return _values(resolve_templates(hass, built["payload"], set(), fc))

    with freeze_time(today, real_asyncio=True):
        # 10°F spread and 7 mph wind are normal in imperial units (not 10°C / 7 m/s).
        vals_mild_imp = render_size(
            {
                "temperature": 60,
                "temperature_unit": "°F",
                "apparent_temperature": 59,
                "humidity": 50,
                "wind_speed": 7,
                "wind_speed_unit": "mph",
            },
            {
                "condition": "sunny",
                "temperature": 68,
                "templow": 58,
                "precipitation_probability": 10,
            },
        )
        assert "우산 불필요" in vals_mild_imp
        assert "일교차 주의" not in vals_mild_imp and "강풍 주의" not in vals_mild_imp

        # 18°F spread triggers temperature-gap advisory; 16 mph triggers wind advisory.
        vals_gap_imp = render_size(
            {
                "temperature": 55,
                "temperature_unit": "°F",
                "apparent_temperature": 53,
                "humidity": 40,
                "wind_speed": 5,
                "wind_speed_unit": "mph",
            },
            {
                "condition": "sunny",
                "temperature": 73,
                "templow": 55,
                "precipitation_probability": 0,
            },
        )
        assert {"일교차 주의", "일교차 18°"} <= set(vals_gap_imp)

        vals_wind_imp = render_size(
            {
                "temperature": 55,
                "temperature_unit": "°F",
                "apparent_temperature": 49,
                "humidity": 45,
                "wind_speed": 16,
                "wind_speed_unit": "mph",
            },
            {
                "condition": "cloudy",
                "temperature": 60,
                "templow": 52,
                "precipitation_probability": 20,
            },
        )
        assert "강풍 주의" in vals_wind_imp

        # Positive precipitation in inches (0.04in) and near-integer mm (1.96mm -> 2mm).
        vals_in = render_size(
            {
                "temperature": 50,
                "temperature_unit": "°F",
                "apparent_temperature": 48,
                "humidity": 80,
                "wind_speed": 5,
                "wind_speed_unit": "mph",
                "precipitation_unit": "in",
            },
            {
                "condition": "rainy",
                "temperature": 54,
                "templow": 46,
                "precipitation_probability": 70,
                "precipitation": 0.04,
            },
            size=(384, 184),
        )
        assert "강수 70% · 0.04in" in vals_in

        vals_mm = render_size(
            {
                "temperature": 11,
                "temperature_unit": "°C",
                "apparent_temperature": 9,
                "humidity": 80,
                "wind_speed": 3,
                "wind_speed_unit": "m/s",
                "precipitation_unit": "mm",
            },
            {
                "condition": "rainy",
                "temperature": 14,
                "templow": 8,
                "precipitation_probability": 70,
                "precipitation": 1.96,
            },
            size=(384, 184),
        )
        assert "강수 70% · 2mm" in vals_mm


@pytest.mark.parametrize(
    ("accent", "expected_ink", "expected_fg"),
    [("yellow", "yellow", "black"), ("white", "black", "black")],
)
async def test_commute_weather_yellow_and_white_accent_contrast(
    hass, accent, expected_ink, expected_fg
):
    from datetime import timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = dt_util.start_of_local_day() + timedelta(hours=7, minutes=30)
    hass.states.async_set("weather.home", "rainy", {"temperature": 11, "temperature_unit": "°C"})
    variables = {
        "fc": {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": (today + timedelta(days=offset, hours=4)).isoformat(),
                        "condition": "rainy",
                        "temperature": 13,
                        "templow": 6,
                        "precipitation_probability": 80,
                    }
                    for offset in range(6)
                ]
            }
        }
    }
    with freeze_time(today, real_asyncio=True):
        built = build(TEMPLATES["weather_commute"], 400, 300, "BWRY", {"accent": accent})
        rendered = resolve_templates(hass, built["payload"], set(), variables)
        pill_rect = next(
            item for item in rendered if item["type"] == "rectangle" and item["y_start"] < 20
        )
        assert pill_rect["fill"] == expected_ink
        pill_text = next(item for item in rendered if item.get("value") == "우산 챙기기")
        assert pill_text["color"] == expected_fg
        pop_texts = [item for item in rendered if item.get("value") == "80%"]
        assert pop_texts and all(item["color"] == expected_fg for item in pop_texts)
        high_text = next(
            item for item in rendered if item.get("value") == "13°" and item["y"] < 100
        )
        assert high_text["color"] == expected_ink


async def test_commute_weather_designer_preview_fetches_all_seven_forecast_days(hass, wolink_entry):
    from datetime import datetime, timedelta

    from freezegun import freeze_time
    from homeassistant.core import SupportsResponse
    from homeassistant.util import dt as dt_util

    thursday = datetime(2026, 11, 19, 7, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    daily = [
        {
            "datetime": (thursday + timedelta(days=offset, hours=5)).isoformat(),
            "condition": "sunny",
            "temperature": 10 + offset,
            "templow": 2 + offset,
            "precipitation_probability": 10,
        }
        for offset in range(-1, 8)
    ]

    async def get_forecasts(call):
        return {"weather.home": {"forecast": daily}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    hass.states.async_set("weather.home", "sunny", {"temperature": 10, "temperature_unit": "°C"})
    designer = hass.data[KEY]
    with freeze_time(thursday, real_asyncio=True):
        built = build(TEMPLATES["weather_commute"], 960, 640, "BWR")
        variables = await designer.forecast_variable(built["payload"], {})
        assert len(variables["fc"]["weather.home"]["forecast"]) == 9
        vals = _values(resolve_templates(hass, built["payload"], set(), variables))
        # Day +7 (목) has temperature 17° / templow 9° (not truncated at index 7).
        assert {"목", "17°", "9°"} <= set(vals)


@pytest.mark.parametrize("size", sorted(TEMPLATES["weather_commute"]["layouts"]))
def test_commute_weather_boxes_do_not_overlap_in_any_layout(size):
    from itertools import combinations

    width, height = (int(part) for part in size.split("x"))
    items = build(TEMPLATES["weather_commute"], width, height, "BWRY")["payload"]
    frames = []
    for item in items:
        if item["type"] == "text_fit":
            frames.append(("text_fit", _frame(item)))
        elif item["type"] == "icon":
            sz = item["size"]
            left = item["x"] - (sz // 2 if item.get("anchor") == "mt" else 0)
            top = item["y"]
            frames.append(("icon", (left, top, left + sz, top + sz)))
    for (kind_a, a), (kind_b, b) in combinations(frames, 2):
        # Adjacent icon/text inside a shared pill/banner may touch or share margins,
        # but two text_fit boxes or a text_fit box and an icon must never overlap.
        if "text_fit" in (kind_a, kind_b):
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (
                size,
                (kind_a, a),
                (kind_b, b),
            )


def test_indoor_climate_covers_all_29_sizes_without_overlap():
    template = TEMPLATES["indoor_climate"]
    assert set(template["layouts"]) == set(TEMPLATES["weather_outdoor"]["layouts"])
    assert len((TEMPLATE_DIR / "indoor_climate.yaml").read_bytes()) < 256 * 1024

    def _box(item):
        kind = item["type"]
        if kind == "text_fit":
            return (item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"])
        if kind in ("progress_bar", "rectangle", "line"):
            return (item["x_start"], item["y_start"], item["x_end"], item["y_end"])
        if kind == "icon":
            size = item["size"]
            return (
                item["x"] - size // 2,
                item["y"] - size // 2,
                item["x"] + size - size // 2,
                item["y"] + size - size // 2,
            )
        return None

    for size, items in template["layouts"].items():
        assert len(items) <= 100, size
        width, height = (int(part) for part in size.split("x"))
        all_boxes = [
            (index, item["type"], box)
            for index, item in enumerate(items)
            if (box := _box(item)) is not None
        ]
        for index, kind, box in all_boxes:
            if kind == "line":
                assert 0 <= box[0] <= box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] <= box[3] <= height, (size, index, kind, box)
            else:
                assert 0 <= box[0] < box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] < box[3] <= height, (size, index, kind, box)
        fg_boxes = [entry for entry in all_boxes if entry[1] not in ("rectangle", "line")]
        for idx in range(len(fg_boxes)):
            for jdx in range(idx + 1, len(fg_boxes)):
                i1, t1, b1 = fg_boxes[idx]
                i2, t2, b2 = fg_boxes[jdx]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: element {i1}({t1}) {b1} overlaps {i2}({t2}) {b2}"


async def test_indoor_climate_renders_alerts_contrast_and_edge_cases(hass):
    from custom_components.ble_esl.designer.specs import resolve_templates

    hass.states.async_set("sensor.temperature", "23.5", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.humidity", "48", {"unit_of_measurement": "%"})
    texts = _texts(_shown(hass, "indoor_climate", 800, 480))
    assert "23.5°C" in texts and "48%" in texts and "쾌적" in texts and "미설정" in texts

    # Warm / slightly humid thresholds stay consistent between chips and header badge.
    hass.states.async_set("sensor.temperature", "27.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.humidity", "63", {"unit_of_measurement": "%"})
    warm_texts = _texts(_shown(hass, "indoor_climate", 800, 480))
    assert "따뜻" in warm_texts and "약간 습함" in warm_texts and "보통" in warm_texts

    # Fahrenheit support: comfort thresholds & hints adapt without false overheating alerts.
    hass.states.async_set("sensor.temperature", "72", {"unit_of_measurement": "°F"})
    hass.states.async_set("sensor.humidity", "50", {"unit_of_measurement": "%"})
    f_texts = _texts(_shown(hass, "indoor_climate", 800, 480))
    assert "72°F" in f_texts and "쾌적" in f_texts and "적정 68 ~ 79°F" in f_texts

    # Near-zero negative temperatures never render as "-0°C", while real negatives keep their sign.
    hass.states.async_set("sensor.temperature", "-0.04", {"unit_of_measurement": "°C"})
    assert "0°C" in _texts(_shown(hass, "indoor_climate", 400, 300))
    assert "-0°C" not in _texts(_shown(hass, "indoor_climate", 400, 300))
    hass.states.async_set("sensor.temperature", "-12.5", {"unit_of_measurement": "°C"})
    assert "-12.5°C" in _texts(_shown(hass, "indoor_climate", 400, 300))

    # Optional CO2 / PM2.5 sensors trigger ventilation alert and accent contrast across BW/BWR/BWRY.
    hass.states.async_set("sensor.temperature", "24.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.humidity", "48", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.co2", "1250")
    hass.states.async_set("sensor.pm25", "42")
    options = {"co2_sensor": "sensor.co2", "pm25_sensor": "sensor.pm25"}
    alert_items = resolve_templates(
        hass, build(TEMPLATES["indoor_climate"], 800, 480, "BWR", options)["payload"], set()
    )
    alert_texts = [str(item.get("value", "")) for item in alert_items]
    assert "1250 ppm" in alert_texts and "42 ug/m3" in alert_texts and "환기 권장" in alert_texts
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "red" for item in alert_items
    )
    assert any(
        item.get("value") == "환기 권장" and item.get("color") == "white" for item in alert_items
    )

    # accent="yellow" on BWRY uses yellow pill + black text, and keeps white-bg text/icons black.
    bwry_items = resolve_templates(
        hass,
        build(TEMPLATES["indoor_climate"], 400, 300, "BWRY", {**options, "accent": "yellow"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "yellow" for item in bwry_items
    )
    assert any(
        item.get("value") == "환기 권장" and item.get("color") == "black" for item in bwry_items
    )
    assert not any(
        item.get("type") in ("text_fit", "icon") and item.get("color") in ("yellow", "white")
        for item in bwry_items
    )

    # accent="white" never renders black-on-black pill text.
    white_accent_items = resolve_templates(
        hass,
        build(TEMPLATES["indoor_climate"], 400, 300, "BWR", {**options, "accent": "white"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "black"
        for item in white_accent_items
    )
    assert any(
        item.get("value") == "환기 권장" and item.get("color") == "white"
        for item in white_accent_items
    )

    bw_items = resolve_templates(
        hass,
        build(TEMPLATES["indoor_climate"], 400, 300, "BW", {**options, "accent": "red"})["payload"],
        set(),
    )
    assert any(item.get("type") == "rectangle" and item.get("fill") == "black" for item in bw_items)
    assert any(
        item.get("value") == "환기 권장" and item.get("color") == "white" for item in bw_items
    )
    bw_tiny_items = resolve_templates(
        hass,
        build(TEMPLATES["indoor_climate"], 212, 104, "BW", {**options, "accent": "red"})["payload"],
        set(),
    )
    assert not any(item.get("type") == "rectangle" for item in bw_tiny_items)
    assert any(
        item.get("value") == "환기 권장" and item.get("color") == "black" for item in bw_tiny_items
    )

    # Tiny portrait stays decluttered (no CO2/hint clutter), while 4.2"+ shows CO2 & humidifier advice.
    co2_tiny = _texts(_shown(hass, "indoor_climate", 104, 212, {"co2_sensor": "sensor.co2"}))
    assert co2_tiny == ["24°C", "48%", "환기 권장"]
    co2_panel = _texts(_shown(hass, "indoor_climate", 400, 300, {"co2_sensor": "sensor.co2"}))
    assert "1250 ppm" in co2_panel and "환기 권장" in co2_panel
    hass.states.async_set("sensor.humidity", "22")
    dry_panel = _texts(_shown(hass, "indoor_climate", 400, 300))
    assert any("가습기" in t for t in dry_panel)

    # Malformed optional entity IDs are treated as unset rather than missing entities.
    for bogus in ("1.2", "sensor.", " sensor.co2 ", "a.b.c"):
        bogus_texts = _texts(
            _shown(hass, "indoor_climate", 800, 480, {"co2_sensor": bogus, "pm25_sensor": bogus})
        )
        assert bogus_texts.count("미설정") == 2 and bogus_texts.count("선택") == 2

    # Edge cases: non-numeric / nan / inf / bool states never crash and round-trip cleanly.
    for bad in ("unavailable", "nan", "inf", "warm", "True"):
        hass.states.async_set("sensor.temperature", bad, {"unit_of_measurement": "°C"})
        hass.states.async_set("sensor.humidity", bad)
        hass.states.async_set("sensor.co2", bad)
        hass.states.async_set("sensor.pm25", bad)
        rendered = _shown(hass, "indoor_climate", 800, 480, options)
        bad_texts = _texts(rendered)
        assert "--°C" in bad_texts and "--%" in bad_texts and "센서 대기" in bad_texts
        render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), rendered)

    hass.states.async_set("sensor.temperature", "29.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.humidity", "70")
    hass.states.async_set("sensor.co2", "1100")
    hass.states.async_set("sensor.pm25", "40")
    for size in TEMPLATES["indoor_climate"]["layouts"]:
        w, h = (int(part) for part in size.split("x"))
        preset = DevicePreset("test", "test", w, h, "BWR")
        elements, imported, issues = elements_from(
            build(TEMPLATES["indoor_climate"], w, h, "BWR", options)["payload"], preset
        )
        assert issues == [], size
        original, rebuilt = stable_template_payloads(hass, imported, elements)
        assert different_pixels(hass, preset, original, rebuilt) == 0, size


def test_calendar_weather_covers_all_29_sizes_without_overlap():
    template = TEMPLATES["calendar_weather"]
    assert set(template["layouts"]) == set(TEMPLATES["weather_outdoor"]["layouts"])
    assert len((TEMPLATE_DIR / "calendar_weather.yaml").read_bytes()) < 256 * 1024

    def _box(item):
        kind = item["type"]
        if kind == "text_fit":
            return (item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"])
        if kind in ("rectangle", "line"):
            return (item["x_start"], item["y_start"], item["x_end"], item["y_end"])
        if kind == "icon":
            size = item["size"]
            return (
                item["x"] - size // 2,
                item["y"] - size // 2,
                item["x"] + size - size // 2,
                item["y"] + size - size // 2,
            )
        return None

    for size, items in template["layouts"].items():
        assert len(items) <= 100, size
        width, height = (int(part) for part in size.split("x"))
        all_boxes = [
            (index, item["type"], box)
            for index, item in enumerate(items)
            if (box := _box(item)) is not None
        ]
        for index, kind, box in all_boxes:
            if kind == "line":
                assert 0 <= box[0] <= box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] <= box[3] <= height, (size, index, kind, box)
            else:
                assert 0 <= box[0] < box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] < box[3] <= height, (size, index, kind, box)
        fg_boxes = [entry for entry in all_boxes if entry[1] not in ("rectangle", "line")]
        for idx in range(len(fg_boxes)):
            for jdx in range(idx + 1, len(fg_boxes)):
                i1, t1, b1 = fg_boxes[idx]
                i2, t2, b2 = fg_boxes[jdx]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: element {i1}({t1}) {b1} overlaps {i2}({t2}) {b2}"


async def test_calendar_weather_renders_forecast_events_edge_cases_and_designer(hass, wolink_entry):
    from homeassistant.core import SupportsResponse
    from homeassistant.util import dt as dt_util

    from custom_components.ble_esl.designer.specs import resolve_templates
    from scripts.designer_demo import demo_payload_variables

    today = dt_util.now().date().isoformat()
    tomorrow = (dt_util.now() + __import__("datetime").timedelta(days=1)).date().isoformat()
    hass.states.async_set(
        "weather.home",
        "rainy",
        {"temperature": 14.5, "temperature_unit": "°C", "humidity": 78},
    )
    hass.states.async_set(
        "calendar.home",
        "on",
        {
            "message": "Fallback Meeting",
            "start_time": f"{today} 09:00:00",
            "end_time": f"{today} 10:00:00",
            "all_day": False,
            "location": "Room 101",
        },
    )
    forecast = [
        {
            "datetime": today,
            "condition": "rainy",
            "templow": 8,
            "temperature": 17,
            "precipitation_probability": 70,
        },
        {
            "datetime": tomorrow,
            "condition": "sunny",
            "templow": 6,
            "temperature": 19,
            "precipitation_probability": 10,
        },
    ]
    events = [
        {
            "summary": "Standup",
            "start": f"{today}T09:30:00+09:00",
            "end": f"{today}T10:00:00+09:00",
            "location": "Room A",
        },
        {
            "summary": "Design Review",
            "start": f"{today}T14:00:00+09:00",
            "end": f"{today}T15:00:00+09:00",
        },
        {
            "summary": "Release Trip",
            "start": "2026-11-23",
            "end": "2026-11-25",
        },
    ]

    # Small (<4") uses weather forecast & calendar entity attributes only (no calendar.get_events needed).
    small_payload = build(TEMPLATES["calendar_weather"], 250, 128, "BWR")["payload"]
    small_texts = _texts(
        resolve_templates(
            hass, small_payload, set(), {"fc": {"weather.home": {"forecast": forecast}}}
        )
    )
    assert "14.5°C" in small_texts and "Fallback Meeting" in small_texts
    med_payload = build(TEMPLATES["calendar_weather"], 384, 184, "BWR")["payload"]
    med_texts = _texts(
        resolve_templates(
            hass, med_payload, set(), {"fc": {"weather.home": {"forecast": forecast}}}
        )
    )
    assert "14.5°C" in med_texts and "Fallback Meeting" in med_texts
    assert not any("갱신" in t for t in med_texts)
    small_elements, _, small_issues = elements_from(
        small_payload, DevicePreset("small", "small", 250, 128, "BWR")
    )
    assert small_issues == []
    small_saved = await hass.data[KEY].export(
        wolink_entry, {"version": 1, "elements": small_elements, "background": "white"}
    )
    assert small_saved["setup_actions"] == []

    # 4.2"+ displays forecast + upcoming events list + badge contrast + all-day formatting.
    large_payload = build(TEMPLATES["calendar_weather"], 800, 480, "BWR")["payload"]
    vars_both = {
        "fc": {"weather.home": {"forecast": forecast}},
        "events": {"calendar.home": {"events": events}},
    }
    large_rendered = resolve_templates(hass, large_payload, set(), vars_both)
    large_texts = [str(item.get("value", "")) for item in large_rendered]
    assert "14.5°C" in large_texts and "70%" in large_texts
    assert (
        "Standup" in large_texts
        and "Design Review" in large_texts
        and "Release Trip" in large_texts
    )
    assert any("11/23 - 11/24" in text for text in large_texts)
    assert "일정 3건" in large_texts
    render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), large_rendered)

    # Fallback to entity attributes when events list is empty.
    fallback_texts = _texts(
        resolve_templates(
            hass,
            large_payload,
            set(),
            {
                "fc": {"weather.home": {"forecast": forecast}},
                "events": {"calendar.home": {"events": []}},
            },
        )
    )
    assert "Fallback Meeting" in fallback_texts and "일정 1건" in fallback_texts

    # Contrast safety on BWRY accent=yellow & BWR accent=white, plus near-zero/nan/inf resilience.
    bwry_items = resolve_templates(
        hass,
        build(TEMPLATES["calendar_weather"], 400, 300, "BWRY", {"accent": "yellow"})["payload"],
        set(),
        vars_both,
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "yellow" for item in bwry_items
    )
    assert any(
        item.get("value") == "일정 3건" and item.get("color") == "black" for item in bwry_items
    )
    assert not any(
        item.get("type") in ("text_fit", "icon") and item.get("color") in ("yellow", "white")
        for item in bwry_items
    )

    white_items = resolve_templates(
        hass,
        build(TEMPLATES["calendar_weather"], 400, 300, "BWR", {"accent": "white"})["payload"],
        set(),
        vars_both,
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "black" for item in white_items
    )
    assert any(
        item.get("value") == "일정 3건" and item.get("color") == "white" for item in white_items
    )

    hass.states.async_set("weather.home", "sunny", {"temperature": -0.04, "humidity": "nan"})
    near_zero_texts = _texts(
        resolve_templates(
            hass,
            large_payload,
            set(),
            {
                "events": {
                    "calendar.home": {
                        "events": [
                            {
                                "summary": "Mix",
                                "start": "2026-11-23",
                                "end": "2026-11-23T12:00:00+09:00",
                            },
                            {
                                "summary": "SingleDayAll",
                                "start": "2026-11-23",
                                "end": "2026-11-24",
                            },
                            {
                                "summary": "MultiTimed",
                                "start": "2026-11-23T09:00:00",
                                "end": "2026-11-24T18:00:00",
                            },
                            {
                                "summary": "주간 제품 디자인 리뷰 및 일정 확인 장기 타이틀 테스트",
                                "start": "2026-11-25T10:00:00+00:00",
                                "end": "2026-11-25T11:00:00+00:00",
                            },
                        ]
                    }
                }
            },
        )
    )
    assert "0°C" in near_zero_texts and "-0°C" not in near_zero_texts and "Mix" in near_zero_texts
    assert "11/23" in near_zero_texts and "11/23 - 11/23" not in near_zero_texts
    assert "11/23 09:00 - 11/24 18:00" in near_zero_texts
    utc_expected = dt_util.as_local(dt_util.parse_datetime("2026-11-25T10:00:00+00:00")).strftime(
        "%m/%d %H:%M"
    )
    assert any(utc_expected in t for t in near_zero_texts)

    # Malformed / incomplete fc & events mappings never crash under strict=True.
    for bad_fc, bad_ev in (
        ({"weather.home": {}}, {"calendar.home": {}}),
        ({"weather.home": {"forecast": "none"}}, {"calendar.home": {"events": "none"}}),
        ({"weather.home": {"forecast": {"a": 1}}}, {"calendar.home": {"events": {"a": 1}}}),
        ({"weather.home": {"forecast": [None]}}, {"calendar.home": {"events": [None]}}),
    ):
        bad_res = _texts(
            resolve_templates(hass, large_payload, set(), {"fc": bad_fc, "events": bad_ev})
        )
        assert "Fallback Meeting" in bad_res and "일정 1건" in bad_res

    # Empty time_format is rejected by parameter validation.
    with pytest.raises(HomeAssistantError, match="time_format"):
        resolve_parameters(TEMPLATES["calendar_weather"], {"time_format": ""}, "BWR")

    # Designer preview, preview_design_template, apply_design_template, export, automation validation, and demo.
    from scripts.designer_demo import STATES as DEMO_STATES

    assert "calendar.home" in DEMO_STATES

    async def get_forecasts(call):
        return {
            entity: {"forecast": forecast}
            for entity in (
                [call.data["entity_id"]]
                if isinstance(call.data["entity_id"], str)
                else call.data["entity_id"]
            )
        }

    event_calls = 0

    async def get_events(call):
        nonlocal event_calls
        event_calls += 1
        ids = call.data["entity_id"]
        ids = [ids] if isinstance(ids, str) else ids
        return {entity: {"events": events} for entity in ids}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register(
        "calendar", "get_events", get_events, supports_response=SupportsResponse.ONLY
    )
    designer = hass.data[KEY]
    large_elements, _, large_issues = elements_from(
        large_payload, DevicePreset("large", "large", 800, 480, "BWR")
    )
    assert large_issues == []
    large_doc = {"version": 1, "elements": large_elements, "background": "white"}
    preview = await designer.preview(wolink_entry, large_doc)
    assert "Standup" in _texts(preview["payload"])
    gallery_preview = await designer.preview_design_template(wolink_entry, "calendar_weather")
    assert gallery_preview["png"].startswith("data:image/png;base64,")
    applied = await designer.apply_design_template(wolink_entry, "calendar_weather")
    assert applied["issues"] == [] and applied["different_pixels"] == 0
    saved = await designer.export(wolink_entry, large_doc)
    assert [step["action"] for step in saved["setup_actions"]] == [
        "weather.get_forecasts",
        "calendar.get_events",
    ]
    auto = await designer.automation(wolink_entry, large_doc)
    assert [step["action"] for step in auto["automation"]["actions"]] == [
        "weather.get_forecasts",
        "calendar.get_events",
        "ble_esl.write",
    ]
    await async_validate_config_item(hass, {}, auto["automation"])
    auto_dedup = await designer.automation(
        wolink_entry, large_doc, defaults={"actions": saved["setup_actions"]}
    )
    assert [step["action"] for step in auto_dedup["automation"]["actions"]] == [
        "weather.get_forecasts",
        "calendar.get_events",
        "ble_esl.write",
    ]

    # _preview_calendar_events cools down after a failing service call.
    fail_calls = 0

    async def failing_get_events(call):
        nonlocal fail_calls
        fail_calls += 1
        raise RuntimeError("calendar backend down")

    hass.states.async_set("calendar.work", "on", {"message": "Work Fallback"})
    hass.services.async_register(
        "calendar", "get_events", failing_get_events, supports_response=SupportsResponse.ONLY
    )
    work_elements, _, _ = elements_from(
        build(TEMPLATES["calendar_weather"], 800, 480, "BWR", {"calendar": "calendar.work"})[
            "payload"
        ],
        DevicePreset("large", "large", 800, 480, "BWR"),
    )
    work_doc = {"version": 1, "elements": work_elements, "background": "white"}
    await designer.preview(wolink_entry, work_doc)
    await designer.preview(wolink_entry, work_doc)
    assert fail_calls == 1

    demo_vars = demo_payload_variables(large_payload, {("weather.home", "daily"): forecast})
    assert (
        "fc" in demo_vars
        and "events" in demo_vars
        and demo_vars["events"]["calendar.home"]["events"]
    )

    # Round-trip pixel parity across all 29 sizes (with long summary shrink_ellipsis).
    hass.states.async_set("weather.home", "cloudy", {"temperature": 18, "humidity": 55})
    hass.states.async_set(
        "calendar.home",
        "on",
        {
            "message": "주간 제품 디자인 회의 및 리뷰 일정 상세 확인",
            "start_time": f"{today} 09:30:00",
            "end_time": f"{today} 10:00:00",
            "all_day": False,
            "location": "Main Conference Room A",
        },
    )
    for size in TEMPLATES["calendar_weather"]["layouts"]:
        w, h = (int(part) for part in size.split("x"))
        preset = DevicePreset("test", "test", w, h, "BWR")
        elements, imported, issues = elements_from(
            build(TEMPLATES["calendar_weather"], w, h, "BWR")["payload"], preset
        )
        assert issues == [], size
        original, rebuilt = stable_template_payloads(hass, imported, elements)
        assert different_pixels(hass, preset, original, rebuilt) == 0, size


def test_home_presence_covers_all_29_sizes_without_overlap():
    template = TEMPLATES["home_presence"]
    assert set(template["layouts"]) == set(TEMPLATES["weather_outdoor"]["layouts"])
    assert len((TEMPLATE_DIR / "home_presence.yaml").read_bytes()) < 256 * 1024

    def _box(item):
        kind = item["type"]
        if kind == "text_fit":
            return (item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"])
        if kind in ("rectangle", "line"):
            return (item["x_start"], item["y_start"], item["x_end"], item["y_end"])
        if kind == "icon":
            size = item["size"]
            return (
                item["x"] - size // 2,
                item["y"] - size // 2,
                item["x"] + size - size // 2,
                item["y"] + size - size // 2,
            )
        return None

    for size, items in template["layouts"].items():
        assert len(items) <= 100, size
        width, height = (int(part) for part in size.split("x"))
        all_boxes = [
            (index, item["type"], box)
            for index, item in enumerate(items)
            if (box := _box(item)) is not None
        ]
        for index, kind, box in all_boxes:
            if kind == "line":
                assert 0 <= box[0] <= box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] <= box[3] <= height, (size, index, kind, box)
            else:
                assert 0 <= box[0] < box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] < box[3] <= height, (size, index, kind, box)
        fg_boxes = [entry for entry in all_boxes if entry[1] not in ("rectangle", "line")]
        line_boxes = [entry for entry in all_boxes if entry[1] == "line"]
        for idx in range(len(fg_boxes)):
            for jdx in range(idx + 1, len(fg_boxes)):
                i1, t1, b1 = fg_boxes[idx]
                i2, t2, b2 = fg_boxes[jdx]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: element {i1}({t1}) {b1} overlaps {i2}({t2}) {b2}"
            i1, t1, b1 = fg_boxes[idx]
            for li, _, lb in line_boxes:
                lx0, ly0, lx1, ly1 = lb
                line_box = (lx0, ly0, lx1 + (lx0 == lx1), ly1 + (ly0 == ly1))
                hits_line = (
                    b1[0] < line_box[2]
                    and line_box[0] < b1[2]
                    and b1[1] < line_box[3]
                    and line_box[1] < b1[3]
                )
                assert not hits_line, f"{size}: element {i1}({t1}) {b1} touches line {li} {lb}"


async def test_home_presence_renders_states_doors_contrast_and_edge_cases(hass, wolink_entry):
    from custom_components.ble_esl.designer.specs import resolve_templates
    from scripts.designer_demo import STATES as DEMO_STATES

    assert "person.home" in DEMO_STATES

    hass.states.async_set("person.home", "home", {"friendly_name": "민준"})
    hass.states.async_set("person.partner", "not_home", {"friendly_name": "서연"})
    hass.states.async_set("person.kid", "학교", {"friendly_name": "지우"})
    hass.states.async_set("person.guest", "unavailable", {"friendly_name": "손님"})
    hass.states.async_set("binary_sensor.front_door", "on", {"friendly_name": "현관문"})

    options = {
        "person_1": "person.home",
        "person_2": "person.partner",
        "person_3": "person.kid",
        "person_4": "person.guest",
        "door_sensor": "binary_sensor.front_door",
    }
    rendered = resolve_templates(
        hass, build(TEMPLATES["home_presence"], 800, 480, "BWR", options)["payload"], set()
    )
    texts = [str(item.get("value", "")) for item in rendered]
    assert {"민준", "서연", "지우", "손님", "재실", "외출", "학교", "알 수 없음"} <= set(texts)
    assert "재실 1/4" in texts and "현관 출입문 · 열림 주의" in texts
    assert any(item.get("type") == "rectangle" and item.get("fill") == "red" for item in rendered)
    assert any(
        item.get("value") == "현관 출입문 · 열림 주의" and item.get("color") == "white"
        for item in rendered
    )
    render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), rendered)

    # All away + door closed -> neutral badge & door closed banner.
    hass.states.async_set("person.home", "not_home", {"friendly_name": "민준"})
    hass.states.async_set("binary_sensor.front_door", "off")
    away_texts = _texts(_shown(hass, "home_presence", 800, 480, options))
    assert "전원 외출" in away_texts and "현관 출입문 · 닫힘 (안전)" in away_texts

    # 0-person configured/missing, unknown state, and valid-format missing optional entities.
    zero_texts = _texts(
        _shown(
            hass,
            "home_presence",
            800,
            480,
            {"person_1": "person.missing_primary", "door_sensor": "binary_sensor.missing_door"},
        )
    )
    assert "연결 대기" in zero_texts and "엔티티 없음" in zero_texts
    assert "현관 출입문 · 확인 필요" in zero_texts

    hass.states.async_set("person.unknown_member", "unknown", {"friendly_name": "누군가"})
    unknown_texts = _texts(
        _shown(hass, "home_presence", 800, 480, {"person_2": "person.unknown_member"})
    )
    assert "누군가" in unknown_texts and "알 수 없음" in unknown_texts

    # Compact portrait layouts with unset door_sensor/people omit clock chrome and show door fallback.
    hass.states.async_set("person.home", "home", {"friendly_name": "민준"})
    for cw, ch in ((104, 212), (128, 250), (184, 384), (240, 416)):
        compact_items = resolve_templates(
            hass, build(TEMPLATES["home_presence"], cw, ch, "BWR")["payload"], set()
        )
        compact_texts = [str(item.get("value", "")) for item in compact_items]
        assert "현관 · 미설정" in compact_texts
        assert not any("갱신" in t for t in compact_texts)

    # Unavailable door & unset optional people + malformed IDs handled safely.
    hass.states.async_set("person.home", "home", {"friendly_name": "민준"})
    hass.states.async_set("binary_sensor.front_door", "unavailable")
    unavail_texts = _texts(_shown(hass, "home_presence", 800, 480, options))
    assert "현관 출입문 · 확인 필요" in unavail_texts

    for bogus in ("1.2", "person.", " binary_sensor.door ", "a.b.c"):
        unset_texts = _texts(
            _shown(
                hass,
                "home_presence",
                800,
                480,
                {"person_2": bogus, "person_3": bogus, "person_4": bogus, "door_sensor": bogus},
            )
        )
        assert unset_texts.count("미설정") == 3 and "현관 센서 · 미설정" in unset_texts

    # Contrast safety on BWRY accent=yellow, BWR accent=white, and BW.
    hass.states.async_set("binary_sensor.front_door", "on")
    bwry_items = resolve_templates(
        hass,
        build(TEMPLATES["home_presence"], 400, 300, "BWRY", {**options, "accent": "yellow"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "yellow" for item in bwry_items
    )
    assert any(
        item.get("value") == "재실 1/4" and item.get("color") == "black" for item in bwry_items
    )
    assert any(
        item.get("value") == "현관 출입문 · 열림 주의" and item.get("color") == "black"
        for item in bwry_items
    )
    assert not any(
        item.get("type") in ("text_fit", "icon") and item.get("color") in ("yellow", "white")
        for item in bwry_items
    )

    white_items = resolve_templates(
        hass,
        build(TEMPLATES["home_presence"], 400, 300, "BWR", {**options, "accent": "white"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "black" for item in white_items
    )
    assert any(
        item.get("value") == "재실 1/4" and item.get("color") == "white" for item in white_items
    )

    bw_items = resolve_templates(
        hass,
        build(TEMPLATES["home_presence"], 400, 300, "BW", {**options, "accent": "red"})["payload"],
        set(),
    )
    assert any(item.get("type") == "rectangle" and item.get("fill") == "black" for item in bw_items)
    assert any(
        item.get("value") == "재실 1/4" and item.get("color") == "white" for item in bw_items
    )
    bw_tiny_items = resolve_templates(
        hass,
        build(TEMPLATES["home_presence"], 212, 104, "BW", {**options, "accent": "red"})["payload"],
        set(),
    )
    assert not any(item.get("type") == "rectangle" for item in bw_tiny_items)
    assert any(
        item.get("value") == "재실 1/4" and item.get("color") == "black" for item in bw_tiny_items
    )

    # Designer preview & apply + full 29-size round-trip pixel parity.
    designer = hass.data[KEY]
    preview = await designer.preview_design_template(wolink_entry, "home_presence", options)
    assert preview["png"].startswith("data:image/png;base64,")
    applied = await designer.apply_design_template(wolink_entry, "home_presence", options)
    assert applied["issues"] == [] and applied["different_pixels"] == 0

    for size in TEMPLATES["home_presence"]["layouts"]:
        w, h = (int(part) for part in size.split("x"))
        preset = DevicePreset("test", "test", w, h, "BWR")
        elements, imported, issues = elements_from(
            build(TEMPLATES["home_presence"], w, h, "BWR", options)["payload"], preset
        )
        assert issues == [], size
        original, rebuilt = stable_template_payloads(hass, imported, elements)
        assert different_pixels(hass, preset, original, rebuilt) == 0, size


def test_energy_power_covers_all_29_sizes_without_overlap():
    template = TEMPLATES["energy_power"]
    assert set(template["layouts"]) == set(TEMPLATES["weather_outdoor"]["layouts"])
    assert len((TEMPLATE_DIR / "energy_power.yaml").read_bytes()) < 256 * 1024

    def _box(item):
        kind = item["type"]
        if kind == "text_fit":
            return (item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"])
        if kind in ("progress_bar", "rectangle", "line"):
            return (item["x_start"], item["y_start"], item["x_end"], item["y_end"])
        if kind == "icon":
            size = item["size"]
            return (
                item["x"] - size // 2,
                item["y"] - size // 2,
                item["x"] + size - size // 2,
                item["y"] + size - size // 2,
            )
        return None

    for size, items in template["layouts"].items():
        assert len(items) <= 100, size
        width, height = (int(part) for part in size.split("x"))
        all_boxes = [
            (index, item["type"], box)
            for index, item in enumerate(items)
            if (box := _box(item)) is not None
        ]
        for index, kind, box in all_boxes:
            if kind == "line":
                assert 0 <= box[0] <= box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] <= box[3] <= height, (size, index, kind, box)
            else:
                assert 0 <= box[0] < box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] < box[3] <= height, (size, index, kind, box)
        fg_boxes = [entry for entry in all_boxes if entry[1] not in ("rectangle", "line")]
        rect_boxes = [entry for entry in all_boxes if entry[1] == "rectangle"]
        line_boxes = [entry for entry in all_boxes if entry[1] == "line"]
        for r1 in range(len(rect_boxes)):
            for r2 in range(r1 + 1, len(rect_boxes)):
                i1, _, b1 = rect_boxes[r1]
                i2, _, b2 = rect_boxes[r2]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: rect {i1} {b1} overlaps rect {i2} {b2}"
        for idx in range(len(fg_boxes)):
            for jdx in range(idx + 1, len(fg_boxes)):
                i1, t1, b1 = fg_boxes[idx]
                i2, t2, b2 = fg_boxes[jdx]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: element {i1}({t1}) {b1} overlaps {i2}({t2}) {b2}"
            i1, t1, b1 = fg_boxes[idx]
            for li, _, lb in line_boxes:
                lx0, ly0, lx1, ly1 = lb
                line_box = (lx0, ly0, lx1 + (lx0 == lx1), ly1 + (ly0 == ly1))
                hits_line = (
                    b1[0] < line_box[2]
                    and line_box[0] < b1[2]
                    and b1[1] < line_box[3]
                    and line_box[1] < b1[3]
                )
                assert not hits_line, f"{size}: element {i1}({t1}) {b1} touches line {li} {lb}"
            for ri, _, rb in rect_boxes:
                rw = round(items[ri].get("width", 1))
                inside = (
                    b1[0] >= rb[0] + rw
                    and b1[2] <= rb[2] - rw
                    and b1[1] >= rb[1] + rw
                    and b1[3] <= rb[3] - rw
                )
                disjoint = b1[2] <= rb[0] or rb[2] <= b1[0] or b1[3] <= rb[1] or rb[3] <= b1[1]
                assert inside or disjoint, f"{size}: {i1}({t1}) {b1} crosses rect {ri} border {rb}"


async def test_energy_power_renders_units_alerts_contrast_and_edge_cases(hass, wolink_entry):
    from custom_components.ble_esl.designer.specs import resolve_templates
    from scripts.designer_demo import STATES as DEMO_STATES

    assert "sensor.power" in DEMO_STATES

    hass.states.async_set("sensor.power", "1250", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.energy_today", "10.5", {"unit_of_measurement": "kWh"})
    hass.states.async_set("sensor.solar_power", "840", {"unit_of_measurement": "W"})
    options = {
        "today_energy_sensor": "sensor.energy_today",
        "solar_sensor": "sensor.solar_power",
        "budget_watts": 3000,
    }
    normal_texts = _texts(_shown(hass, "energy_power", 800, 480, options))
    assert {"1250 W", "10.5 kWh", "840 W", "여유"} <= set(normal_texts)

    # kW conversion into budget percentage & overload alert + BW/BWR/BWRY contrast.
    hass.states.async_set("sensor.power", "3.2", {"unit_of_measurement": "kW"})
    kw_items = resolve_templates(
        hass, build(TEMPLATES["energy_power"], 800, 480, "BWR", options)["payload"], set()
    )
    kw_texts = [str(item.get("value", "")) for item in kw_items]
    assert "3.2 kW" in kw_texts and "과부하" in kw_texts and "목표 3000W 대비 107%" in kw_texts
    assert any(item.get("type") == "rectangle" and item.get("fill") == "red" for item in kw_items)
    assert any(item.get("value") == "과부하" and item.get("color") == "white" for item in kw_items)
    render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), kw_items)

    bwry_items = resolve_templates(
        hass,
        build(TEMPLATES["energy_power"], 400, 300, "BWRY", {**options, "accent": "yellow"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "yellow" for item in bwry_items
    )
    assert any(
        item.get("value") == "과부하" and item.get("color") == "black" for item in bwry_items
    )
    assert not any(
        item.get("type") in ("text_fit", "icon") and item.get("color") in ("yellow", "white")
        for item in bwry_items
    )

    white_items = resolve_templates(
        hass,
        build(TEMPLATES["energy_power"], 400, 300, "BWR", {**options, "accent": "white"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "black" for item in white_items
    )
    assert any(
        item.get("value") == "과부하" and item.get("color") == "white" for item in white_items
    )

    # Negative export power and near-zero values never render as "-0".
    hass.states.async_set("sensor.power", "-0.04", {"unit_of_measurement": "kW"})
    export_texts = _texts(_shown(hass, "energy_power", 400, 300))
    assert "-0.04 kW" in export_texts and "발전 여유" in export_texts
    hass.states.async_set("sensor.power", "-0.4", {"unit_of_measurement": "W"})
    nz_texts = _texts(_shown(hass, "energy_power", 400, 300))
    assert "0 W" in nz_texts and "-0 W" not in nz_texts

    # Solar kW/fractional W formatting consistency across compact portrait, tiny/medium landscape, & panels.
    hass.states.async_set("sensor.power", "1800", {"unit_of_measurement": "W"})  # 보통 (50-80%)
    hass.states.async_set("sensor.energy_today", "1.05", {"unit_of_measurement": "kWh"})
    hass.states.async_set("sensor.solar_power", "0.84", {"unit_of_measurement": "kW"})
    assert "보통" in _texts(_shown(hass, "energy_power", 800, 480, options))
    assert {"1.05 kWh", "0.84 kW"} <= set(_texts(_shown(hass, "energy_power", 800, 480, options)))
    tiny_p_texts = _texts(_shown(hass, "energy_power", 104, 212, options))
    assert tiny_p_texts == ["1800 W", "보통", "오늘 1.05kWh"]

    hass.states.async_set("sensor.solar_power", "2.001", {"unit_of_measurement": "kW"})
    assert "2 kW" in _texts(_shown(hass, "energy_power", 400, 300, options))
    tiny_l_texts = _texts(_shown(hass, "energy_power", 212, 104, options))
    assert tiny_l_texts == ["1800 W", "보통", "오늘 1.05kWh"]

    hass.states.async_set("sensor.solar_power", "840.4", {"unit_of_measurement": "W"})
    med_l_texts = _texts(
        resolve_templates(
            hass, build(TEMPLATES["energy_power"], 384, 184, "BWR", options)["payload"], set()
        )
    )
    assert med_l_texts == ["1800 W", "보통", "오늘 1.05kWh"]
    panel_solar_texts = _texts(_shown(hass, "energy_power", 400, 300, options))
    assert "태양광 840W 발전 중 · 현재 부하 60%" in panel_solar_texts

    # Compact <4" omits timestamp chrome; 4.2"+ shows advice.
    med_l_plain = _texts(_shown(hass, "energy_power", 384, 184))
    assert not any("갱신" in t for t in med_l_plain)
    panel_plain = _texts(_shown(hass, "energy_power", 400, 300))
    assert any("안정적인 전력 사용 중입니다" in t for t in panel_plain)

    # Caution tier (80-99%), BW fallback, budget_watts coercion bounds, & empty/missing unit.
    hass.states.async_set("sensor.power", "2500", {})
    caution_bw = resolve_templates(
        hass, build(TEMPLATES["energy_power"], 800, 480, "BW", {"accent": "red"})["payload"], set()
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "black" for item in caution_bw
    )
    assert any(item.get("value") == "주의" and item.get("color") == "white" for item in caution_bw)
    assert any(
        item.get("type") == "progress_bar" and item.get("progress") == 83 for item in caution_bw
    )

    with pytest.raises(HomeAssistantError, match="budget_watts"):
        resolve_parameters(TEMPLATES["energy_power"], {"budget_watts": 50}, "BWR")
    with pytest.raises(HomeAssistantError, match="budget_watts"):
        resolve_parameters(TEMPLATES["energy_power"], {"budget_watts": 60000}, "BWR")

    for cw, ch in ((104, 212), (184, 384), (384, 184), (416, 240)):
        p_texts = _texts(_shown(hass, "energy_power", cw, ch))
        assert not any("갱신" in t for t in p_texts)

    for bogus in ("1.2", "sensor.", " sensor.power ", "a.b.c"):
        bogus_texts = _texts(
            _shown(
                hass,
                "energy_power",
                800,
                480,
                {"today_energy_sensor": bogus, "solar_sensor": bogus},
            )
        )
        assert bogus_texts.count("미설정") == 2

    for bad in ("unavailable", "unknown", "nan", "inf", "-inf", "True", "False"):
        hass.states.async_set("sensor.power", bad, {"unit_of_measurement": "W"})
        hass.states.async_set("sensor.energy_today", bad)
        hass.states.async_set("sensor.solar_power", bad)
        bad_rendered = _shown(hass, "energy_power", 800, 480, options)
        bad_texts = _texts(bad_rendered)
        assert "-- W" in bad_texts and "센서 대기" in bad_texts
        render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), bad_rendered)

    hass.states.async_set("sensor.power", "1850", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.energy_today", "10.5", {"unit_of_measurement": "kWh"})
    hass.states.async_set("sensor.solar_power", "840", {"unit_of_measurement": "W"})
    designer = hass.data[KEY]
    applied = await designer.apply_design_template(wolink_entry, "energy_power", options)
    assert applied["issues"] == [] and applied["different_pixels"] == 0

    for size in TEMPLATES["energy_power"]["layouts"]:
        w, h = (int(part) for part in size.split("x"))
        preset = DevicePreset("test", "test", w, h, "BWR")
        elements, imported, issues = elements_from(
            build(TEMPLATES["energy_power"], w, h, "BWR", options)["payload"], preset
        )
        assert issues == [], size
        original, rebuilt = stable_template_payloads(hass, imported, elements)
        assert different_pixels(hass, preset, original, rebuilt) == 0, size


def test_ev_charging_covers_all_29_sizes_without_overlap():
    template = TEMPLATES["ev_charging"]
    assert set(template["layouts"]) == set(TEMPLATES["weather_outdoor"]["layouts"])
    assert len((TEMPLATE_DIR / "ev_charging.yaml").read_bytes()) < 256 * 1024

    def _box(item):
        kind = item["type"]
        if kind == "text_fit":
            return (item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"])
        if kind in ("progress_bar", "rectangle", "line"):
            return (item["x_start"], item["y_start"], item["x_end"], item["y_end"])
        if kind == "icon":
            size = item["size"]
            return (
                item["x"] - size // 2,
                item["y"] - size // 2,
                item["x"] + size - size // 2,
                item["y"] + size - size // 2,
            )
        return None

    for size, items in template["layouts"].items():
        assert len(items) <= 100, size
        width, height = (int(part) for part in size.split("x"))
        all_boxes = [
            (index, item["type"], box)
            for index, item in enumerate(items)
            if (box := _box(item)) is not None
        ]
        for index, kind, box in all_boxes:
            if kind == "line":
                assert 0 <= box[0] <= box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] <= box[3] <= height, (size, index, kind, box)
            else:
                assert 0 <= box[0] < box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] < box[3] <= height, (size, index, kind, box)
        fg_boxes = [entry for entry in all_boxes if entry[1] not in ("rectangle", "line")]
        rect_boxes = [entry for entry in all_boxes if entry[1] == "rectangle"]
        line_boxes = [entry for entry in all_boxes if entry[1] == "line"]
        for r1 in range(len(rect_boxes)):
            for r2 in range(r1 + 1, len(rect_boxes)):
                i1, _, b1 = rect_boxes[r1]
                i2, _, b2 = rect_boxes[r2]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: rect {i1} {b1} overlaps rect {i2} {b2}"
        for idx in range(len(fg_boxes)):
            for jdx in range(idx + 1, len(fg_boxes)):
                i1, t1, b1 = fg_boxes[idx]
                i2, t2, b2 = fg_boxes[jdx]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: element {i1}({t1}) {b1} overlaps {i2}({t2}) {b2}"
            i1, t1, b1 = fg_boxes[idx]
            for li, _, lb in line_boxes:
                lx0, ly0, lx1, ly1 = lb
                line_box = (lx0, ly0, lx1 + (lx0 == lx1), ly1 + (ly0 == ly1))
                hits_line = (
                    b1[0] < line_box[2]
                    and line_box[0] < b1[2]
                    and b1[1] < line_box[3]
                    and line_box[1] < b1[3]
                )
                assert not hits_line, f"{size}: element {i1}({t1}) {b1} touches line {li} {lb}"
            for ri, _, rb in rect_boxes:
                rw = round(items[ri].get("width", 1))
                inside = (
                    b1[0] >= rb[0] + rw
                    and b1[2] <= rb[2] - rw
                    and b1[1] >= rb[1] + rw
                    and b1[3] <= rb[3] - rw
                )
                disjoint = b1[2] <= rb[0] or rb[2] <= b1[0] or b1[3] <= rb[1] or rb[3] <= b1[1]
                assert inside or disjoint, f"{size}: {i1}({t1}) {b1} crosses rect {ri} border {rb}"


async def test_ev_charging_renders_states_alerts_contrast_and_edge_cases(hass, wolink_entry):
    from custom_components.ble_esl.designer.specs import resolve_templates
    from scripts.designer_demo import STATES as DEMO_STATES

    assert "sensor.ev_battery" in DEMO_STATES

    hass.states.async_set("sensor.ev_battery", "78", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.ev_range", "312", {"unit_of_measurement": "km"})
    hass.states.async_set("sensor.ev_status", "charging")
    hass.states.async_set("sensor.ev_power", "7.2", {"unit_of_measurement": "kW"})
    options = {
        "range_sensor": "sensor.ev_range",
        "status_sensor": "sensor.ev_status",
        "power_sensor": "sensor.ev_power",
        "low_threshold": 20,
    }
    chg_items = resolve_templates(
        hass, build(TEMPLATES["ev_charging"], 800, 480, "BWR", options)["payload"], set()
    )
    chg_texts = [str(item.get("value", "")) for item in chg_items]
    assert {"78%", "312 km", "7.2 kW", "충전 중"} <= set(chg_texts)
    assert any(item.get("type") == "rectangle" and item.get("fill") == "red" for item in chg_items)
    assert any(
        item.get("value") == "충전 중" and item.get("color") == "white" for item in chg_items
    )
    assert any(
        item.get("type") == "icon" and item.get("value") == "battery-charging" for item in chg_items
    )
    render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), chg_items)

    # Low battery alert + BWRY yellow contrast + white accent contrast.
    hass.states.async_set("sensor.ev_battery", "15", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.ev_status", "disconnected")
    hass.states.async_set("sensor.ev_power", "-0.04", {"unit_of_measurement": "kW"})
    low_bwry = resolve_templates(
        hass,
        build(TEMPLATES["ev_charging"], 400, 300, "BWRY", {**options, "accent": "yellow"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("value") == "충전 필요" and item.get("color") == "black" for item in low_bwry
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "yellow" for item in low_bwry
    )
    assert not any(
        item.get("type") in ("text_fit", "icon") and item.get("color") in ("yellow", "white")
        for item in low_bwry
    )

    white_items = resolve_templates(
        hass,
        build(TEMPLATES["ev_charging"], 400, 300, "BWR", {**options, "accent": "white"})["payload"],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "black" for item in white_items
    )
    assert any(
        item.get("value") == "충전 필요" and item.get("color") == "white" for item in white_items
    )

    bw_items = resolve_templates(
        hass,
        build(TEMPLATES["ev_charging"], 800, 480, "BW", {**options, "accent": "red"})["payload"],
        set(),
    )
    assert any(item.get("type") == "rectangle" and item.get("fill") == "black" for item in bw_items)

    # Decimal SOC (1.05 -> 1.1) and W-unit / zero-normalization + complete/fault states.
    hass.states.async_set("sensor.ev_battery", "100", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.ev_status", "complete")
    hass.states.async_set("sensor.ev_power", "-0.4", {"unit_of_measurement": "W"})
    done_texts = _texts(_shown(hass, "ev_charging", 384, 184, options))
    assert "312 km · 0 W" in done_texts
    assert "-0" not in str(done_texts)

    hass.states.async_set("sensor.ev_battery", "65.4", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.ev_power", "3.05", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.ev_status", "unknown")
    inf_texts = _texts(_shown(hass, "ev_charging", 800, 480, options))
    assert {"65.4%", "3.05 kW", "충전 중"} <= set(inf_texts)

    hass.states.async_set("sensor.ev_status", "fault")
    assert "충전 오류" in _texts(_shown(hass, "ev_charging", 384, 184, options))

    # SOC clamping (150 -> 100, -12 -> 0) and decluttered <4" without clock chrome.
    hass.states.async_set("sensor.ev_battery", "150")
    assert "100%" in _texts(_shown(hass, "ev_charging", 200, 200))
    hass.states.async_set("sensor.ev_battery", "-12")
    assert "0%" in _texts(_shown(hass, "ev_charging", 200, 200))

    for cw, ch in ((104, 212), (184, 384), (384, 184), (416, 240)):
        c_texts = _texts(_shown(hass, "ev_charging", cw, ch))
        assert not any("갱신" in t for t in c_texts)

    # Invalid optional entity strings safely display 미설정 and threshold validation bounds apply.
    for bogus in ("1.2", "sensor.", " sensor.ev_range ", "a.b.c"):
        bogus_texts = _texts(
            _shown(
                hass,
                "ev_charging",
                800,
                480,
                {"range_sensor": bogus, "power_sensor": bogus, "status_sensor": bogus},
            )
        )
        assert bogus_texts.count("미설정") == 2

    with pytest.raises(HomeAssistantError, match="low_threshold"):
        resolve_parameters(TEMPLATES["ev_charging"], {"low_threshold": 2}, "BWR")
    with pytest.raises(HomeAssistantError, match="low_threshold"):
        resolve_parameters(TEMPLATES["ev_charging"], {"low_threshold": 80}, "BWR")

    # Non-finite and boolean entity states degrade cleanly.
    for bad in ("unavailable", "unknown", "nan", "inf", "-inf", "True", "False"):
        hass.states.async_set("sensor.ev_battery", bad, {"unit_of_measurement": "%"})
        hass.states.async_set("sensor.ev_range", bad, {"unit_of_measurement": "km"})
        hass.states.async_set("sensor.ev_power", bad, {"unit_of_measurement": "kW"})
        bad_rendered = _shown(hass, "ev_charging", 800, 480, options)
        bad_texts = _texts(bad_rendered)
        assert "--%" in bad_texts and "-- km" in bad_texts and "-- kW" in bad_texts
        render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), bad_rendered)

    hass.states.async_set("sensor.ev_battery", "78", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.ev_range", "312", {"unit_of_measurement": "km"})
    hass.states.async_set("sensor.ev_status", "charging")
    hass.states.async_set("sensor.ev_power", "7.2", {"unit_of_measurement": "kW"})
    designer = hass.data[KEY]
    preview = await designer.preview_design_template(wolink_entry, "ev_charging", options)
    assert preview["png"].startswith("data:image/png;base64,")
    applied = await designer.apply_design_template(wolink_entry, "ev_charging", options)
    assert applied["issues"] == [] and applied["different_pixels"] == 0

    for size in TEMPLATES["ev_charging"]["layouts"]:
        w, h = (int(part) for part in size.split("x"))
        preset = DevicePreset("test", "test", w, h, "BWR")
        elements, imported, issues = elements_from(
            build(TEMPLATES["ev_charging"], w, h, "BWR", options)["payload"], preset
        )
        assert issues == [], size
        original, rebuilt = stable_template_payloads(hass, imported, elements)
        assert different_pixels(hass, preset, original, rebuilt) == 0, size


def test_appliance_status_covers_all_29_sizes_without_overlap():
    template = TEMPLATES["appliance_status"]
    assert set(template["layouts"]) == set(TEMPLATES["weather_outdoor"]["layouts"])
    assert len((TEMPLATE_DIR / "appliance_status.yaml").read_bytes()) < 256 * 1024

    def _box(item):
        kind = item["type"]
        if kind == "text_fit":
            return (item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"])
        if kind in ("progress_bar", "rectangle", "line"):
            return (item["x_start"], item["y_start"], item["x_end"], item["y_end"])
        if kind == "icon":
            size = item["size"]
            return (
                item["x"] - size // 2,
                item["y"] - size // 2,
                item["x"] + size - size // 2,
                item["y"] + size - size // 2,
            )
        return None

    for size, items in template["layouts"].items():
        assert len(items) <= 100, size
        width, height = (int(part) for part in size.split("x"))
        all_boxes = [
            (index, item["type"], box)
            for index, item in enumerate(items)
            if (box := _box(item)) is not None
        ]
        for index, kind, box in all_boxes:
            if kind == "line":
                assert 0 <= box[0] <= box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] <= box[3] <= height, (size, index, kind, box)
            else:
                assert 0 <= box[0] < box[2] <= width, (size, index, kind, box)
                assert 0 <= box[1] < box[3] <= height, (size, index, kind, box)
        fg_boxes = [entry for entry in all_boxes if entry[1] not in ("rectangle", "line")]
        rect_boxes = [entry for entry in all_boxes if entry[1] == "rectangle"]
        line_boxes = [entry for entry in all_boxes if entry[1] == "line"]
        for r1 in range(len(rect_boxes)):
            for r2 in range(r1 + 1, len(rect_boxes)):
                i1, _, b1 = rect_boxes[r1]
                i2, _, b2 = rect_boxes[r2]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: rect {i1} {b1} overlaps rect {i2} {b2}"
        for idx in range(len(fg_boxes)):
            for jdx in range(idx + 1, len(fg_boxes)):
                i1, t1, b1 = fg_boxes[idx]
                i2, t2, b2 = fg_boxes[jdx]
                overlaps = b1[0] < b2[2] and b2[0] < b1[2] and b1[1] < b2[3] and b2[1] < b1[3]
                assert not overlaps, f"{size}: element {i1}({t1}) {b1} overlaps {i2}({t2}) {b2}"
            i1, t1, b1 = fg_boxes[idx]
            for li, _, lb in line_boxes:
                lx0, ly0, lx1, ly1 = lb
                line_box = (lx0, ly0, lx1 + (lx0 == lx1), ly1 + (ly0 == ly1))
                hits_line = (
                    b1[0] < line_box[2]
                    and line_box[0] < b1[2]
                    and b1[1] < line_box[3]
                    and line_box[1] < b1[3]
                )
                assert not hits_line, f"{size}: element {i1}({t1}) {b1} touches line {li} {lb}"
            for ri, _, rb in rect_boxes:
                rw = round(items[ri].get("width", 1))
                inside = (
                    b1[0] >= rb[0] + rw
                    and b1[2] <= rb[2] - rw
                    and b1[1] >= rb[1] + rw
                    and b1[3] <= rb[3] - rw
                )
                disjoint = b1[2] <= rb[0] or rb[2] <= b1[0] or b1[3] <= rb[1] or rb[3] <= b1[1]
                assert inside or disjoint, f"{size}: {i1}({t1}) {b1} crosses rect {ri} border {rb}"


async def test_appliance_status_renders_states_alerts_contrast_and_edge_cases(hass, wolink_entry):
    from custom_components.ble_esl.designer.specs import resolve_templates
    from scripts.designer_demo import STATES as DEMO_STATES

    assert "sensor.washer_state" in DEMO_STATES

    hass.states.async_set("sensor.washer_state", "running", {"friendly_name": "세탁기"})
    hass.states.async_set("sensor.washer_remaining", "25", {"unit_of_measurement": "min"})
    hass.states.async_set("sensor.dryer_state", "complete", {"friendly_name": "건조기"})
    hass.states.async_set("sensor.dryer_remaining", "0", {"unit_of_measurement": "min"})
    hass.states.async_set("sensor.dishwasher_state", "idle", {"friendly_name": "식기세척기"})
    hass.states.async_set("sensor.dishwasher_remaining", "1.5", {"unit_of_measurement": "h"})
    options = {
        "remaining_1": "sensor.washer_remaining",
        "appliance_2": "sensor.dryer_state",
        "remaining_2": "sensor.dryer_remaining",
        "appliance_3": "sensor.dishwasher_state",
        "remaining_3": "sensor.dishwasher_remaining",
    }

    # Completion alert highlights dryer slot + badge + banner.
    done_items = resolve_templates(
        hass, build(TEMPLATES["appliance_status"], 800, 480, "BWR", options)["payload"], set()
    )
    done_texts = [str(item.get("value", "")) for item in done_items]
    assert {"동작 중", "남은 25분", "완료됨", "대기 중", "완료 알림"} <= set(done_texts)
    assert any("건조기 작동 완료" in t for t in done_texts)
    assert any(item.get("type") == "rectangle" and item.get("fill") == "red" for item in done_items)
    assert any(
        item.get("value") == "완료 알림" and item.get("color") == "white" for item in done_items
    )
    assert any(
        item.get("type") == "icon" and item.get("value") == "check-circle-outline"
        for item in done_items
    )
    render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), done_items)

    # Error alert overrides completion alert + checks BW/BWRY/white contrast.
    hass.states.async_set("sensor.dishwasher_state", "fault", {"friendly_name": "식기세척기"})
    err_bwry = resolve_templates(
        hass,
        build(TEMPLATES["appliance_status"], 800, 480, "BWRY", {**options, "accent": "yellow"})[
            "payload"
        ],
        set(),
    )
    err_texts = [str(item.get("value", "")) for item in err_bwry]
    assert "오류 확인" in err_texts and any("식기세척기 오류 확인 필요" in t for t in err_texts)
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "yellow" for item in err_bwry
    )
    assert any(
        item.get("value") == "오류 확인" and item.get("color") == "black" for item in err_bwry
    )
    assert not any(
        item.get("type") in ("text_fit", "icon") and item.get("color") in ("yellow", "white")
        for item in err_bwry
    )

    white_items = resolve_templates(
        hass,
        build(TEMPLATES["appliance_status"], 400, 300, "BWR", {**options, "accent": "white"})[
            "payload"
        ],
        set(),
    )
    assert any(
        item.get("type") == "rectangle" and item.get("fill") == "black" for item in white_items
    )
    assert any(
        item.get("value") == "오류 확인" and item.get("color") == "white" for item in white_items
    )

    bw_items = resolve_templates(
        hass,
        build(TEMPLATES["appliance_status"], 800, 480, "BW", {**options, "accent": "red"})[
            "payload"
        ],
        set(),
    )
    assert any(item.get("type") == "rectangle" and item.get("fill") == "black" for item in bw_items)

    # All-running + paused + remaining time units (hour/sec/string/negative clamp) + compact layout checks.
    hass.states.async_set("sensor.washer_state", "paused", {"friendly_name": "세탁기"})
    hass.states.async_set("sensor.washer_remaining", "-0.4", {"unit_of_measurement": "min"})
    hass.states.async_set("sensor.dryer_state", "drying", {"friendly_name": "건조기"})
    hass.states.async_set("sensor.dryer_remaining", "90", {"unit_of_measurement": "sec"})
    hass.states.async_set("sensor.dishwasher_state", "washing", {"friendly_name": "식기세척기"})
    hass.states.async_set("sensor.dishwasher_remaining", "1.5", {"unit_of_measurement": "h"})
    run_texts = _texts(_shown(hass, "appliance_status", 800, 480, options))
    assert {"일시정지", "남은 0분", "남은 2분", "남은 1.5시간", "동작 2"} <= set(run_texts)
    assert "-0" not in str(run_texts)

    # <4" shows only the highest-priority appliance & status without unset slots or clock chrome.
    hass.states.async_set("sensor.washer_state", "finished", {"friendly_name": "세탁기"})
    assert _texts(_shown(hass, "appliance_status", 384, 184, {})) == ["세탁기", "완료됨"]

    hass.states.async_set("sensor.washer_state", "running", {"friendly_name": "세탁기"})
    hass.states.async_set("sensor.washer_remaining", "25", {"unit_of_measurement": "min"})
    hass.states.async_set("sensor.dryer_state", "complete", {"friendly_name": "건조기"})
    hass.states.async_set("sensor.dishwasher_state", "idle", {"friendly_name": "식기세척기"})
    feat_200 = _texts(_shown(hass, "appliance_status", 200, 200, options))
    assert feat_200 == ["건조기", "완료됨"]

    for cw, ch in ((104, 212), (184, 384), (384, 184), (416, 240)):
        c_texts = _texts(_shown(hass, "appliance_status", cw, ch, options))
        assert not any("갱신" in t for t in c_texts)

    # Bogus optional entity strings and non-finite/boolean states degrade safely without errors.
    for bogus in ("1.2", "sensor.", " sensor.dryer_state ", "a.b.c"):
        bogus_texts = _texts(
            _shown(
                hass,
                "appliance_status",
                800,
                480,
                {"appliance_2": bogus, "appliance_3": bogus, "remaining_1": bogus},
            )
        )
        assert bogus_texts.count("미설정") >= 2

    for bad in ("unavailable", "unknown", "nan", "inf", "-inf", "True", "False"):
        hass.states.async_set("sensor.washer_state", "running", {"friendly_name": "세탁기"})
        hass.states.async_set("sensor.washer_remaining", bad, {"unit_of_measurement": "min"})
        rem_opts = {"remaining_1": "sensor.washer_remaining"}
        bad_rendered = _shown(hass, "appliance_status", 800, 480, rem_opts)
        bad_texts = _texts(bad_rendered)
        assert "세탁기" in bad_texts and "동작 중" in bad_texts
        assert not any(bad in t or "남은 " in t for t in bad_texts)
        compact_bad = _texts(_shown(hass, "appliance_status", 212, 104, rem_opts))
        assert not any(bad in t or "남은 " in t or f"동작 · {bad}" in t for t in compact_bad)
        render_image(hass, DevicePreset("large", "large", 800, 480, "BWR"), bad_rendered)

    # All-unavailable/missing and custom states never claim all appliances are idle.
    hass.states.async_set("sensor.washer_state", "unavailable", {"friendly_name": "세탁기"})
    unavail_panel = _texts(
        _shown(hass, "appliance_status", 800, 480, {"appliance_2": "sensor.missing_dryer"})
    )
    assert "상태 대기" in unavail_panel and "가전 상태를 확인할 수 없습니다" in unavail_panel
    assert "모두 대기" not in unavail_panel and "모든 가전이 대기 중입니다" not in unavail_panel

    unavail_compact = _texts(_shown(hass, "appliance_status", 104, 212, {}))
    assert unavail_compact == ["세탁기", "응답 없음"]

    hass.states.async_set("sensor.washer_state", "spin_rinse", {"friendly_name": "세탁기"})
    custom_panel = _texts(
        _shown(hass, "appliance_status", 800, 480, {"appliance_2": "sensor.missing_dryer"})
    )
    assert "spin_rinse" in custom_panel and "세탁기 상태: spin_rinse" in custom_panel

    hass.states.async_set("sensor.washer_state", "idle", {"friendly_name": "세탁기"})
    partial_idle = _texts(
        _shown(hass, "appliance_status", 800, 480, {"appliance_2": "sensor.missing_dryer"})
    )
    assert "대기 중" in partial_idle and "대기 중인 가전이 있습니다" in partial_idle
    assert "모든 가전이 대기 중입니다" not in partial_idle

    hass.states.async_set("sensor.washer_state", "running", {"friendly_name": "세탁기"})
    hass.states.async_set("sensor.washer_remaining", "25", {"unit_of_measurement": "min"})
    hass.states.async_set("sensor.dryer_state", "complete", {"friendly_name": "건조기"})
    hass.states.async_set("sensor.dishwasher_state", "idle", {"friendly_name": "식기세척기"})
    designer = hass.data[KEY]
    preview = await designer.preview_design_template(wolink_entry, "appliance_status", options)
    assert preview["png"].startswith("data:image/png;base64,")
    applied = await designer.apply_design_template(wolink_entry, "appliance_status", options)
    assert applied["issues"] == [] and applied["different_pixels"] == 0

    for size in TEMPLATES["appliance_status"]["layouts"]:
        w, h = (int(part) for part in size.split("x"))
        preset = DevicePreset("test", "test", w, h, "BWR")
        elements, imported, issues = elements_from(
            build(TEMPLATES["appliance_status"], w, h, "BWR", options)["payload"], preset
        )
        assert issues == [], size
        original, rebuilt = stable_template_payloads(hass, imported, elements)
        assert different_pixels(hass, preset, original, rebuilt) == 0, size


def test_under_4_inch_templates_enforce_readable_font_floors():
    size_floors = {
        "200x200": (22, 48, 16, 4),
        "212x104": (20, 40, 16, 4),
        "250x122": (20, 40, 16, 4),
        "250x128": (20, 40, 16, 4),
        "250x132": (20, 40, 16, 4),
        "104x212": (18, 34, 14, 4),
        "122x250": (18, 34, 14, 4),
        "128x250": (18, 34, 14, 4),
        "132x250": (18, 34, 14, 4),
        "296x128": (22, 48, 18, 4),
        "296x152": (22, 48, 18, 4),
        "128x296": (20, 40, 15, 4),
        "152x296": (20, 40, 15, 4),
        "384x184": (24, 60, 18, 5),
        "416x240": (24, 60, 18, 5),
        "184x384": (22, 52, 16, 5),
        "240x416": (22, 52, 16, 5),
    }
    templates = (
        "weather_outdoor",
        "weather_commute",
        "indoor_climate",
        "calendar_weather",
        "home_presence",
        "energy_power",
        "ev_charging",
        "appliance_status",
    )
    for name in templates:
        layouts = TEMPLATES[name]["layouts"]
        for size, (min_sec, min_hero, min_ms, max_cnt) in size_floors.items():
            texts = [i for i in layouts[size] if i.get("type") in ("text_fit", "text")]
            assert texts, (name, size)
            assert len(texts) <= max_cnt, (name, size, len(texts))
            sizes = [i["size"] for i in texts]
            assert min(sizes) >= min_sec, (name, size, sizes)
            assert max(sizes) >= min_hero, (name, size, sizes)
            fit_mins = [i["min_size"] for i in texts if i.get("type") == "text_fit"]
            assert fit_mins and min(fit_mins) >= min_ms, (name, size, fit_mins)
            assert not any("갱신" in str(i.get("value", "")) for i in texts), (name, size)
            assert not any(i.get("type") == "rectangle" for i in layouts[size]), (name, size)


@pytest.mark.parametrize("accent", ["white", "yellow"])
@pytest.mark.parametrize(
    ("width", "height"),
    [(200, 200), (212, 104), (104, 212), (296, 128), (184, 384), (384, 184)],
)
async def test_under_4_inch_weather_white_bg_avoids_low_contrast_accent_colors(
    hass, accent, width, height
):
    from datetime import timedelta

    from freezegun import freeze_time
    from homeassistant.util import dt as dt_util

    today = dt_util.start_of_local_day() + timedelta(hours=6, minutes=30)

    def at(hour):
        return (dt_util.start_of_local_day() + timedelta(hours=hour)).isoformat()

    hass.states.async_set("weather.home", "snowy", {"temperature": -1, "temperature_unit": "°C"})
    variables = {
        "fc": {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": at(12),
                        "condition": "snowy",
                        "temperature": 3,
                        "templow": -4,
                        "precipitation_probability": 80,
                        "precipitation": 2,
                    }
                ]
            }
        },
        "fc_hourly": {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": at(h),
                        "condition": "snowy",
                        "temperature": 0,
                        "precipitation_probability": 80,
                    }
                    for h in (7, 19)
                ]
            }
        },
    }

    def enclosing_fill(rects, item):
        cx = item["x"] + item.get("width", 0) / 2
        cy = item["y"] + item.get("height", 0) / 2
        for rect in rects:
            if rect["x_start"] <= cx <= rect["x_end"] and rect["y_start"] <= cy <= rect["y_end"]:
                return rect["fill"]
        return "white"

    with freeze_time(today, real_asyncio=True):
        for name in ("weather_outdoor", "weather_commute"):
            built = build(TEMPLATES[name], width, height, "BWRY", {"accent": accent})
            rendered = resolve_templates(hass, built["payload"], set(), variables)
            rects = [
                item
                for item in rendered
                if item.get("type") == "rectangle" and item.get("fill") not in (None, "white")
            ]
            for item in rendered:
                if item.get("type") not in ("text", "text_fit", "icon", "line"):
                    continue
                if item.get("type") == "line":
                    cx = (item["x_start"] + item["x_end"]) / 2
                    cy = (item["y_start"] + item["y_end"]) / 2
                    bg = enclosing_fill(rects, {"x": cx, "y": cy})
                    color = item.get("fill", "black")
                else:
                    bg = enclosing_fill(rects, item)
                    color = item.get("color", "black")
                if bg == "white":
                    assert color not in ("white", "yellow"), (name, width, height, accent, item)
                elif bg == "yellow":
                    assert color == "black", (name, width, height, accent, item)
                elif bg == "black":
                    assert color == "white", (name, width, height, accent, item)
