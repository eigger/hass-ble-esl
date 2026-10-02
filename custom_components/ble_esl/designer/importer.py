"""Bring a payload written for ``ble_esl.write`` into the designer as elements."""

from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError
from PIL import ImageChops
import voluptuous as vol
import yaml

from ..renderer import render_image
from .layout import compile_payload, validate
from .specs import ImportProblem, from_payload, resolve_templates

MAX_TEXT = 256 * 1024
MAX_ELEMENTS = 100  # What a display holds: layout.DOCUMENT


class _NoAliases(yaml.SafeLoader):
    """A pasted payload is data: an alias would let a few bytes become megabytes."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise yaml.YAMLError("YAML aliases (&anchor, *alias) are not accepted here")
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


def payloads(hass, imported, elements):
    """The pasted payload and the designer's, templates rendered.

    On the event loop: Home Assistant renders templates there.
    """
    return (
        resolve_templates(hass, imported, set()),
        compile_payload(hass, {"elements": elements}),
    )


def different_pixels(hass, preset, original, rebuilt, background="white"):
    """How many pixels differ between the two payloads once drawn.

    Zero means the designer will write exactly what the automation did.
    """
    before = render_image(hass, preset, original, background=background)
    after = render_image(hass, preset, rebuilt, background=background)
    differing = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v else 0)
    return differing.histogram()[255]
