"""Bring a payload written for ``ble_esl.write`` into the designer as elements."""

from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError
from PIL import ImageChops
import voluptuous as vol
import yaml

from ..renderer import render_image
from .layout import compile_payload, validate
from .specs import ImportProblem, from_payload, resolve_templates


def parse(text):
    """The payload list (and background) in what was pasted.

    It may be the list itself, a mapping with ``payload``, or a whole
    ``ble_esl.write`` action (``data.payload``), as the YAML dialog shows it.
    """
    try:
        loaded = yaml.safe_load(text)
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


def elements_from(items, preset):
    """Designer elements for each placeable item, what could not be placed, and why."""
    elements, imported, issues = [], [], []
    for number, item in enumerate(items, 1):
        label = f"#{number} {item.get('type', '?')}"
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
        except ImportProblem as err:
            issues.append(f"{label}: {err}")
        except (vol.Invalid, HomeAssistantError) as err:
            issues.append(f"{label}: {err}")
        else:
            elements.append(element)
            imported.append(item)
    return elements, imported, issues


def different_pixels(hass, preset, imported, elements, background="white"):
    """How many pixels differ between the pasted payload and what the designer builds.

    Zero means the designer will write exactly what the automation did.
    """
    original = resolve_templates(hass, imported, set())
    rebuilt = compile_payload(hass, {"elements": elements})
    before = render_image(hass, preset, original, background=background)
    after = render_image(hass, preset, rebuilt, background=background)
    differing = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v else 0)
    return differing.histogram()[255]
