"""Element transforms preserve live component behavior and exported pixels."""

import base64
from io import BytesIO
from types import SimpleNamespace

from PIL import Image, ImageChops
import pytest

from custom_components.ble_esl.designer import KEY
from custom_components.ble_esl.designer.layout import compile_payload, validate
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.renderer import render_image


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


async def test_automation_keeps_original_component_configuration(hass, wolink_entry):
    hass.states.async_set("binary_sensor.laundry", "on")
    source = icon_document(rotation=0)
    source["elements"][0]["field_templates"] = {
        "color": "{{ 'red' if value == 'on' else 'black' }}"
    }
    result = await hass.data[KEY].automation(wolink_entry, source)
    action = result["automation"]["actions"][0]
    assert action["data"] == {"use_saved_design": True}
    assert "field_templates" in result["design_source"]


async def test_new_automation_triggers_on_its_input_states(hass, wolink_entry):
    hass.states.async_set("binary_sensor.laundry", "on")
    result = await hass.data[KEY].automation(wolink_entry, icon_document(rotation=0))
    assert result["automation"]["triggers"] == [
        {
            "trigger": "event",
            "event_type": "ble_esl_inputs_changed",
            "event_data": {"entry_id": wolink_entry.entry_id},
            "id": "ble_esl_inputs",
        }
    ]


async def test_automation_write_resolves_current_rules_after_ha_renders_action_data(
    hass, wolink_entry
):
    from homeassistant.helpers.template import Template

    from custom_components.ble_esl.designer.automation_source import decode_design
    from custom_components.ble_esl.services import build_write_job_from_data

    hass.states.async_set("binary_sensor.laundry", "on")
    source = icon_document()
    source["elements"][0]["field_templates"] = {
        "color": "{{ 'red' if value == 'on' else 'black' }}"
    }
    exported = await hass.data[KEY].export(wolink_entry, source)
    import yaml

    action = yaml.safe_load(exported["service"])
    data = {**action["data"], "design": Template(action["data"]["design"], hass).async_render()}
    assert (
        decode_design(data["design"])["elements"][0]["field_templates"]
        == source["elements"][0]["field_templates"]
    )
    first = await build_write_job_from_data(hass, wolink_entry, data)
    hass.states.async_set("binary_sensor.laundry", "off")
    second = await build_write_job_from_data(hass, wolink_entry, data)
    assert first.image_png != second.image_png


async def test_input_state_change_runs_the_exported_automation(hass, wolink_entry, tag_writer):
    from homeassistant.setup import async_setup_component

    hass.states.async_set("binary_sensor.laundry", "off")
    await hass.data[KEY].save(wolink_entry, icon_document())
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


async def test_automation_passes_script_variables_to_native_templates(hass, wolink_entry):
    from homeassistant.helpers.template import Template

    from custom_components.ble_esl.services import build_write_job_from_data

    source = {
        "version": 1,
        "elements": [
            {
                "id": "native",
                "type": "imagespec",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 40,
                "spec": {"type": "text", "value": "{{ message }}", "size": 24},
            }
        ],
    }
    result = await hass.data[KEY].automation(
        wolink_entry, source, preview_variables={"message": "preview only"}
    )
    data = result["automation"]["actions"][0]["data"]
    assert data["use_saved_design"] is True
    assert "design" not in data
    await hass.data[KEY].save(wolink_entry, source)
    assert data["design_variables"] == {"message": "{{ message }}"}
    data["design_variables"] = {
        key: Template(value, hass).async_render({"message": "Actual run"})
        for key, value in data["design_variables"].items()
    }
    job = await build_write_job_from_data(hass, wolink_entry, data)
    assert job.image_png


async def test_automation_templates_can_read_trigger_objects(hass, wolink_entry):
    from homeassistant.helpers.template import Template

    from custom_components.ble_esl.services import build_write_job_from_data

    source = {
        "version": 1,
        "elements": [
            {
                "id": "native",
                "type": "imagespec",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 40,
                "spec": {"type": "text", "value": "{{ trigger.to_state.state }}", "size": 24},
            }
        ],
    }
    result = await hass.data[KEY].automation(
        wolink_entry, source, preview_variables={"trigger": {"to_state": {"state": "off"}}}
    )
    data = result["automation"]["actions"][0]["data"]
    await hass.data[KEY].save(wolink_entry, source)
    assert data["design_variables"] == {
        "trigger": {"to_state": {"state": '{{ trigger["to_state"]["state"] }}'}}
    }
    state = SimpleNamespace(state="on")
    variables = {"trigger": SimpleNamespace(to_state=state)}
    data["design_variables"] = {
        "trigger": {
            "to_state": {
                "state": Template(
                    data["design_variables"]["trigger"]["to_state"]["state"], hass
                ).async_render(variables)
            }
        }
    }
    assert (await build_write_job_from_data(hass, wolink_entry, data)).image_png


