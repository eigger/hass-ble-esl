"""Element transforms preserve live component behavior and exported pixels."""

import base64
from io import BytesIO
import json
from types import SimpleNamespace

from PIL import Image, ImageChops
import pytest

from custom_components.ble_esl.designer import KEY
from custom_components.ble_esl.designer.layout import compile_payload, validate
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.renderer import render_image


def legacy_design(document):
    """The ``design`` an older release saved in an action: still accepted when it runs."""
    return "{{ " + json.dumps(json.dumps(document)) + " | from_json }}"


def icon_document(rotation=90, visible=True):
    return {
        "version": 1,
        "elements": [
            {
                "id": "laundry",
                "type": "conditional_icon",
                "entity_id": "binary_sensor.laundry",
                "data_field": "state",
                "icon": "mdi:help",
                "icon_rules": [
                    {"kind": "state", "state": "on", "icon": "mdi:washing-machine"},
                    {"kind": "state", "state": "off", "icon": "mdi:washing-machine-off"},
                ],
                "x": 60,
                "y": 30,
                "width": 40,
                "height": 30,
                "rotation": rotation,
                "visible": visible,
            }
        ],
    }


async def test_rotation_preserves_rules_and_refreshes_from_the_entity(hass):
    preset = DevicePreset("test", "Test", 200, 100, "BWR")
    hass.states.async_set("binary_sensor.laundry", "on")
    doc = validate(icon_document(), preset)
    payload = compile_payload(hass, doc)
    assert doc["elements"][0]["type"] == "conditional_icon"
    assert doc["elements"][0]["icon_rules"][0]["state"] == "on"
    assert payload[0]["type"] == "group" and payload[0]["rotate"] == 90
    assert payload[0]["elements"][0]["value"] == "mdi:washing-machine"
    hass.states.async_set("binary_sensor.laundry", "off")
    assert compile_payload(hass, doc)[0]["elements"][0]["value"] == "mdi:washing-machine-off"


@pytest.mark.parametrize(
    "kind", ["text", "sensor", "icon", "conditional_icon", "rectangle", "imagespec"]
)
async def test_rotation_is_available_for_every_component_format(hass, kind):
    hass.states.async_set("binary_sensor.laundry", "on")
    raw = icon_document()
    raw["elements"][0].update(
        type=kind,
        text="Laundry",
        spec={"type": "rectangle", "fill": "red"} if kind == "imagespec" else {},
    )
    if kind != "imagespec":
        del raw["elements"][0]["spec"]
    doc = validate(raw, DevicePreset("test", "Test", 200, 100, "BWR"))
    assert compile_payload(hass, doc)[0]["rotate"] == 90


async def test_rotated_preview_matches_export_and_layer_bounds(hass, wolink_entry):
    hass.states.async_set("binary_sensor.laundry", "on")
    designer = hass.data[KEY]
    doc = icon_document()
    result = await designer.preview(wolink_entry, doc)
    image = Image.open(BytesIO(base64.b64decode(result["png"].split(",")[1]))).convert("RGB")
    expected = await hass.async_add_executor_job(
        lambda: render_image(
            hass, wolink_entry.runtime_data.preset, result["payload"], background="white"
        )
    )
    assert ImageChops.difference(image, expected).getbbox() is None
    assert result["layers"]["_bounds"]["laundry"] is not None


async def test_hidden_icon_ghosts_are_editing_metadata_only(hass, wolink_entry):
    hass.states.async_set("binary_sensor.laundry", "off")
    result = await hass.data[KEY].preview(wolink_entry, icon_document(visible=False))
    assert result["payload"] == []
    image = Image.open(BytesIO(base64.b64decode(result["png"].split(",")[1]))).convert("RGB")
    assert image.getextrema() == ((255, 255),) * 3
    assert result["layers"]["_ghosts"]["laundry"].startswith("data:image/png")
    assert result["layers"]["_ghost_bounds"]["laundry"] is not None


async def test_automation_keeps_only_the_payload(hass, wolink_entry):
    hass.states.async_set("binary_sensor.laundry", "on")
    source = icon_document(rotation=0)
    source["elements"][0]["field_templates"] = {
        "color": "{{ 'red' if value == 'on' else 'black' }}"
    }
    result = await hass.data[KEY].automation(wolink_entry, source)
    data = result["automation"]["actions"][0]["data"]
    assert set(data) == {"background", "payload"}
    assert "as of now" in " ".join(result["warnings"])


