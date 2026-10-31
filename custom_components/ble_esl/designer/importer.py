"""Bring a payload written for ``ble_esl.write`` into the designer as elements."""

from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError
from PIL import ImageChops
import voluptuous as vol
import yaml

from ..renderer import render_image
from .layout import compile_payload, validate
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


def convert(hass, static, live, preset):
    """An element of the old kinds as imagespec elements, and how exactly they draw it.

    ``static`` is the payload the element draws now and ``live`` the same with
    what follows its entity written as templates (``layout.live_payload``), item
    for item. Returns (elements, issues, original payload, rebuilt payload).
    """
    # Text with template syntax in it (a sensor's unit can say anything) would be
    # rendered as a template once it is an imagespec element: leave it out, and
    # let the comparison show what that costs.
    plain = [index for index, item in enumerate(static) if not templates_in(item)]
    left_out = [item for item in static if templates_in(item)]
    elements, imported, issues = elements_from([live[index] for index in plain], preset)
    issues.extend(
        f"{item.get('type')}: left out, its text has template syntax that would be rendered"
        for item in left_out
    )
    kept = {id(item) for item in imported}
    original = [static[index] for index in plain if id(live[index]) in kept]
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
