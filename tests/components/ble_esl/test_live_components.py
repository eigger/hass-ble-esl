"""A payload saved from the designer follows the entities of the components it was drawn from."""

from custom_components.ble_esl.designer import KEY
from custom_components.ble_esl.designer.specs import resolve_templates

BOX = {"x": 4, "y": 4, "width": 120, "height": 40}


def element(kind, id_="e", **fields):
    return {"id": id_, "type": kind, **BOX, **fields}


def document(*elements):
    return {"version": 1, "elements": list(elements)}


async def export(hass, entry, *elements):
    result = await hass.data[KEY].export(entry, document(*elements))
    assert result["validation_errors"] == []
    return result


def drawn(hass, result):
    """The saved payload as Home Assistant renders it with the entities as they are now."""
    return resolve_templates(hass, result["payload_data"], set())


async def test_a_sensor_value_follows_its_entity(hass, wolink_entry):
    hass.states.async_set("sensor.temp", "21.26", {"unit_of_measurement": "°C"})
    result = await export(
        hass, wolink_entry, element("sensor", entity_id="sensor.temp", decimals=1)
    )
    assert result["frozen"] == []
    assert drawn(hass, result)[-1]["value"] == "21.3 °C"
    hass.states.async_set("sensor.temp", "30", {"unit_of_measurement": "°C"})
    assert drawn(hass, result)[-1]["value"] == "30.0 °C"


async def test_a_data_field_text_follows_its_entity(hass, wolink_entry):
    hass.states.async_set("sensor.mode", "eco", {"level": "low"})
    result = await export(
        hass,
        wolink_entry,
        element("text", "state", entity_id="sensor.mode", data_field="state"),
        element("text", "attr", entity_id="sensor.mode", data_field="attribute", attribute="level"),
    )
    assert result["frozen"] == []
    assert [item["value"] for item in drawn(hass, result)] == ["eco", "low"]
    hass.states.async_set("sensor.mode", "boost", {"level": "high"})
    assert [item["value"] for item in drawn(hass, result)] == ["boost", "high"]


async def test_the_icon_a_rule_picks_follows_its_entity(hass, wolink_entry):
    hass.states.async_set("sensor.washer", "run")
    rules = [
        {"kind": "state", "state": "run", "icon": "mdi:washing-machine"},
        {"kind": "state", "state": "done", "icon": "mdi:check"},
    ]
    result = await export(
        hass,
        wolink_entry,
        element(
            "conditional_icon",
            entity_id="sensor.washer",
            data_field="state",
            icon="mdi:help",
            icon_rules=rules,
        ),
    )
    assert result["frozen"] == []
    assert drawn(hass, result)[0]["value"] == "mdi:washing-machine"
    hass.states.async_set("sensor.washer", "done")
    assert drawn(hass, result)[0]["value"] == "mdi:check"
    hass.states.async_set("sensor.washer", "other")
    assert drawn(hass, result)[0]["value"] == "mdi:help"


async def test_a_range_rule_follows_a_number(hass, wolink_entry):
    hass.states.async_set("sensor.level", "80")
    rules = [
        {"kind": "range", "min": 50, "icon": "mdi:battery"},
        {"kind": "range", "max": 50, "icon": "mdi:battery-low"},
    ]
    result = await export(
        hass,
        wolink_entry,
        element(
            "conditional_icon",
            entity_id="sensor.level",
            data_field="state",
            icon="mdi:help",
            icon_rules=rules,
        ),
    )
    assert result["frozen"] == []
    assert drawn(hass, result)[0]["value"] == "mdi:battery"
    hass.states.async_set("sensor.level", "20")
    assert drawn(hass, result)[0]["value"] == "mdi:battery-low"
    hass.states.async_set("sensor.level", "unavailable")
    assert drawn(hass, result)[0]["value"] == "mdi:help"


async def test_a_bar_and_a_gauge_follow_a_number_and_hide_without_one(hass, wolink_entry):
    hass.states.async_set("sensor.fill", "25")
    result = await export(
        hass,
        wolink_entry,
        element("progress_bar", "bar", entity_id="sensor.fill", data_field="state"),
        element("gauge", "gauge", entity_id="sensor.fill", data_field="state"),
    )
    assert result["frozen"] == []
    bar, gauge = drawn(hass, result)
    assert (bar["progress"], gauge["progress"]) == (25, 25)
    assert bar["visible"] is True
    hass.states.async_set("sensor.fill", "75")
    bar, gauge = drawn(hass, result)
    assert (bar["progress"], gauge["progress"]) == (75, 75)
    hass.states.async_set("sensor.fill", "unknown")
    assert [item["visible"] for item in drawn(hass, result)] == [False, False]


async def test_what_a_template_cannot_reproduce_exactly_stays_as_drawn_and_is_reported(
    hass, wolink_entry
):
    # Rounded text is not what the state says, so the data field is not followed.
    hass.states.async_set("sensor.temp", "21.26")
    rounded = element("text", "rounded", entity_id="sensor.temp", data_field="state", decimals=1)
    templated = element(
        "text",
        "templated",
        entity_id="sensor.temp",
        data_field="state",
        field_templates={"color": "{{ 'red' if value | float > 20 else 'black' }}"},
    )
    result = await export(hass, wolink_entry, rounded, templated)
    assert [item.split(":")[0] for item in result["frozen"]] == ["rounded", "templated"]
    assert [item["value"] for item in result["payload_data"]] == ["21.3", "21.26"]


async def test_a_hidden_component_is_kept_as_hidden_and_comes_back(hass, wolink_entry):
    hass.states.async_set("sensor.temp", "5", {"unit_of_measurement": "°C"})
    result = await export(
        hass,
        wolink_entry,
        element("rectangle", "shown"),
        element("rectangle", "gone", visible=False),
    )
    shown, gone = result["payload_data"]
    assert "visible" not in shown and gone["visible"] is False
    # Reopened, both come back as elements and the display is drawn the same.
    imported = await hass.data[KEY].import_payload(wolink_entry, result["payload_data"], "white")
    assert imported["issues"] == []
    assert len(imported["elements"]) == 2
    assert imported["different_pixels"] == 0


async def test_a_turned_component_stays_live_inside_its_group(hass, wolink_entry):
    hass.states.async_set("sensor.mode", "eco")
    result = await export(
        hass,
        wolink_entry,
        element("text", entity_id="sensor.mode", data_field="state", rotation=90),
    )
    assert result["frozen"] == []
    group = result["payload_data"][0]
    assert group["type"] == "group" and group["rotate"] == 90
    assert group["elements"][0]["value"] == '{{ states("sensor.mode") }}'
