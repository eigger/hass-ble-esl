"""Design templates: format, parameter substitution, layouts and the designer API."""

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


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
@pytest.mark.parametrize(("width", "height"), SIZES)
@pytest.mark.parametrize("colors", ["BW", "BWR", "BWRY"])
async def test_bundled_template_imports_and_draws_exactly(hass, template_id, width, height, colors):
    preset = DevicePreset("test", "test", width, height, colors)
    built = build(TEMPLATES[template_id], width, height, colors)
    elements, imported, issues = elements_from(built["payload"], preset)
    assert issues == []
    assert len(elements) == len(built["payload"])
    original, rebuilt = payloads(hass, imported, elements)
    assert different_pixels(hass, preset, original, rebuilt, built["background"]) == 0
    for item in original:
        for key in ("x", "y"):
            assert 0 <= item[key] <= (width if key == "x" else height)


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
async def test_bundled_automation_is_a_valid_home_assistant_automation(hass, template_id):
    template = TEMPLATES[template_id]
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
    for bad in ("{{ x }}", "it's", "a\\b", "a\nb"):
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
        (("&a", "&a"), None),
    ],
)
def test_invalid_templates_are_rejected(change, message):
    text = MINIMAL.replace(*change)
    if message is None:
        with pytest.raises((ValueError, vol.Invalid)):
            parse_template("x: &a 1\ny: *a\n")
        return
    with pytest.raises(vol.Invalid, match=message):
        parse_template(text)


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
    assert draft["actions"][0]["action"] == "ble_esl.write"
    assert "{{ now()" in yaml.dump(draft["actions"])


async def test_applying_rejects_unknown_template_and_missing_font(hass, wolink_entry):
    designer = hass.data[KEY]
    with pytest.raises(HomeAssistantError, match="no design template"):
        await designer.apply_design_template(wolink_entry, "nope")
    with pytest.raises(HomeAssistantError, match="Font not found"):
        await designer.apply_design_template(wolink_entry, "date", {"font": "Missing.ttf"})
