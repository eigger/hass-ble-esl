"""Missing preview values fail without Home Assistant warning spam."""

from copy import deepcopy

import pytest

from custom_components.ble_esl.designer import KEY
from custom_components.ble_esl.designer.specs import MissingTemplateParameter, resolve_templates


def test_reported_variable_templates_require_typed_preview_values(hass, caplog):
    source = {
        "font": "{{ font_bold }}",
        "color_s3": "{{ 'red' if is_alert_s3 else 'black' }}",
        "name_s4": "{{ name_s4 }}",
        "value_s4": "{{ val_s4 }}",
        "color_s4": "{{ 'red' if is_alert_s4 else 'black' }}",
    }
    original = deepcopy(source)
    parameters = {
        "font_bold": "fonts/CookieRunBold.ttf",
        "is_alert_s3": True,
        "name_s4": "Temperature",
        "val_s4": 23,
        "is_alert_s4": False,
    }
    for template in source.values():
        with pytest.raises(MissingTemplateParameter):
            resolve_templates(hass, template, set())
    assert resolve_templates(hass, source, set(), parameters) == {
        "font": "fonts/CookieRunBold.ttf",
        "color_s3": "red",
        "name_s4": "Temperature",
        "value_s4": 23,
        "color_s4": "black",
    }
    assert source == original
    assert not any("Template variable warning" in record.message for record in caplog.records)


async def test_automation_export_blocks_sampled_polygon_coordinates(hass, wolink_entry):
    document = {
        "version": 1,
        "elements": [
            {
                "id": "polygon",
                "type": "imagespec",
                "x": 5,
                "y": 5,
                "width": 40,
                "height": 40,
                "spec": {"type": "polygon", "points": "{{ corners }}", "fill": "black"},
            }
        ],
    }
    result = await hass.data[KEY].export(
        wolink_entry,
        document,
        preview_variables={"corners": "0,0;100,0;50,100"},
        automation_edit=True,
    )
    assert result["validation_errors"]
    assert result["payload_data"] is None
    assert document["elements"][0]["spec"]["points"] == "{{ corners }}"
