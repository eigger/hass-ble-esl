"""Render the display exactly as a write would, plus movable editor layers."""

import base64
from copy import deepcopy
from io import BytesIO

from PIL import ImageChops

from ..esl_ble.base import DevicePreset
from ..renderer import render_image
from .layout import compile_payload, resolve_component


def snapshot_layers(hass, document, templates, forecasts):
    """Resolve HA state on the event loop, before CPU work enters the executor."""
    layers = []
    for element in document["elements"]:
        element = resolve_component(hass, element)[0]
        local = deepcopy(element)
        local["x"] = local["y"] = 0
        payload = compile_payload(hass, {"elements": [local]}, templates, forecasts)
        layers.append((element, payload))
    return layers


def png_url(image):
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def render_document(hass, preset, document, payload, snapshots):
    """Render the display from the whole payload, plus per-element editor layers.

    The returned image is one imagespec render of ``payload``: the same call a
    ``ble_esl.write`` with that payload makes, so the preview, the pixels sent
    to the tag and an automation using the exported YAML cannot differ.

    The layers only exist to select and drag elements. imagespec returns RGB, so
    each is rendered against black and white: pixels that differ were untouched
    by the element and become transparent, without mistaking intentionally white
    text or fills for transparency. Font drawing uses imagespec's monochrome
    masks, so covered pixels are exact.
    """
    canvas = render_image(hass, preset, payload, background=document["background"])
    previews = {"_bounds": {}, "_values": {}, "_dependencies": {}}
    for element, element_payload in snapshots:
        local = DevicePreset("layer", "Layer", element["width"], element["height"], preset.colors)
        background = element["background"]
        light = render_image(
            hass,
            local,
            element_payload,
            background="white" if background == "transparent" else background,
        )
        dark = render_image(
            hass,
            local,
            element_payload,
            background="black" if background == "transparent" else background,
        )
        previews["_values"][element["id"]] = element.get("_templated_fields", {})
        previews["_dependencies"][element["id"]] = element.get("_template_entities", [])
        alpha = (
            ImageChops.difference(light, dark).convert("L").point(lambda value: 0 if value else 255)
        )
        layer = light.convert("RGBA")
        layer.putalpha(alpha)
        if bounds := alpha.getbbox():
            previews["_bounds"][element["id"]] = bounds
        previews[element["id"]] = png_url(layer)
    return canvas, previews
