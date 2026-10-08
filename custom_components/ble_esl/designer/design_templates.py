"""Ready-made designs: YAML files that become designer elements and an automation."""

import logging
import math
from pathlib import Path
import re

from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol
import yaml

from .importer import MAX_ELEMENTS, _NoAliases

_LOGGER = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
MAX_TEMPLATE_BYTES = 256 * 1024
FORMAT_VERSION = 1

_SLUG = vol.All(str, vol.Match(r"^[a-z][a-z0-9_]{0,39}\Z"))
_SIZE = vol.All(str, vol.Match(r"^[1-9][0-9]{1,4}x[1-9][0-9]{1,4}\Z"))
_REFERENCE = re.compile(r"\$\{([^}]*)\}")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?\Z")
_COLORS = {"black": "B", "white": "W", "red": "R", "yellow": "Y"}
_ENTITY = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+")
_FONT = re.compile(r"^[\w .-]+\.(ttf|otf|ttc)\Z")
_UNSAFE_TEXT = re.compile(r"[{}'\"\\\n\r]")
# Numeric keys that are counts, angles, values or limits, not lengths in pixels:
# every other number in a layout follows the size of the display.
_NOT_SCALED = frozenset(
    {
        "x_repeat",
        "y_repeat",
        "rotate",
        "rotation",
        "start_angle",
        "end_angle",
        "min",
        "max",
        "value",
        "progress",
        "max_lines",
        "level",
        "dpi",
        "timeout",
        "duration",
        "quiet_zone",
        "opacity",
        "alpha",
        "threshold",
        "low_threshold",
        "min_value",
        "max_value",
        "low",
        "high",
        "tick_every",
        "grow",
        "border",
        "module_width",
        "module_height",
        "text_distance",
        "values",
        "rows",
        "data",
        "dither",
        "decimals",
        "count",
        "ticks",
        "rating",
        "stars",
        "scale",
    }
)

_X_KEYS = ("x", "x_start", "x_end")
_Y_KEYS = ("y", "y_start", "y_end", "start_y")

_LOCALIZED = vol.Any(str, {str: str})
_PARAMETER = vol.Schema(
    {
        vol.Required("type"): vol.In(
            ("font", "color", "select", "string", "number", "time", "boolean", "entity")
        ),
        vol.Required("default"): vol.Any(str, int, float, bool),
        vol.Optional("label"): _LOCALIZED,
        vol.Optional("group", default="design"): vol.In(("design", "automation")),
        vol.Optional("options"): [str],
        vol.Optional("domain"): _SLUG,
        vol.Optional("forbidden"): str,
        vol.Optional("min_length"): vol.All(int, vol.Range(min=1, max=200)),
        vol.Optional("min"): vol.Any(int, float),
        vol.Optional("max"): vol.Any(int, float),
    },
    extra=vol.PREVENT_EXTRA,
)
_AUTOMATION = vol.Schema(
    {
        vol.Optional("alias"): str,
        vol.Optional("description", default=""): str,
        vol.Required("triggers"): vol.All([dict], vol.Length(min=1)),
        vol.Optional("conditions", default=list): [dict],
        vol.Optional("mode", default="single"): vol.In(("single", "restart", "queued", "parallel")),
    }
)
TEMPLATE = vol.Schema(
    {
        vol.Required("template"): FORMAT_VERSION,
        vol.Required("id"): _SLUG,
        vol.Required("name"): _LOCALIZED,
        vol.Optional("description", default=""): _LOCALIZED,
        vol.Optional("background", default="white"): vol.In(tuple(_COLORS)),
        vol.Required("layouts"): vol.All(
            {_SIZE: vol.All([dict], vol.Length(max=MAX_ELEMENTS))}, vol.Length(min=1)
        ),
        vol.Optional("parameters", default=dict): {_SLUG: _PARAMETER},
        vol.Optional("automation"): _AUTOMATION,
    }
)