async def test_invalid_design_specs_raise_a_service_error(hass, wolink_entry):
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.ble_esl.services import build_write_job_from_data

    source = {
        "version": 1,
        "elements": [
            {
                "id": "native",
                "type": "imagespec",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 40,
                "spec": {"type": "text", "value": "{{ message }}", "size": 24},
            }
        ],
    }
    result = await hass.data[KEY].automation(
        wolink_entry, source, preview_variables={"message": "x"}
    )
    data = result["automation"]["actions"][0]["data"]
    await hass.data[KEY].save(wolink_entry, source)
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


async def test_free_angle_rotation_changes_pixels_and_preserves_source(hass, wolink_entry):
    source = icon_document(rotation=37.5)
    hass.states.async_set("binary_sensor.laundry", "on")
    result = await hass.data[KEY].preview(wolink_entry, source)
    unrotated = await hass.data[KEY].preview(wolink_entry, icon_document(rotation=0))
    assert result["png"] != unrotated["png"]
    exported = await hass.data[KEY].export(wolink_entry, source)
    assert exported["validation_errors"] == []
    assert exported["payload_data"][0]["type"] == "dlimg"
    actual = await hass.async_add_executor_job(
        lambda: render_image(hass, wolink_entry.runtime_data.preset, exported["payload_data"])
    )
    preview_image = Image.open(BytesIO(base64.b64decode(result["png"].split(",")[1]))).convert(
        "RGB"
    )
    assert ImageChops.difference(actual, preview_image).getbbox() is None
    from custom_components.ble_esl.designer.automation_source import decode_design

    assert decode_design(exported["design_source"])["elements"][0]["rotation"] == 37.5


@pytest.mark.parametrize("width,height", [(40, 30), (31, 22), (60, 40)])
def test_rotated_size_matches_pillow_for_free_angles(width, height):
    from custom_components.ble_esl.renderer import rotated_size

    for angle in (0, 17, 37.5, 90, 123, 180, 270, 359, -35):
        expected = Image.new("RGBA", (width, height)).rotate(-angle, expand=True).size
        assert rotated_size(width, height, angle) == expected


async def test_tag_orientation_changes_editor_size_and_guarded_output(hass, wolink_entry):
    from custom_components.ble_esl.services import build_write_job_from_data

    hass.config_entries.async_update_entry(
        wolink_entry, options={**wolink_entry.options, "display_rotation": 90}
    )
    designer = hass.data[KEY]
    physical = wolink_entry.runtime_data.preset
    logical = designer.preset(wolink_entry)
    assert (logical.width, logical.height) == (physical.height, physical.width)
    source = icon_document(rotation=0)
    preview = await designer.preview(wolink_entry, source)
    data = {"design": source, "payload": preview["payload"]}
    job = await build_write_job_from_data(hass, wolink_entry, data)
    assert job.image.size == (physical.width, physical.height)
    editor_image = Image.open(BytesIO(base64.b64decode(preview["png"].split(",")[1]))).convert(
        "RGB"
    )
    assert ImageChops.difference(job.image, editor_image.rotate(-90, expand=True)).getbbox() is None


async def test_orientation_setting_is_persisted_through_editor_api(
    hass, wolink_entry, hass_ws_client
):
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "ble_esl/designer",
            "action": "orientation",
            "entry_id": wolink_entry.entry_id,
            "rotation": 270,
        }
    )
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["rotation"] == 270
    assert wolink_entry.options["display_rotation"] == 270


async def test_saved_design_refresh_uses_the_current_layout_not_the_exported_copy(
    hass, wolink_entry
):
    from custom_components.ble_esl.services import build_write_job_from_data

    designer = hass.data[KEY]
    hass.states.async_set("binary_sensor.laundry", "on")
    old = icon_document(rotation=0)
    data = {"use_saved_design": True}
    await designer.save(wolink_entry, old)
    before = await build_write_job_from_data(hass, wolink_entry, data)
    await designer.save(wolink_entry, icon_document(rotation=37.5))
    after = await build_write_job_from_data(hass, wolink_entry, data)
    assert before.image_png != after.image_png


async def test_saved_design_service_needs_no_embedded_payload(hass, wolink_entry):
    from custom_components.ble_esl.services import (
        WRITE_GUARDED_SERVICE_SCHEMA,
        WRITE_SERVICE_SCHEMA,
    )

    for schema in (WRITE_SERVICE_SCHEMA, WRITE_GUARDED_SERVICE_SCHEMA):
        assert schema({"use_saved_design": True}) == {
            "use_saved_design": True,
            "skip_unchanged": True,
        }