async def test_new_automation_triggers_on_its_input_states(hass, wolink_entry):
    hass.states.async_set("binary_sensor.laundry", "on")
    result = await hass.data[KEY].automation(wolink_entry, icon_document(rotation=0))
    assert result["automation"]["triggers"] == [
        {
            "trigger": "state",
            "entity_id": ["binary_sensor.laundry"],
            "not_to": ["unavailable", "unknown"],
        }
    ]


async def test_a_design_saved_by_an_older_release_still_resolves_current_rules(hass, wolink_entry):
    from homeassistant.helpers.template import Template

    from custom_components.ble_esl.services import build_write_job_from_data

    hass.states.async_set("binary_sensor.laundry", "on")
    source = icon_document()
    source["elements"][0]["field_templates"] = {
        "color": "{{ 'red' if value == 'on' else 'black' }}"
    }
    design = legacy_design(source)
    data = {"design": Template(design, hass).async_render(), "payload": []}
    first = await build_write_job_from_data(hass, wolink_entry, data)
    hass.states.async_set("binary_sensor.laundry", "off")
    second = await build_write_job_from_data(hass, wolink_entry, data)
    assert first.image_png != second.image_png


async def test_input_state_change_runs_the_exported_automation(hass, wolink_entry, tag_writer):
    from homeassistant.setup import async_setup_component

    hass.states.async_set("binary_sensor.laundry", "off")
    result = await hass.data[KEY].automation(wolink_entry, icon_document())
    config = {"id": "live-tag", **result["automation"]}
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_block_till_done()
    hass.states.async_set("binary_sensor.laundry", "on")
    await hass.async_block_till_done()
    assert tag_writer.write_prepared.await_count == 1
    hass.states.async_set("binary_sensor.laundry", "off")
    await hass.async_block_till_done()
    assert tag_writer.write_prepared.await_count == 2


def native_text(value):
    return {
        "version": 1,
        "elements": [
            {
                "id": "native",
                "type": "imagespec",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 40,
                "spec": {"type": "text", "value": value, "size": 24},
            }
        ],
    }


async def test_automation_passes_script_variables_to_native_templates(hass, wolink_entry):
    from homeassistant.helpers.template import Template

    from custom_components.ble_esl.services import build_write_job_from_data

    result = await hass.data[KEY].automation(
        wolink_entry, native_text("{{ message }}"), preview_variables={"message": "preview only"}
    )
    data = result["automation"]["actions"][0]["data"]
    assert set(data) == {"background", "payload"}
    assert "preview only" not in json.dumps(data)
    assert data["payload"][0]["value"] == "{{ message }}"
    # Home Assistant renders the action data with the automation's variables.
    rendered = [
        {**item, "value": Template(item["value"], hass).async_render({"message": "Actual run"})}
        for item in data["payload"]
    ]
    job = await build_write_job_from_data(hass, wolink_entry, {**data, "payload": rendered})
    assert job.image_png


async def test_automation_templates_can_read_trigger_objects(hass, wolink_entry):
    from homeassistant.helpers.template import Template

    from custom_components.ble_esl.services import build_write_job_from_data

    result = await hass.data[KEY].automation(
        wolink_entry,
        native_text("{{ trigger.to_state.state }}"),
        preview_variables={"trigger": {"to_state": {"state": "off"}}},
    )
    data = result["automation"]["actions"][0]["data"]
    assert data["payload"][0]["value"] == "{{ trigger.to_state.state }}"
    variables = {"trigger": SimpleNamespace(to_state=SimpleNamespace(state="on"))}
    rendered = [
        {**item, "value": Template(item["value"], hass).async_render(variables)}
        for item in data["payload"]
    ]
    assert (
        await build_write_job_from_data(hass, wolink_entry, {**data, "payload": rendered})
    ).image_png


async def test_invalid_design_specs_raise_a_service_error(hass, wolink_entry):
    """The ``design_specs`` an older release saved are still checked when they run."""
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.ble_esl.services import build_write_job_from_data

    data = {"design": legacy_design(native_text("{{ message }}")), "payload": []}
    for bad in ("oops", {"type": "row"}, {"value": "x"}):
        with pytest.raises(ServiceValidationError):
            await build_write_job_from_data(
                hass, wolink_entry, {**data, "design_specs": {"native": bad}}
            )