def _references(value):
    if isinstance(value, str):
        yield from _REFERENCE.findall(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _references(item)
    elif isinstance(value, list):
        for item in value:
            yield from _references(item)


def parse_template(text):
    """A validated template from YAML text; raises ``vol.Invalid`` or ``ValueError``."""
    if len(text.encode()) > MAX_TEMPLATE_BYTES:
        raise ValueError("template is too large")
    try:
        template = TEMPLATE(yaml.load(text, Loader=_NoAliases))
    except (yaml.YAMLError, RecursionError) as err:
        raise ValueError(f"not usable YAML: {err}") from err
    declared = template["parameters"]
    for name, parameter in declared.items():
        if parameter["type"] == "select" and not parameter.get("options"):
            raise vol.Invalid(f"parameter {name}: a select needs options")
        # Defaults must themselves be acceptable values.
        coerce_value(name, parameter, parameter["default"], None)
    in_design = set(_references(template["layouts"]))
    used = in_design | set(_references(template.get("automation", {})))
    unknown = sorted(used - set(declared))
    if unknown:
        raise vol.Invalid(f"undeclared parameters: {', '.join(unknown)}")
    for name in in_design:
        if declared[name]["group"] == "automation":
            raise vol.Invalid(f"parameter {name} belongs to the automation, not the design")
    return template


def load_templates(directory=TEMPLATE_DIR):
    """Every valid template in a folder, by id. A broken file is logged and skipped."""
    templates = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        try:
            # A user folder is untrusted: look at the size before reading.
            if path.stat().st_size > MAX_TEMPLATE_BYTES:
                raise ValueError("template is too large")
            template = parse_template(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, vol.Invalid) as err:
            _LOGGER.warning("Ignoring design template %s: %s", path.name, err)
            continue
        if template["id"] in templates:
            _LOGGER.warning("Ignoring design template %s: duplicate id", path.name)
            continue
        templates[template["id"]] = {**template, "file": path.name}
    return templates


def load_all(user_dir=None):
    """Bundled templates, then the user's own; a user file cannot replace a bundled id."""
    templates = {key: {**value, "source": "bundled"} for key, value in load_templates().items()}
    if user_dir is not None and Path(user_dir).is_dir():
        for key, value in load_templates(user_dir).items():
            if key in templates:
                _LOGGER.warning("Ignoring user design template %s: id is already bundled", key)
                continue
            templates[key] = {**value, "source": "user"}
    return templates


ID_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,39}")


def slug(name):
    """A template id from a name: ASCII letters and digits only, at most 37 characters.

    Names without any become ``design``; the room left is for ``_2`` style suffixes.
    """
    text = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:30].strip("_")
    return text if text and text[0].isalpha() else f"design_{text}".strip("_")


def check_name(name):
    """A template name, trimmed; ``HomeAssistantError`` when it cannot be used."""
    name = (name or "").strip()
    if not name or len(name) > 80 or any(ord(char) < 32 for char in name):
        raise HomeAssistantError("Give the template a name of up to 80 characters")
    return name


def pick_id(name, template_id, overwrite, templates, exists):
    """The id and file name for a design saved by the user.

    ``templates`` are the loaded ones (bundled and user); ``exists(file_name)``
    says whether a file is already in the user folder, so a file that is there
    but did not load is never overwritten by accident. Without an explicit
    ``template_id`` a taken id gets a ``_2``, ``_3``… suffix.
    """
    bundled = {key for key, value in templates.items() if value.get("source") == "bundled"}
    if template_id:
        if not ID_PATTERN.fullmatch(template_id):
            raise HomeAssistantError("A template id is lowercase letters, digits and underscores")
        if template_id in bundled:
            raise HomeAssistantError(f"{template_id} is the id of a bundled template")
        file_name = f"{template_id}.yaml"
        loaded = templates.get(template_id)
        if loaded and loaded.get("file") not in (None, file_name):
            raise HomeAssistantError(f"Template {template_id} is defined in {loaded['file']}")
        # That file may hold a different template: never replace it by its file name.
        holder = next(
            (key for key, value in templates.items() if value.get("file") == file_name),
            None,
        )
        if holder not in (None, template_id):
            raise HomeAssistantError(f"{file_name} holds the template {holder}")
        if (loaded or exists(file_name)) and not overwrite:
            raise HomeAssistantError(f"Template {template_id} already exists")
        return template_id, file_name
    base = slug(name)
    candidate = base
    for number in range(2, 100):
        if (
            candidate not in bundled
            and candidate not in templates
            and not exists(f"{candidate}.yaml")
        ):
            return candidate, f"{candidate}.yaml"
        candidate = f"{base}_{number}"
    raise HomeAssistantError("Too many templates share that name")


