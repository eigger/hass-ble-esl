"""imagespec elements in the designer: their editable fields and where they sit.

An ``imagespec`` designer element stores a plain imagespec element in ``spec``
plus a frame (x, y, width, height) the editor moves and resizes. The keys of
the element that say *where* it is are not stored: they are derived from the
frame whenever the payload is built, so dragging and resizing work the same
for every type and the exported payload is ordinary absolute imagespec. The
other keys are exactly imagespec's own, edited through ``imagespec.specs()``.
"""

from copy import deepcopy
import math
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


class ImportProblem(ValueError):
    """An element of a pasted payload the designer cannot place, and why."""


def _finite(value):
    """A number from what a payload holds: a number, or text that is one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        return value
    return None


def _number(item, key):
    if key not in item:
        raise ImportProblem(
            f"no '{key}': an element without a position is laid out after the previous "
            "one, which the designer cannot place"
        )
    value = _finite(item[key])
    if value is None:
        raise ImportProblem(f"'{key}' must be a number (a template cannot place an element)")
    return round(value)


def from_payload(item):
    """The designer's spec and frame for an imagespec element: the inverse of spec_payload.

    Returns (spec, x, y, width, height). Raises ImportProblem when the element
    cannot be placed, for example a line that is neither horizontal nor vertical.
    """
    if not isinstance(item, dict) or not isinstance(item.get("type"), str):
        raise ImportProblem("an element needs a 'type'")
    name = item["type"]
    spec = dict(item)
    if name in ("row", "column"):
        spec["type"] = name = "stack"
        spec.setdefault("direction", "horizontal" if item["type"] == "row" else "vertical")
    if name not in GEOMETRY:
        raise ImportProblem(f"'{name}' is not an imagespec element")
    role, keys = GEOMETRY[name]
    _, default_width, default_height = new_spec(name)
    for key in keys:
        spec.pop(key, None)
    if role == "box":
        x0, y0, x1, y1 = (_number(item, key) for key in keys)
        x, y = min(x0, x1), min(y0, y1)
        return spec, x, y, abs(x1 - x0) + 1, abs(y1 - y0) + 1
    if role == "line":
        x0, x1 = _number(item, "x_start"), _number(item, "x_end")
        y0, y1 = _number(item, "y_start"), _number(item, "y_end")
        raw = item.get("width", 1)
        if isinstance(raw, float) and not math.isfinite(raw):
            raise ImportProblem("'width' must be a finite number")
        stroke = max(1, round(_finite(raw) or 1))  # a template: the stroke is unknown here
        if y0 == y1:
            # Horizontal needs a frame wider than it is tall, however thick the stroke.
            length = abs(x1 - x0) + 1
            height = max(1, min(stroke, length - 1))
            return spec, min(x0, x1), y0 - height // 2, length, height
        if x0 == x1:
            length = abs(y1 - y0) + 1
            width = max(1, min(stroke, length - 1))
            return spec, x0 - width // 2, min(y0, y1), width, length
        raise ImportProblem("a line must be horizontal or vertical")
    if role == "circle":
        cx, cy, radius = (_number(item, key) for key in keys)
        radius = max(1, radius)
        return spec, cx - radius - 1, cy - radius - 1, 2 * radius + 2, 2 * radius + 2
    if role == "icon":
        x, y = _number(item, keys[0]), _number(item, keys[1])
        size = max(1, _number(item, "size")) if "size" in item else default_width
        return spec, x, y, size, size
    if role == "rect":
        x, y = _number(item, keys[0]), _number(item, keys[1])
        size = []
        for key, default in zip(keys[2:], (default_width, default_height), strict=True):
            size.append(max(1, _number(item, key)) if key in item else default)
        return spec, x, y, size[0], size[1]
    if role == "midline":
        x, middle = _number(item, keys[0]), _number(item, keys[1])
        return spec, x, middle - default_height // 2, default_width, default_height
    if role == "points":
        try:
            corners = [
                (float(px), float(py))
                for px, py in (
                    pair.split(",")
                    for pair in str(item.get("points", "")).split(";")
                    if pair.strip()
                )
            ]
        except ValueError as err:
            raise ImportProblem("'points' must be \"x,y;x,y;...\"") from err
        if not all(math.isfinite(value) for corner in corners for value in corner):
            raise ImportProblem("'points' must be finite numbers")
        if len(corners) < 3:
            raise ImportProblem("a polygon needs at least three points")
        left = round(min(px for px, _ in corners))
        top = round(min(py for _, py in corners))
        width = max(1, round(max(px for px, _ in corners)) - left) + 1
        height = max(1, round(max(py for _, py in corners)) - top) + 1
        spec["points"] = ";".join(
            f"{round((px - left) * 100 / (width - 1), 4):g},{round((py - top) * 100 / (height - 1), 4):g}"
            for px, py in corners
        )
        return spec, left, top, width, height
    # origin: drawn from the frame's top left at its own size
    x, y = _number(item, keys[0]), _number(item, keys[1])
    return spec, x, y, default_width, default_height


def templates_in(value):
    """Strings in a spec that Home Assistant renders when the payload is built."""
    if isinstance(value, str):
        return [value] if _TEMPLATE.search(value) else []
    if isinstance(value, dict):
        return [found for item in value.values() for found in templates_in(item)]
    if isinstance(value, list):
        return [found for item in value for found in templates_in(item)]
    return []


class MissingTemplateParameter(HomeAssistantError):
    """A template needs a value supplied only for its designer preview."""

    def __init__(self, name):
        self.name = name
        super().__init__(f"Preview parameter {name!r} is required")


def resolve_templates(hass, value, entities, preview_variables=None):
    """The spec with each template rendered, as an automation would render it."""
    if isinstance(value, str) and _TEMPLATE.search(value):
        try:
            info = Template(value, hass).async_render_to_info(
                preview_variables, parse_result=True, strict=True
            )
            result = info.result()
        except Exception as err:
            missing = re.search(r"['\"]([^'\"]+)['\"] is undefined", str(err))
            if missing:
                raise MissingTemplateParameter(missing.group(1)) from err
            raise HomeAssistantError(f"Template error in {value!r}: {err}") from err
        entities.update(info.entities)
        return result
    if isinstance(value, dict):
        return {
            key: resolve_templates(hass, item, entities, preview_variables)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [resolve_templates(hass, item, entities, preview_variables) for item in value]
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