async def test_saved_inputs_follow_edits_and_template_dependencies(hass, wolink_entry):
    designer = hass.data[KEY]
    events = []
    hass.bus.async_listen("ble_esl_inputs_changed", lambda event: events.append(event.data))
    hass.states.async_set("binary_sensor.laundry", "on")
    hass.states.async_set("sensor.color", "red")
    source = icon_document(rotation=0)
    source["elements"][0]["field_templates"] = {"color": "{{ states('sensor.color') }}"}
    await designer.save(wolink_entry, source)
    await hass.async_block_till_done()
    events.clear()
    hass.states.async_set("sensor.color", "black")
    await hass.async_block_till_done()
    assert events == [{"entry_id": wolink_entry.entry_id, "entity_id": "sensor.color"}]
    source["elements"][0]["entity_id"] = "binary_sensor.other"
    source["elements"][0]["field_templates"] = {}
    await designer.save(wolink_entry, source)
    await hass.async_block_till_done()
    events.clear()
    hass.states.async_set("binary_sensor.laundry", "off")
    hass.states.async_set("sensor.color", "red")
    await hass.async_block_till_done()
    assert events == []
    hass.states.async_set("binary_sensor.other", "on")
    await hass.async_block_till_done()
    assert events == [{"entry_id": wolink_entry.entry_id, "entity_id": "binary_sensor.other"}]


async def test_saved_inputs_retrack_conditional_reads_and_stop_on_unload(hass, wolink_entry):
    designer = hass.data[KEY]
    events = []
    hass.bus.async_listen("ble_esl_inputs_changed", lambda event: events.append(event.data))
    hass.states.async_set("binary_sensor.laundry", "on")
    hass.states.async_set("sensor.primary_color", "black")
    hass.states.async_set("sensor.backup_color", "red")
    source = icon_document(rotation=0)
    source["elements"][0]["field_templates"] = {
        "color": "{{ states('sensor.primary_color') if value == 'on' else states('sensor.backup_color') }}"
    }
    await designer.save(wolink_entry, source)
    await hass.async_block_till_done()
    events.clear()
    hass.states.async_set("sensor.backup_color", "white")
    await hass.async_block_till_done()
    assert events == []
    hass.states.async_set("binary_sensor.laundry", "off")
    await hass.async_block_till_done()
    events.clear()
    hass.states.async_set("sensor.backup_color", "black")
    await hass.async_block_till_done()
    assert events == [{"entry_id": wolink_entry.entry_id, "entity_id": "sensor.backup_color"}]
    designer.inputs.untrack(wolink_entry.entry_id)
    events.clear()
    hass.states.async_set("sensor.backup_color", "red")
    await hass.async_block_till_done()
    assert events == []
    designer.inputs.track(wolink_entry.entry_id)
    hass.states.async_set("sensor.backup_color", "black")
    await hass.async_block_till_done()
    assert events == [{"entry_id": wolink_entry.entry_id, "entity_id": "sensor.backup_color"}]


async def test_saved_design_runs_with_real_automation_trigger_state(hass, wolink_entry, tag_writer):
    from homeassistant.setup import async_setup_component

    source = {
        "version": 1,
        "elements": [
            {
                "id": "native",
                "type": "imagespec",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 40,
                "spec": {"type": "text", "value": "{{ trigger.to_state.state }}", "size": 24},
            }
        ],
    }
    designer = hass.data[KEY]
    hass.states.async_set("sensor.trigger_source", "off")
    await designer.save(wolink_entry, source)
    result = await designer.automation(
        wolink_entry, source, preview_variables={"trigger": {"to_state": {"state": "off"}}}
    )
    config = {
        "id": "saved-context",
        **result["automation"],
        "triggers": [
            {
                "trigger": "state",
                "entity_id": "sensor.trigger_source",
                "not_to": ["unknown", "unavailable"],
            }
        ],
    }
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_block_till_done()
    hass.states.async_set("sensor.trigger_source", "on")
    await hass.async_block_till_done()
    assert tag_writer.write_prepared.await_count == 1
    assert wolink_entry.runtime_data.reports.last["success"] is True


async def test_saved_inputs_keep_display_on_unavailable_and_refresh_on_recovery(hass, wolink_entry):
    designer = hass.data[KEY]
    hass.states.async_set("binary_sensor.laundry", "off")
    await designer.save(wolink_entry, icon_document())
    await hass.async_block_till_done()
    events = []
    hass.bus.async_listen("ble_esl_inputs_changed", lambda event: events.append(event.data))
    hass.states.async_set("binary_sensor.laundry", "unavailable")
    await hass.async_block_till_done()
    assert events == []
    hass.states.async_set("binary_sensor.laundry", "on")
    await hass.async_block_till_done()
    assert events == [{"entry_id": wolink_entry.entry_id, "entity_id": "binary_sensor.laundry"}]
