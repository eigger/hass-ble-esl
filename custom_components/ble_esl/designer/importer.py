"""Bring a payload written for ``ble_esl.write`` into the designer as elements."""

from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError
from PIL import ImageChops
import voluptuous as vol
import yaml

from ..renderer import render_image
from .layout import as_number, compile_payload, format_decimals, normalize_unit, validate
from .specs import ImportProblem, from_payload, resolve_templates, templates_in

MAX_TEXT = 256 * 1024
MAX_ELEMENTS = 100  # What a display holds: layout.DOCUMENT


class _NoAliases(yaml.SafeLoader):
    """A pasted payload is data: an alias would let a few bytes become megabytes."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise yaml.YAMLError(
                "YAML aliases (&anchor, *alias, <<: *merge) are not accepted here: "
                "write the repeated values out before pasting"
            )
        return super().compose_node(parent, index)


def parse(text):
    """The payload list (and background) in what was pasted.

    It may be the list itself, a mapping with ``payload``, or a whole
    ``ble_esl.write`` action (``data.payload``), as the YAML dialog shows it.
    """
    if len(text) > MAX_TEXT:
        raise HomeAssistantError(f"That is too much to import (over {MAX_TEXT // 1024} KB)")
    try:
        loaded = yaml.load(text, Loader=_NoAliases)
    except yaml.YAMLError as err:
        raise HomeAssistantError(f"This is not YAML: {err}") from err
    except RecursionError as err:
        raise HomeAssistantError("This is not usable YAML: it is nested too deeply") from err
    data = loaded
    if isinstance(loaded, dict) and isinstance(loaded.get("data"), dict):
        data = loaded["data"]
    background = data.get("background") if isinstance(data, dict) else None
    if isinstance(data, dict):
        data = data.get("payload")
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise HomeAssistantError(
            "Paste a payload (a list of elements) or a ble_esl.write action with a payload"
        )
    return data, background if isinstance(background, str) else None


def elements_from(items, preset, room=MAX_ELEMENTS):
    """Designer elements for each placeable item, what could not be placed, and why.

    At most ``room`` elements: a display holds no more than that.
    """
    elements, imported, issues = [], [], []
    for number, item in enumerate(items, 1):
        label = f"#{number} {item.get('type', '?')}"
        if len(elements) >= room:
            issues.append(f"{label}: left out, a display holds at most {MAX_ELEMENTS} elements")
            continue
        try:
            spec, x, y, width, height = from_payload(item)
            element = validate(
                {
                    "version": 1,
                    "elements": [
                        {
                            "id": uuid4().hex,
                            "type": "imagespec",
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "spec": spec,
                        }
                    ],
                },
                preset,
            )["elements"][0]
        except (ImportProblem, vol.Invalid, HomeAssistantError, ValueError, OverflowError) as err:
            issues.append(f"{label}: {err}")
        else:
            elements.append(element)
            imported.append(item)
    return elements, imported, issues


def value_template(element, state, items):
    """The payload with a sensor's value text turned into a template, as a copy.

    Only a sensor shown as a plain value can be written as one: its text is the
    state, rounded as asked, and the unit, and the template follows the
    designer's own rules (an unavailable state shows as such, without the unit).
    Anything else is left as it is, and why is returned: a weather or binary
    sensor, a state that is not available, a data field, field templates, a
    unit that would itself be read as a template, and a bare number (Home
    Assistant turns the text of a template that is only a number back into one,
    so 21.50 would come out as 21.5).

    Returns (the payload, a reason or None).
    """
    templated = [dict(item) for item in items]
    if element["type"] != "sensor" or state is None:
        return templated, None
    if (
        state.entity_id.startswith(("weather.", "binary_sensor."))
        or state.state in ("unavailable", "unknown")
        or element.get("data_field")
        or element.get("field_templates")
    ):
        return templated, None
    shown = state.state
    decimals = element.get("decimals")
    numeric = decimals is not None and as_number(state.state) is not None
    if decimals is not None:
        shown = format_decimals(state.state, decimals)
    unit = normalize_unit(state.attributes.get("unit_of_measurement", ""))
    unit = unit if element.get("show_unit", True) else ""
    if any(char in unit for char in "'\"\\\n"):
        return (
            templated,
            "the unit has characters a template would misread, so the value stays as text",
        )
    if not unit and as_number(shown) is not None:
        return (
            templated,
            "a bare number stays as text: written as a template it would lose its format",
        )
    # A state that is not a number is shown as reported, as the designer does.
    value = f"('%.{decimals}f'|format(n) if n is not none else v)" if numeric else "v"
    if unit:
        value = f"({value}) ~ ' {unit}'"
    number = "{% set n = v|float(none) %}" if numeric else ""
    template = (
        f"{{% set v = states('{state.entity_id}') %}}{number}"
        f"{{{{ v|capitalize if v in ['unavailable', 'unknown'] else {value} }}}}"
    )
    wanted = shown + (f" {unit}" if unit else "")
    for item in reversed(templated):
        if item.get("type") == "text_fit" and item.get("value") == wanted:
            item["value"] = template
            break
    return templated, None


def convert(hass, element, state, items, preset):
    """An element of the old kinds as imagespec elements, and how exactly they draw it.

    Returns (elements, issues, original payload, rebuilt payload).
    """
    # Text with template syntax in it (a sensor's unit can say anything) would be
    # rendered as a template once it is an imagespec element: leave it out, and
    # let the comparison show what that costs.
    plain = [item for item in items if not templates_in(item)]
    left_out = [item for item in items if templates_in(item)]
    templated, reason = value_template(element, state, plain)
    elements, imported, issues = elements_from(templated, preset)
    if reason:
        issues.append(reason)
    issues.extend(
        f"{item.get('type')}: left out, its text has template syntax that would be rendered"
        for item in left_out
    )
    kept = {id(item) for item in imported}
    original = [item for item, copy in zip(plain, templated, strict=True) if id(copy) in kept]
    return elements, issues, [*original, *left_out], compile_payload(hass, {"elements": elements})


def payloads(hass, imported, elements, preview_variables=None):
    """The pasted payload and the designer's, templates rendered.

    On the event loop: Home Assistant renders templates there.
    """
    return (
        resolve_templates(hass, imported, set(), preview_variables),
        compile_payload(hass, {"elements": elements}, preview_variables=preview_variables),
    )


def different_pixels(hass, preset, original, rebuilt, background="white"):
    """How many pixels differ between the two payloads once drawn.

    Zero means the designer will write exactly what the automation did.
    """
    before = render_image(hass, preset, original, background=background)
    after = render_image(hass, preset, rebuilt, background=background)
    differing = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v else 0)
    return differing.histogram()[255]