async def test_field_hidden_icon_with_null_glyph_still_has_an_editing_ghost(hass, wolink_entry):
    hass.states.async_set("binary_sensor.laundry", "on")
    source = icon_document(rotation=0)
    source["elements"][0]["field_templates"] = {"visible": "{{ false }}", "icon": "{{ none }}"}
    result = await hass.data[KEY].preview(wolink_entry, source)
    assert result["payload"] == []
    assert result["layers"]["_ghost_bounds"]["laundry"]


async def test_free_angle_rotation_previews_but_a_payload_cannot_hold_it(hass, wolink_entry):
    """An older design may turn an element by any angle: it still draws, but cannot be saved."""
    source = icon_document(rotation=37.5)
    hass.states.async_set("binary_sensor.laundry", "on")
    result = await hass.data[KEY].preview(wolink_entry, source)
    unrotated = await hass.data[KEY].preview(wolink_entry, icon_document(rotation=0))
    assert result["png"] != unrotated["png"]
    exported = await hass.data[KEY].export(wolink_entry, source)
    assert exported["payload_data"] is None
    assert exported["validation_errors"] == [
        "blocking: laundry: a payload turns elements in steps of 90°, not 37.5°"
    ]
    # Steps of 90° are payload data.
    turned = await hass.data[KEY].export(wolink_entry, icon_document(rotation=270))
    assert turned["validation_errors"] == []
    assert turned["payload_data"][0]["rotate"] == 270


@pytest.mark.parametrize("width,height", [(40, 30), (31, 22), (60, 40)])
def test_rotated_size_matches_pillow_for_free_angles(width, height):
    from custom_components.ble_esl.renderer import rotated_size

    for angle in (0, 17, 37.5, 90, 123, 180, 270, 359, -35):
        expected = Image.new("RGBA", (width, height)).rotate(-angle, expand=True).size
        assert rotated_size(width, height, angle) == expected


async def test_design_orientation_sets_canvas_export_and_written_output(hass, wolink_entry):
    from custom_components.ble_esl.services import build_write_job_from_data

    designer = hass.data[KEY]
    physical = wolink_entry.runtime_data.preset
    source = {**icon_document(rotation=0), "rotate": 90}
    logical = designer.preset(wolink_entry, source["rotate"])
    assert (logical.width, logical.height) == (physical.height, physical.width)
    assert "display_rotation" not in wolink_entry.options

    preview = await designer.preview(wolink_entry, source)
    exported = await designer.export(wolink_entry, source)
    assert exported["rotate"] == 90
    assert "rotate: 90" in exported["service"]
    upright = await designer.export(wolink_entry, icon_document(rotation=0))
    assert upright["rotate"] == 0
    assert "rotate:" not in upright["service"]

    # A design an older release saved carries the orientation; an explicit `rotate` overrides it.
    job = await build_write_job_from_data(
        hass, wolink_entry, {"design": legacy_design(source), "payload": []}
    )
    assert job.image.size == (physical.width, physical.height)
    editor_image = Image.open(BytesIO(base64.b64decode(preview["png"].split(",")[1]))).convert(
        "RGB"
    )
    assert ImageChops.difference(job.image, editor_image.rotate(-90, expand=True)).getbbox() is None
    plain_job = await build_write_job_from_data(
        hass,
        wolink_entry,
        {"payload": exported["payload_data"], "rotate": 90, "background": "white"},
    )
    assert ImageChops.difference(plain_job.image, job.image).getbbox() is None


async def test_import_payload_uses_the_automation_orientation(hass, wolink_entry, hass_ws_client):
    designer = hass.data[KEY]
    physical = wolink_entry.runtime_data.preset
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "ble_esl/designer",
            "action": "import_payload",
            "entry_id": wolink_entry.entry_id,
            "payload": [{"type": "text", "value": "Hi", "x": 2, "y": 2, "size": 12}],
            "rotation": 90,
        }
    )
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["issues"] == []
    assert response["result"]["different_pixels"] == 0
    assert designer.preset(wolink_entry).width == physical.width
