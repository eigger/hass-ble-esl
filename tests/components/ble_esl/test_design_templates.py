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
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.renderer import render_image

TEMPLATES = load_templates()
SIZES = [(250, 128), (296, 128), (400, 300), (800, 480)]

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


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
@pytest.mark.parametrize(("width", "height"), SIZES)
@pytest.mark.parametrize("colors", ["BW", "BWR", "BWRY"])
async def test_bundled_template_imports_and_draws_exactly(hass, template_id, width, height, colors):
    preset = DevicePreset("test", "test", width, height, colors)
    seed_entities(hass, TEMPLATES[template_id])
    built = build(TEMPLATES[template_id], width, height, colors)
    elements, imported, issues = elements_from(built["payload"], preset)
    assert issues == []
    assert len(elements) == len(built["payload"])
    original, rebuilt = payloads(hass, imported, elements)
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
        "actions": [{"action": "ble_esl.write", "data": {"payload": built["payload"]}}],
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
                left, _, right, _ = _frame(item)
                assert left >= qr[2] or right <= qr[0], size


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
        original, rebuilt = payloads(hass, imported, elements)
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
