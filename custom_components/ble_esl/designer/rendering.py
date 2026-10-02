"""Render the display exactly as a write would, plus movable editor layers."""

import base64
from io import BytesIO

from PIL import Image, ImageChops

from ..renderer import render_image
from .layout import compile_payload, resolve_component
from .specs import resolve_templates


def snapshot_layers(hass, document, templates, forecasts):
    """Resolve HA state on the event loop, before CPU work enters the executor."""
    layers = []
    for element in document["elements"]:
        placed = (element["x"], element["y"])
        element = resolve_component(hass, element)[0]
        # A field template can move the element: its layer is placed by the
        # frame the editor holds, so it is measured from there.
        element["_placed"] = placed
        if element["type"] == "imagespec":
            # Rendered once here: the layer and the display share these values,
            # and the entities say which state changes redraw the preview.
            entities = set()
            element["spec"] = resolve_templates(hass, element["spec"], entities)
            element["_spec_resolved"] = True
            element["_template_entities"] = sorted(entities)
        payload = compile_payload(hass, {"elements": [element]}, templates, forecasts)
        layers.append((element, payload))
    return layers


def png_url(image):
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def element_layer(hass, preset, element, payload, previews):
    """The transparent layer of one element, cropped to what it draws.

    An element can draw beyond its frame (a barcode's quiet zone, a chart's
    labels, a glyph's overhang), so the layer is all of it, placed relative to
    the frame, not the frame's own crop.
    """
    light = render_image(hass, preset, payload, background="white")
    dark = render_image(hass, preset, payload, background="black")
    alpha = ImageChops.difference(light, dark).convert("L").point(lambda value: 0 if value else 255)
    layer = light.convert("RGBA")
    layer.putalpha(alpha)
    box = alpha.getbbox()
    if box is None:
        return png_url(Image.new("RGBA", (element["width"], element["height"])))
    x, y = element.get("_placed", (element["x"], element["y"]))
    previews["_offsets"][element["id"]] = [box[0] - x, box[1] - y]
    previews["_bounds"][element["id"]] = [box[0] - x, box[1] - y, box[2] - x, box[3] - y]
    return png_url(layer.crop(box))


def render_document(hass, preset, document, payload, snapshots):
    """Render the display from the whole payload, plus per-element editor layers.

    The returned image is one imagespec render of ``payload``: the same call a
    ``ble_esl.write`` with that payload makes, so the preview, the pixels sent
    to the tag and an automation using the exported YAML cannot differ.

    The layers only exist to select and drag elements. imagespec returns RGB, so
    each is rendered, at its place on the display, against black and white: pixels that differ were untouched
    by the element and become transparent, without mistaking intentionally white
    text or fills for transparency. Font drawing uses imagespec's monochrome
    masks, so covered pixels are exact.
    """
    canvas = render_image(hass, preset, payload, background=document["background"])
    previews = {"_bounds": {}, "_offsets": {}, "_values": {}, "_dependencies": {}}
    for element, element_payload in snapshots:
        previews["_values"][element["id"]] = element.get("_templated_fields", {})
        previews["_dependencies"][element["id"]] = element.get("_template_entities", [])
        previews[element["id"]] = element_layer(hass, preset, element, element_payload, previews)
    return canvas, previews