def template_text(template_id, name, width, height, background, payload):
    """YAML of a template whose only layout is a finished design.

    Raises ``HomeAssistantError`` when the result would not load again, e.g. a
    text that contains a ``${...}`` reference.
    """
    document = {
        "template": FORMAT_VERSION,
        "id": template_id,
        "name": name,
        "background": background,
        "layouts": {f"{width}x{height}": payload},
    }
    text = yaml.dump(document, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10**6)
    try:
        parse_template(text)
    except (ValueError, vol.Invalid) as err:
        raise HomeAssistantError(f"This design cannot be saved as a template: {err}") from err
    return text


class _Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def coerce_value(name, parameter, value, colors):
    """A parameter value in its final form, or ``vol.Invalid``.

    ``colors`` is the display's palette (``"BWR"``); a colour it cannot show
    becomes black, so one template fits every tag.
    """
    kind = parameter["type"]
    try:
        if kind == "boolean":
            if not isinstance(value, bool):
                raise ValueError("expected true or false")
            return value
        if kind == "number":
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError("expected a number")
            if not math.isfinite(value):
                raise ValueError("expected a finite number")
            if "min" in parameter and value < parameter["min"]:
                raise ValueError(f"at least {parameter['min']}")
            if "max" in parameter and value > parameter["max"]:
                raise ValueError(f"at most {parameter['max']}")
            return value
        if not isinstance(value, str):
            raise ValueError("expected text")
        if kind == "color":
            if value not in _COLORS:
                raise ValueError(f"one of {', '.join(_COLORS)}")
            return value if colors is None or _COLORS[value] in colors else "black"
        if kind == "select":
            if value not in parameter["options"]:
                raise ValueError(f"one of {', '.join(parameter['options'])}")
            return value
        if kind == "time":
            if not _TIME.match(value):
                raise ValueError("a time such as 12:00 or 12:00:00")
            return value if value.count(":") == 2 else f"{value}:00"
        if kind == "entity":
            if not _ENTITY.fullmatch(value):
                raise ValueError("an entity id such as weather.home")
            if "domain" in parameter and not value.startswith(f"{parameter['domain']}."):
                raise ValueError(f"a {parameter['domain']} entity")
            return value
        if kind == "font":
            if not _FONT.match(value):
                raise ValueError("a font file name such as NotoSansKR-Bold.ttf")
            return value
        if len(value) > 200 or _UNSAFE_TEXT.search(value):
            raise ValueError("text without braces, quotes, backslashes or line breaks")
        if len(value) < parameter.get("min_length", 0):
            raise ValueError(f"at least {parameter['min_length']} characters")
        if any(char in value for char in parameter.get("forbidden", "")):
            raise ValueError(f"text without any of {parameter['forbidden']}")
        return value
    except ValueError as err:
        raise vol.Invalid(f"parameter {name}: {err}") from err


def resolve_parameters(template, given, colors):
    """Every declared parameter's value: what was given, else its default."""
    given = given or {}
    unknown = sorted(set(given) - set(template["parameters"]))
    if unknown:
        raise HomeAssistantError(f"Unknown template parameters: {', '.join(unknown)}")
    try:
        return {
            name: coerce_value(name, parameter, given.get(name, parameter["default"]), colors)
            for name, parameter in template["parameters"].items()
        }
    except vol.Invalid as err:
        raise HomeAssistantError(str(err)) from err


