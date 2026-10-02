"""imagespec elements in the designer: their editable fields and where they sit.

An ``imagespec`` designer element stores a plain imagespec element in ``spec``
plus a frame (x, y, width, height) the editor moves and resizes. The keys of
the element that say *where* it is are not stored: they are derived from the
frame whenever the payload is built, so dragging and resizing work the same
for every type and the exported payload is ordinary absolute imagespec. The
other keys are exactly imagespec's own, edited through ``imagespec.specs()``.
"""

from copy import deepcopy
import re

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template
import imagespec
from imagespec.spec import UNSET

BOX = ("x_start", "y_start", "x_end", "y_end")
CIRCLE = ("x", "y", "radius")
RECT = ("x", "y", "width", "height")
IMAGE = ("x", "y", "xsize", "ysize")

# type -> (role, keys the frame supplies)
GEOMETRY = {
    # Fill the frame
    "rectangle": ("box", BOX),
    "ellipse": ("box", BOX),
    "arc": ("box", BOX),
    "progress_bar": ("box", BOX),
    "plot": ("box", BOX),
    "line": ("line", BOX),
    # Centred in the frame
    "circle": ("circle", CIRCLE),
    "gauge": ("circle", CIRCLE),
    "pie": ("circle", CIRCLE),
    # Origin and size
    "text_fit": ("rect", RECT),
    "battery": ("rect", RECT),
    "sparkline": ("rect", RECT),
    "new_multiline": ("rect", RECT),
    "group": ("rect", RECT),
    "stack": ("rect", RECT),  # also "row" and "column": same element, preset direction
    "diagram": ("rect", RECT),
    "dlimg": ("rect", IMAGE),
    # Drawn from the frame's top left at their own size
    "text": ("origin", ("x", "y")),
    "text_box": ("origin", ("x", "y")),
    "multiline": ("origin", ("x", "start_y")),
    "table": ("origin", ("x", "y")),
    "rich_text": ("midline", ("x", "y")),
    "icon": ("icon", ("x", "y", "size")),
    "qrcode": ("rect", RECT),
    "barcode": ("rect", RECT),
    "datamatrix": ("rect", RECT),
    "legend": ("origin", ("x", "y")),
    "star_rating": ("origin", ("x", "y")),
    "rectangle_pattern": ("origin", ("x_start", "y_start")),
    # Percentages of the frame
    "polygon": ("points", ("points",)),
}

# A tiny image so a new dlimg draws something before a URL is chosen.
SAMPLE_IMAGE = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAA"
    "BLbSncAAAAKklEQVR42r2NMQ4AIBCDwP//GQcTB5NbZWKgqQBQAer1xUR1ksfHhR8+NtY6I+1HmsaCAAAAAElFTkSuQmCC"
)

# type -> (spec without its geometry keys, frame width, frame height)
EXAMPLES = {
    "line": ({"fill": "black", "width": 2}, 100, 4),
    "rectangle": ({"fill": "black", "outline": "black", "width": 1}, 80, 40),
    "ellipse": ({"fill": "black", "outline": "black", "width": 1}, 80, 50),
    "arc": ({"start_angle": 0, "end_angle": 270, "outline": "black", "width": 4}, 60, 60),
    "circle": ({"fill": "black", "outline": "black", "width": 1}, 60, 60),
    "polygon": (
        {"points": "50,0;100,100;0,100", "fill": "black", "outline": "black", "width": 1},
        60,
        52,
    ),
    "rectangle_pattern": (
        {
            "x_size": 8,
            "y_size": 8,
            "x_repeat": 5,
            "y_repeat": 3,
            "x_offset": 4,
            "y_offset": 4,
            "fill": "black",
        },
        60,
        40,
    ),
    "gauge": ({"progress": 65, "width": 8, "show_value": True, "size": 16}, 80, 80),
    "pie": ({"values": "A,30;B,50;C,20"}, 80, 80),
    "progress_bar": ({"progress": 65, "fill": "black", "show_percentage": True}, 120, 20),
    "plot": ({"data": [{"entity": "sensor.example", "color": "black"}]}, 140, 70),
    "sparkline": ({"values": [1, 3, 2, 5, 4, 6], "color": "black"}, 100, 40),
    "diagram": ({"bars": {"values": "A,10;B,20;C,15", "color": "black"}}, 120, 60),
    "text": ({"value": "Text", "size": 20}, 100, 30),
    "text_box": ({"value": "Text", "size": 20, "fill": "black", "color": "white"}, 100, 36),
    "multiline": (
        {
            "value": "Line 1|Line 2",
            "delimiter": "|",
            "offset_y": 22,
            "size": 18,
            "anchor": "la",
        },
        100,
        50,
    ),
    "new_multiline": ({"value": "Several lines\nof text", "size": 18}, 110, 60),
    "text_fit": ({"value": "Fit this text", "size": 24}, 120, 40),
    "table": ({"columns": [60, 60], "rows": [["A", "B"], ["1", "2"]], "font_size": 14}, 120, 60),
    "rich_text": (
        {"spans": [{"text": "Hello "}, {"text": "world", "color": "red"}], "size": 20},
        140,
        30,
    ),
    "icon": ({"value": "mdi:home", "size": 32}, 32, 32),
    "dlimg": ({"url": SAMPLE_IMAGE}, 60, 60),
    "qrcode": ({"data": "https://www.home-assistant.io"}, 60, 60),
    "barcode": ({"data": "123456789012", "code": "code128"}, 120, 50),
    "datamatrix": ({"data": "ESL"}, 40, 40),
    "legend": ({"items": "A,black;B,red"}, 80, 40),
    "star_rating": ({"rating": 3.5}, 100, 20),
    "battery": ({"level": 70}, 40, 20),
    "group": (
        {"elements": [{"type": "text", "x": 0, "y": 0, "value": "Group", "size": 20}]},
        100,
        50,
    ),
    "stack": (
        {
            "direction": "horizontal",
            "gap": 6,
            "elements": [
                {"type": "icon", "value": "mdi:home", "size": 24},
                {"type": "text", "value": "Stack", "size": 20},
            ],
        },
        120,
        30,
    ),
}

_TEMPLATE = re.compile(r"\{[{%#]")


def element_types():
    """Every imagespec element type the designer can place."""
    return sorted(GEOMETRY)


def geometry_keys(type_):
    return GEOMETRY[type_][1]


def new_spec(type_):
    """A fresh element of this type and the frame it starts in."""
    spec, width, height = EXAMPLES[type_]
    return {"type": type_, **deepcopy(spec)}, width, height


def spec_payload(spec, x, y, width, height):
    """The imagespec element for a stored spec placed in this frame."""
    role, keys = GEOMETRY[spec["type"]]
    payload = {key: value for key, value in spec.items() if key not in keys}
    width, height = max(1, width), max(1, height)
    if role == "box":
        values = (x, y, x + width - 1, y + height - 1)
    elif role == "line":
        if height > width:
            values = (x + width // 2, y, x + width // 2, y + height - 1)
        else:
            values = (x, y + height // 2, x + width - 1, y + height // 2)
    elif role == "circle":
        values = (x + width // 2, y + height // 2, max(1, min(width, height) // 2 - 1))
    elif role == "rect":
        values = (x, y, width, height)
    elif role == "icon":
        values = (x, y, min(width, height))
    elif role == "midline":
        values = (x, y + height // 2)
    elif role == "points":
        return {**payload, "points": _points(spec.get("points", ""), x, y, width, height)}
    else:
        values = (x, y)
    return {**payload, **dict(zip(keys, values, strict=True))}


def _points(value, x, y, width, height):
    """A polygon's "x,y;x,y;..." in percent of the frame, as display coordinates."""
    try:
        pairs = [pair.split(",") for pair in str(value).split(";") if pair.strip()]
        return ";".join(
            f"{x + round(float(px) * (width - 1) / 100)},{y + round(float(py) * (height - 1) / 100)}"
            for px, py in pairs
        )
    except ValueError as err:
        raise HomeAssistantError(
            f'polygon points {value!r} must be "x,y;x,y;..." in percent of the frame'
        ) from err


def frozen_corners(spec):
    """A polygon whose corners come from a template: a live payload cannot keep it."""
    return spec.get("type") == "polygon" and bool(templates_in(spec.get("points", "")))


def templates_in(value):
    """Strings in a spec that Home Assistant renders when the payload is built."""
    if isinstance(value, str):
        return [value] if _TEMPLATE.search(value) else []
    if isinstance(value, dict):
        return [found for item in value.values() for found in templates_in(item)]
    if isinstance(value, list):
        return [found for item in value for found in templates_in(item)]
    return []


def resolve_templates(hass, value, entities):
    """The spec with each template rendered, as an automation would render it."""
    if isinstance(value, str) and _TEMPLATE.search(value):
        try:
            info = Template(value, hass).async_render_to_info(parse_result=True)
            result = info.result()
        except Exception as err:
            raise HomeAssistantError(f"Template error in {value!r}: {err}") from err
        entities.update(info.entities)
        return result
    if isinstance(value, dict):
        return {key: resolve_templates(hass, item, entities) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_templates(hass, item, entities) for item in value]
    return value


def _field(field, percent=False):
    result = {"name": field.name, "kind": field.kind, "required": field.required}
    if percent and field.name == "points":
        # The frame places the polygon, so its corners are relative to it.
        result["doc"] = 'Corners as "x,y;x,y;..." in percent (0-100) of the element frame'
        return result
    if field.default is not UNSET:
        result["default"] = field.default
    if field.doc:
        result["doc"] = field.doc
    if field.enum is not None:
        result["enum"] = list(field.enum)
    if field.alt:
        result["alt"] = field.alt
    if field.kind == "array":
        result["items"] = field.items
    if field.fields:
        result["fields"] = [_field(child) for child in field.fields]
    if field.required_when:
        result["required_when"] = [[key, list(values)] for key, values in field.required_when]
    return result


def describe():
    """What the editor needs to offer every element: fields, geometry, a starting point."""
    types = []
    for spec in imagespec.specs():
        for name in spec.names:
            if name not in GEOMETRY:
                continue
            role, keys = GEOMETRY[name]
            example, width, height = new_spec(name)
            types.append(
                {
                    "type": name,
                    "category": spec.category,
                    "doc": spec.doc,
                    "role": role,
                    "geometry": list(keys),
                    "fields": [
                        _field(field, role == "points")
                        for field in spec.fields
                        if field.name not in keys or role == "points"
                    ],
                    "example": example,
                    "width": width,
                    "height": height,
                }
            )
    return {"types": types, "dither_methods": list(imagespec.DITHER_METHODS)}