def substitute(value, values):
    """``${name}`` replaced by its value. A string that is only a reference keeps the type."""
    if isinstance(value, str):
        whole = _REFERENCE.fullmatch(value)
        if whole:
            return values[whole.group(1)]
        return _REFERENCE.sub(lambda match: _text(values[match.group(1)]), value)
    if isinstance(value, dict):
        return {key: substitute(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, values) for item in value]
    return value


def _text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _distance(size, width, height):
    layout_width, layout_height = (int(part) for part in size.split("x"))
    return abs(math.log(width / layout_width)) + abs(math.log(height / layout_height))


def choose_layout(template, width, height):
    """The layout drawn for this display: (size key, exact match)."""
    key = f"{width}x{height}"
    if key in template["layouts"]:
        return key, True
    return min(template["layouts"], key=lambda size: _distance(size, width, height)), False


def _has_key(value, wanted):
    if isinstance(value, dict):
        return wanted in value or any(_has_key(item, wanted) for item in value.values())
    if isinstance(value, list):
        return any(_has_key(item, wanted) for item in value)
    return False


def _scale(value, factor, key=None):
    if key in _NOT_SCALED:
        return value
    if isinstance(value, dict):
        return {name: _scale(item, factor, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_scale(item, factor, key) for item in value]
    if key not in _NOT_SCALED and isinstance(value, int | float) and not isinstance(value, bool):
        scaled = round(value * factor)
        # A stroke, outline or radius of 1 must not vanish when shrinking.
        if value > 0 and key not in _X_KEYS and key not in _Y_KEYS:
            return max(1, scaled)
        return scaled
    return value


def _fit(items, source, width, height):
    """A layout drawn for another display size: scaled evenly and centred."""
    source_width, source_height = (int(part) for part in source.split("x"))
    factor = min(width / source_width, height / source_height)
    shift_x = round((width - source_width * factor) / 2)
    shift_y = round((height - source_height * factor) / 2)
    fitted = []
    if any(_has_key(item, "points") for item in items):
        raise HomeAssistantError(
            "This template has no layout for the display and its polygon cannot be scaled"
        )
    for item in _scale(items, factor):
        item = dict(item)
        if item.get("type") in ("group", "stack", "row", "column"):
            # Their origin defaults to 0: still part of the layout that is centred.
            item.setdefault("x", 0)
            item.setdefault("y", 0)
        shifts = [(key, shift_x) for key in _X_KEYS] + [(key, shift_y) for key in _Y_KEYS]
        for key, shift in shifts:
            if isinstance(item.get(key), int | float) and not isinstance(item[key], bool):
                item[key] += shift
        fitted.append(item)
    return fitted


def build(template, width, height, colors, given=None):
    """The payload and automation a template makes for one display.

    Returns a dict with ``payload``, ``background``, ``layout``, ``scaled``,
    ``automation`` (without its action, or ``None``) and ``parameters``.
    """
    values = resolve_parameters(template, given, colors)
    size, exact = choose_layout(template, width, height)
    items = substitute(template["layouts"][size], values)
    if not exact:
        items = _fit(items, size, width, height)
    background = template["background"]
    if _COLORS[background] not in colors:
        background = "white"
    automation = template.get("automation")
    if automation is not None:
        automation = substitute(automation, values)
    return {
        "payload": items,
        "background": background,
        "layout": size,
        "scaled": not exact,
        "automation": automation,
        "parameters": values,
    }


def describe(template, width, height):
    """What the gallery shows about a template for one display."""
    size, exact = choose_layout(template, width, height)
    return {
        "id": template["id"],
        "name": template["name"],
        "description": template["description"],
        "layout": size,
        "scaled": not exact,
        "layouts": sorted(template["layouts"]),
        "source": template.get("source", "bundled"),
        "parameters": template["parameters"],
        "automation": template.get("automation") is not None,
    }
