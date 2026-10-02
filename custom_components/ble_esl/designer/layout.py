"""Versioned editor documents compiled into ordinary imagespec payloads."""

from copy import deepcopy
from datetime import timedelta
import re
from types import SimpleNamespace

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util
import imagespec
import voluptuous as vol

from .specs import GEOMETRY, frozen_corners, resolve_templates, spec_payload, templates_in

COLOR = vol.In(("black", "white", "red", "yellow"))


def _dither(value):
    """None (no override), a bool, or one of imagespec's dither methods."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            imagespec.resolve_dither_method(value)
        except ValueError as err:
            raise vol.Invalid(str(err)) from err
        return value
    raise vol.Invalid("Dither is a method name, or yes or no")


ELEMENT = vol.Schema(
    {
        vol.Required("id"): str,
        vol.Required("type"): vol.In(
            (
                "sensor",
                "conditional_icon",
                "progress_bar",
                "gauge",
                "image",
                "text",
                "rectangle",
                "line",
                "icon",
                "ellipse",
                "triangle",
                "rounded_rectangle",
                "imagespec",
            )
        ),
        vol.Optional("spec", default=dict): dict,
        vol.Required("x"): int,
        vol.Required("y"): int,
        vol.Required("width"): vol.All(int, vol.Range(min=1)),
        vol.Required("height"): vol.All(int, vol.Range(min=1)),
        vol.Optional("color", default="black"): COLOR,
        vol.Optional("background", default="transparent"): vol.In(
            ("black", "white", "red", "yellow", "transparent")
        ),
        vol.Optional("visible", default=True): bool,
        vol.Optional("font_size", default=24): vol.All(int, vol.Range(min=8, max=200)),
        vol.Optional("text", default="Text"): str,
        vol.Optional("image", default=""): str,
        vol.Optional("dither"): _dither,
        vol.Optional("rotate"): vol.Coerce(float),
        vol.Optional("circle"): bool,
        vol.Optional("image_fit", default="contain"): vol.In(("contain", "fill", "stretch")),
        vol.Optional("icon", default="{{icon}}"): str,
        vol.Optional("state", default=""): str,
        vol.Optional("state_icons", default=dict): {str: str},
        vol.Optional("template", default="auto"): str,
        vol.Optional("weather_when", default="now"): vol.In(
            ("now", "later_today", "tomorrow", "in_2_days", "in_3_days")
        ),
        vol.Optional("weather_field", default="condition"): vol.In(
            (
                "condition",
                "temperature",
                "templow",
                "precipitation",
                "precipitation_probability",
                "wind_speed",
                "humidity",
            )
        ),
        vol.Optional("entity_id", default=""): str,
        vol.Optional("field_templates", default=dict): {str: str},
        vol.Optional("data_field", default=""): vol.In(
            ("", "state", "name", "unit", "icon", "attribute")
        ),
        vol.Optional("attribute", default=""): str,
        vol.Optional("value", default=0): vol.Any(None, vol.Coerce(float)),
        vol.Optional("min_value", default=0): vol.Coerce(float),
        vol.Optional("max_value", default=100): vol.Coerce(float),
        vol.Optional("icon_rules", default=list): [
            vol.Schema(
                {
                    vol.Required("kind"): vol.In(("state", "range")),
                    vol.Optional("state", default=""): str,
                    vol.Optional("min"): vol.Coerce(float),
                    vol.Optional("max"): vol.Coerce(float),
                    vol.Required("icon"): str,
                }
            )
        ],
        vol.Optional("label", default=""): str,
        vol.Optional("show_label", default=True): bool,
        vol.Optional("show_unit", default=True): bool,
        vol.Optional("decimals"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Optional("align", default="left"): vol.In(("left", "center", "right")),
        vol.Optional("valign"): vol.In(("top", "middle", "bottom")),
        vol.Optional("fit"): vol.In(("shrink", "ellipsis", "shrink_ellipsis")),
        vol.Optional("max_lines"): vol.All(int, vol.Range(min=1, max=20)),
        vol.Optional("min_font_size"): vol.All(int, vol.Range(min=1, max=200)),
        vol.Optional("padding"): vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional("line_spacing"): vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional("font"): str,
        vol.Optional("stroke_width"): vol.All(int, vol.Range(min=0, max=20)),
        vol.Optional("stroke_fill"): COLOR,
        vol.Optional("filled"): bool,
        vol.Optional("line_width"): vol.All(int, vol.Range(min=1, max=20)),
        vol.Optional("radius"): vol.All(int, vol.Range(min=0, max=200)),
        vol.Optional("direction"): vol.In(("right", "left", "up", "down")),
        vol.Optional("show_percentage"): bool,
        vol.Optional("show_value"): bool,
        vol.Optional("thickness"): vol.All(int, vol.Range(min=1, max=100)),
    }
)
DOCUMENT = vol.Schema(
    {
        vol.Required("version"): 1,
        vol.Required("elements"): vol.All([ELEMENT], vol.Length(max=100)),
        vol.Optional("background", default="white"): COLOR,
        vol.Optional("auto_update", default=False): bool,
        vol.Optional("interval", default=60): vol.All(int, vol.Range(min=10, max=86400)),
    }
)


def validate(document, preset):
    """Reject invalid documents before replacing a saved layout."""
    result = DOCUMENT(deepcopy(document))
    palette = (
        {"black", "white"}
        | ({"red"} if "R" in preset.colors else set())
        | ({"yellow"} if "Y" in preset.colors else set())
    )
    if result["background"] not in palette:
        raise vol.Invalid("Background is not supported by this tag")
    ids = set()
    for element in result["elements"]:
        if set(element["field_templates"]) - DYNAMIC_FIELDS:
            raise vol.Invalid("Unsupported dynamic field")
        if element["id"] in ids:
            raise vol.Invalid("Element IDs must be unique")
        ids.add(element["id"])
        if element.get("stroke_fill", "black") not in palette:
            raise vol.Invalid("Element colour is not supported by this tag")
        if element["color"] not in palette or element["background"] not in palette | {
            "transparent"
        }:
            raise vol.Invalid("Element colour is not supported by this tag")
        if (
            element["type"] in ("progress_bar", "gauge")
            and element["min_value"] >= element["max_value"]
        ):
            raise vol.Invalid("Maximum must exceed minimum")
        for rule in element["icon_rules"]:
            if (
                rule["kind"] == "range"
                and "min" in rule
                and "max" in rule
                and rule["min"] >= rule["max"]
            ):
                raise vol.Invalid("Range upper bound must exceed lower bound")
        if element["data_field"] == "attribute" and not element["attribute"]:
            raise vol.Invalid("Choose an attribute")
        element["background"] = "transparent"
        if element["type"] == "sensor" and not element["entity_id"]:
            raise vol.Invalid("Sensor elements need an entity_id")
        if element["type"] == "imagespec":
            validate_spec(element)
    return result


_PATH_STEP = re.compile(r"\.(\w+)|\[(\d+)\]")


def _is_template(payload, path):
    """Whether the value an imagespec issue points at is a template string."""
    value = [payload]
    for key, index in _PATH_STEP.findall(path):
        try:
            value = value[int(index)] if index else value[key]
        except (KeyError, IndexError, TypeError):
            return False
    return bool(templates_in(value))


def validate_spec(element):
    """An imagespec element must be one the designer places, with what it needs."""
    spec = element["spec"]
    name = spec.get("type")
    if not isinstance(name, str) or name not in GEOMETRY:
        hint = " (row and column are a stack with a direction)" if name in ("row", "column") else ""
        raise vol.Invalid(f"Choose an element type{hint}")
    if name == "polygon" and templates_in(spec.get("points", "")):
        # Its corners are known only once the template is rendered.
        spec = {**spec, "points": "0,0"}
    try:
        payload = spec_payload(
            spec, element["x"], element["y"], element["width"], element["height"]
        )
    except HomeAssistantError as err:
        raise vol.Invalid(str(err)) from err
    # A field that holds a template is checked once the template is rendered.
    # A misspelt key is wrong whatever it holds.
    issues = [
        issue
        for issue in imagespec.validate([payload])
        if issue.message.startswith("unknown key") or not _is_template(payload, issue.path)
    ]
    if issues:
        raise vol.Invalid(
            f"{name} {issues[0].path.removeprefix('[0]').lstrip('.')}: {issues[0].message}"
        )


def bindings(document):
    return {element["entity_id"] for element in document["elements"] if element["entity_id"]}


def template_key(state):
    return state.entity_id.split(".")[0] + ":" + state.attributes.get("device_class", "default")


def output_type(state):
    """Template compatibility follows the value, independently of device class."""
    if state.entity_id.startswith("weather."):
        return "weather"
    if state.entity_id.startswith("binary_sensor.") or state.state in ("on", "off"):
        return "binary"
    if state.attributes.get("unit_of_measurement"):
        return "numeric"
    try:
        float(state.state)
    except ValueError:
        return "text"
    return "numeric"


def sensor_icon(state):
    """Respect an entity's HA icon and otherwise use HA device-class icons."""
    if icon := state.attributes.get("icon"):
        return icon
    if state.entity_id.startswith("weather."):
        return "mdi:" + {
            "clear-night": "weather-night",
            "cloudy": "weather-cloudy",
            "fog": "weather-fog",
            "hail": "weather-hail",
            "lightning": "weather-lightning",
            "lightning-rainy": "weather-lightning-rainy",
            "partlycloudy": "weather-partly-cloudy",
            "pouring": "weather-pouring",
            "rainy": "weather-rainy",
            "snowy": "weather-snowy",
            "snowy-rainy": "weather-snowy-rainy",
            "sunny": "weather-sunny",
            "windy": "weather-windy",
            "windy-variant": "weather-windy-variant",
            "exceptional": "alert-circle",
        }.get(state.state, "weather-cloudy")
    device_class = state.attributes.get("device_class", "")
    active = state.state == "on"
    if state.entity_id.startswith("binary_sensor."):
        pairs = {
            "window": ("window-open", "window-closed"),
            "door": ("door-open", "door-closed"),
            "opening": ("square-outline", "square"),
            "motion": ("motion-sensor", "motion-sensor-off"),
            "occupancy": ("home", "home-outline"),
            "presence": ("home", "home-outline"),
            "plug": ("power-plug", "power-plug-off"),
            "power": ("flash", "flash-off"),
            "battery": ("battery-outline", "battery"),
            "connectivity": ("check-network", "close-network"),
            "lock": ("lock-open", "lock"),
            "light": ("brightness-7", "brightness-5"),
        }
        return (
            "mdi:"
            + pairs.get(device_class, ("checkbox-marked-circle", "radiobox-blank"))[not active]
        )
    return "mdi:" + {
        "temperature": "thermometer",
        "humidity": "water-percent",
        "battery": "battery",
        "power": "flash",
        "energy": "lightning-bolt",
        "illuminance": "brightness-5",
        "pressure": "gauge",
        "voltage": "sine-wave",
        "current": "current-ac",
        "signal_strength": "wifi",
        "timestamp": "calendar-clock",
        "wind_speed": "weather-windy",
        "precipitation": "weather-rainy",
    }.get(device_class, "eye")


def normalize_unit(unit):
    # Some integrations report superscript zero, not the degree sign.
    return {"⁰C": "°C", "⁰F": "°F", "℃": "°C", "℉": "°F"}.get(unit, unit)


def weather_state(state, element, forecasts):
    if not state.entity_id.startswith("weather."):
        return state
    field = element.get("weather_field", "condition")
    when = element.get("weather_when", "now")
    values = state.attributes if when == "now" else {}
    condition = state.state
    if when != "now":
        forecast_type = "hourly" if when == "later_today" else "daily"
        days = {"later_today": 0, "tomorrow": 1, "in_2_days": 2, "in_3_days": 3}[when]
        now = dt_util.now()
        date = (now + timedelta(days=days)).date()
        for item in forecasts.get((state.entity_id, forecast_type), []):
            stamp = dt_util.parse_datetime(item["datetime"])
            local = dt_util.as_local(stamp)
            if local.date() == date and (when != "later_today" or local > now):
                values = item
                break
        condition = values.get("condition", "unavailable")
    value = condition if field == "condition" else str(values.get(field, "unavailable"))
    attrs = dict(state.attributes)
    if field != "condition":
        attrs.pop("icon", None)
        attrs["device_class"] = {
            "templow": "temperature",
            "precipitation": "precipitation",
            "precipitation_probability": "humidity",
            "wind_speed": "wind_speed",
        }.get(field, field)
        attrs["unit_of_measurement"] = (
            "%"
            if field in ("humidity", "precipitation_probability")
            else state.attributes.get({"templow": "temperature"}.get(field, field) + "_unit", "")
        )
    # Keep weather condition icons, use sensor device-class icons for numerical weather values.
    return SimpleNamespace(
        entity_id=state.entity_id
        if field == "condition"
        else "sensor." + state.entity_id.split(".")[1],
        state=value,
        attributes=attrs,
    )


def format_decimals(value, decimals):
    """Round numeric states; a non-numeric state is shown as reported."""
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return value


def as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sensor_values(state, element):
    label = element.get("label") or state.attributes.get("friendly_name", state.entity_id)
    value = state.state
    if value in ("unavailable", "unknown"):
        value = value.capitalize()
    elif "decimals" in element:
        value = format_decimals(value, element["decimals"])
    unit = (
        normalize_unit(state.attributes.get("unit_of_measurement", ""))
        if element.get("show_unit", True)
        else ""
    )
    if state.state in ("unknown", "unavailable"):
        unit = ""
    return {"name": label, "state": value, "unit": unit, "icon": sensor_icon(state)}


def validate_template(template):
    """A sensor template has its own coordinate system, independent of a tag."""
    from ..esl_ble.base import DevicePreset

    schema = vol.Schema(
        {
            vol.Required("width"): vol.All(int, vol.Range(min=16, max=1000)),
            vol.Required("height"): vol.All(int, vol.Range(min=16, max=1000)),
            vol.Required("document"): dict,
            vol.Optional("name", default=""): str,
            vol.Optional("sensor_type", default=""): str,
        }
    )
    result = schema(deepcopy(template))
    if any(
        element.get("type") == "imagespec"
        for element in result["document"].get("elements", [])
        if isinstance(element, dict)
    ):
        raise vol.Invalid("Sensor templates cannot contain imagespec elements")
    result["document"] = validate(
        result["document"],
        DevicePreset("template", "Template", result["width"], result["height"], "BWRY"),
    )
    return result


def substitute(document, values, raw_state, sample_state=None):
    result = deepcopy(document)
    result["elements"] = [
        el for el in result["elements"] if not el.get("state") or el["state"] == raw_state
    ]
    for el in result["elements"]:
        if not el.get("entity_id") and el.get("data_field") and sample_state is not None:
            el["_sample_state"] = sample_state
        if el["type"] == "icon" and raw_state in el.get("state_icons", {}):
            el["icon"] = el["state_icons"][raw_state]
        for field in ("text", "icon"):
            for name, value in values.items():
                el[field] = el.get(field, "").replace("{{" + name + "}}", value)
    return result


def conditional_icon(element, value, fallback):
    """First matching rule wins; numeric ranges are [min, max)."""
    for rule in element.get("icon_rules", []):
        if rule["kind"] == "state" and str(value) == rule["state"]:
            return fallback if rule["icon"] == "{{icon}}" else rule["icon"]
        if rule["kind"] == "range":
            try:
                number = float(value)
            except (ValueError, TypeError):
                continue
            if number >= rule.get("min", float("-inf")) and number < rule.get("max", float("inf")):
                return fallback if rule["icon"] == "{{icon}}" else rule["icon"]
    return element.get("state_icons", {}).get(str(value), fallback)


DYNAMIC_FIELDS = {
    "x",
    "y",
    "width",
    "height",
    "color",
    "background",
    "font_size",
    "text",
    "image",
    "icon",
    "value",
    "min_value",
    "max_value",
    "align",
    "show_label",
    "show_unit",
    "label",
    "decimals",
    "image_fit",
    "dither",
    "visible",
}


def template_variables(state, element):
    value = (
        state.attributes.get(element["attribute"])
        if state is not None and element.get("data_field") == "attribute"
        else state.state
        if state is not None
        else element.get("value", "")
    )
    return {
        "value": value,
        "entity": state,
        "attributes": state.attributes if state is not None else {},
        "entity_id": state.entity_id if state is not None else "",
    }


def resolve_fields(hass, element, state):
    fields = element.get("field_templates", {})
    if not fields:
        return element, state
    if extra := set(fields) - DYNAMIC_FIELDS:
        raise vol.Invalid(f"Unsupported dynamic fields: {sorted(extra)}")
    rendered = {
        field: Template(source, hass).async_render_to_info(
            template_variables(state, element), parse_result=True
        )
        for field, source in fields.items()
    }
    values = {field: info.result() for field, info in rendered.items()}
    dependencies = sorted({entity for info in rendered.values() for entity in info.entities})
    plain = {key: value for key, value in element.items() if not key.startswith("_")}
    plain.update(values)
    plain["field_templates"] = {}
    resolved = ELEMENT(plain)
    resolved.update({key: value for key, value in element.items() if key.startswith("_")})
    resolved["_templated_fields"] = values
    resolved["_template_entities"] = dependencies
    return resolved, state


def resolve_component(hass, element):
    element = deepcopy(element)
    if element.get("_resolved"):
        return element, element.get("_sample_state")
    state = (
        hass.states.get(element["entity_id"])
        if element["entity_id"]
        else element.get("_sample_state")
    )
    if state is None or not element.get("data_field"):
        element, state = resolve_fields(hass, element, state)
        element["_resolved"] = True
        return element, state
    field = element["data_field"]
    values = sensor_values(state, element)
    value = (
        state.attributes.get(element["attribute"], "") if field == "attribute" else values[field]
    )
    if element["type"] == "text":
        element["text"] = str(value)
    elif element["type"] == "image":
        element["image"] = str(value)
    elif element["type"] == "icon":
        element["icon"] = conditional_icon(element, state.state, str(value))
    elif element["type"] in ("progress_bar", "gauge"):
        element["value"] = as_number(value)
    elif element["type"] == "conditional_icon":
        fallback = sensor_icon(state) if element["icon"] == "{{icon}}" else element["icon"]
        element["icon"] = conditional_icon(element, value, fallback)
    element, state = resolve_fields(hass, element, state)
    element["_resolved"] = True
    return element, state


def live_payload(hass, document, templates=None, forecasts=None):
    """The payload with imagespec templates left as written, for an automation.

    None when no element has one: the payload as it is then already is it.
    """
    if not any(
        element["type"] == "imagespec" and templates_in(element["spec"])
        for element in document["elements"]
    ):
        return None
    return compile_payload(hass, document, templates, forecasts, keep_templates=True)


# Pixel settings that shrink with a sensor template drawn smaller than designed.
_SCALED_PIXELS = {
    "min_font_size": 1,
    "padding": 0,
    "line_spacing": 0,
    "line_width": 1,
    "radius": 0,
    "stroke_width": 0,
    "thickness": 1,
}


def _optional(element, **keys):
    """The imagespec keys the element sets, under the names imagespec gives them."""
    return {name: element[key] for name, key in keys.items() if element.get(key) is not None}


def _text_options(element):
    return _optional(
        element,
        valign="valign",
        fit="fit",
        max_lines="max_lines",
        min_size="min_font_size",
        padding="padding",
        line_spacing="line_spacing",
        font="font",
    )


def _set_dither(payload, start, dither):
    if dither is not None:
        for item in payload[start:]:
            item.setdefault("dither", dither)


def compile_payload(hass, document, templates=None, forecasts=None, keep_templates=False):
    """Snapshot HA values on its event loop; render them later in the executor."""
    payload = []
    pending = None
    for element in document["elements"]:
        if pending:
            _set_dither(payload, *pending)
            pending = None
        element, _bound_state = resolve_component(hass, element)
        if not element["visible"]:
            continue
        pending = (len(payload), element.get("dither"))
        x, y, width, height = (element[key] for key in ("x", "y", "width", "height"))
        color = element["color"]
        state = hass.states.get(element["entity_id"]) if element["type"] == "sensor" else None
        if state is not None:
            state = weather_state(state, element, forecasts or {})
        if element["type"] == "sensor" and templates:
            key = element.get("template", "auto")
            if key == "auto" and state is not None:
                key = template_key(state)
                if key not in templates:
                    key = state.entity_id.split(".")[0] + ":default"
                if key not in templates:
                    key = "output:" + output_type(state)
            if key in templates and state is not None:
                template = templates[key]
                nested = substitute(
                    template["document"], sensor_values(state, element), state.state, state
                )
                nested["elements"] = [
                    resolve_component(hass, child)[0] for child in nested["elements"]
                ]
                sx, sy = width / template["width"], height / template["height"]
                for child in nested["elements"]:
                    child["x"] = x + round(child["x"] * sx)
                    child["y"] = y + round(child["y"] * sy)
                    child["width"] = max(1, round(child["width"] * sx))
                    child["height"] = max(1, round(child["height"] * sy))
                    child["font_size"] = max(8, round(child["font_size"] * min(sx, sy)))
                    for key, minimum in _SCALED_PIXELS.items():
                        if child.get(key) is not None:
                            child[key] = max(minimum, round(child[key] * min(sx, sy)))
                payload.extend(compile_payload(hass, nested))
                continue
        if element["type"] == "imagespec":
            spec = (
                element["spec"]
                if keep_templates or element.get("_spec_resolved")
                else resolve_templates(hass, element["spec"], set())
            )
            if keep_templates and frozen_corners(element["spec"]):
                # Corners are percentages of the frame: only the rendered text
                # can be turned into them, so they are as of now.
                spec = {**spec, "points": resolve_templates(hass, spec["points"], set())}
            payload.append(spec_payload(spec, x, y, width, height))
            continue
        if element["type"] in ("progress_bar", "gauge"):
            low, high, value = element["min_value"], element["max_value"], element["value"]
            # No reading, or a field template that collapsed the range.
            if value is None or high <= low:
                continue
            if element["type"] == "progress_bar":
                payload.append(
                    {
                        "type": "progress_bar",
                        "x_start": x,
                        "y_start": y,
                        "x_end": x + width - 1,
                        "y_end": y + height - 1,
                        "progress": (value - low) / (high - low) * 100,
                        "fill": color,
                        "background": "white",
                        "outline": color,
                        **_optional(
                            element,
                            direction="direction",
                            radius="radius",
                            show_percentage="show_percentage",
                            width="line_width",
                            font="font",
                        ),
                    }
                )
            else:
                payload.append(
                    {
                        "type": "gauge",
                        "x": x + width // 2,
                        "y": y + height // 2,
                        "radius": max(1, min(width, height) // 2 - 1),
                        "progress": value,
                        "min_value": low,
                        "max_value": high,
                        "fill": color,
                        "background": "white",
                        "show_value": element.get("show_value", True),
                        "size": element["font_size"],
                        "color": color,
                        **_optional(element, width="thickness", font="font"),
                    }
                )
            continue
        if element["type"] == "image":
            if element["image"]:
                payload.append(
                    {
                        "type": "dlimg",
                        "x": x,
                        "y": y,
                        "xsize": width,
                        "ysize": height,
                        "url": element["image"],
                        "mode": element["image_fit"],
                        "dither": True if element.get("dither") is None else element["dither"],
                        **_optional(element, rotate="rotate", circle="circle"),
                    }
                )
            continue
        if element["type"] in ("icon", "conditional_icon"):
            payload.append(
                {
                    "type": "icon",
                    "x": x,
                    "y": y,
                    "size": min(width, height),
                    "value": element["icon"],
                    "color": color,
                    "anchor": "lt",
                    **_optional(element, stroke_width="stroke_width", stroke_fill="stroke_fill"),
                }
            )
            continue
        if element["type"] in ("rectangle", "line", "ellipse", "triangle", "rounded_rectangle"):
            # A line is always solid; the other shapes can be an outline only.
            fill = (
                {}
                if element["type"] != "line" and element.get("filled") is False
                else {"fill": color}
            )
            outline = {"outline": color, **_optional(element, width="line_width")}
            if element["type"] == "triangle":
                payload.append(
                    {
                        "type": "polygon",
                        "points": f"{x + width // 2},{y};{x + width - 1},{y + height - 1};{x},{y + height - 1}",
                        **fill,
                        **outline,
                    }
                )
            else:
                payload.append(
                    {
                        "type": "ellipse" if element["type"] == "ellipse" else "rectangle",
                        "x_start": x,
                        "y_start": y,
                        "x_end": x + width - 1,
                        "y_end": y + height - 1,
                        **fill,
                        **outline,
                        **(
                            {
                                "radius": element["radius"]
                                if element.get("radius") is not None
                                else max(1, min(width, height) // 5)
                            }
                            if element["type"] == "rounded_rectangle"
                            else {}
                        ),
                    }
                )
            continue
        value = element["text"]
        label = element["label"]
        if element["type"] == "sensor":
            if state is None:
                value = "Unavailable"
                label = label or element["entity_id"]
            else:
                label = label or state.attributes.get("friendly_name", state.entity_id)
                value = state.state
                if value in ("unavailable", "unknown"):
                    value = value.capitalize()
                elif "decimals" in element:
                    value = format_decimals(value, element["decimals"])
                if element["show_unit"] and state.state not in ("unavailable", "unknown"):
                    unit = normalize_unit(state.attributes.get("unit_of_measurement", ""))
                    value += f" {unit}" if unit else ""
            if state is not None:
                icon_size = min(32, height, max(8, width // 4))
                payload.append(
                    {
                        "type": "icon",
                        "x": x + 4,
                        "y": y + max(0, (height - icon_size) // 2),
                        "size": icon_size,
                        "value": sensor_icon(state),
                        "color": color,
                        "anchor": "lt",
                    }
                )
                x += icon_size + 12
                width = max(1, width - icon_size - 12)
            if state is not None and state.entity_id.startswith(("weather.", "binary_sensor.")):
                if element["show_label"]:
                    payload.append(
                        {
                            "type": "text_fit",
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "value": label,
                            "size": 12,
                            "min_size": 8,
                            "fit": "shrink_ellipsis",
                            "color": color,
                            "align": element["align"],
                            **_optional(element, font="font"),
                        }
                    )
                continue
            if element["show_label"]:
                label_height = min(18, max(8, height // 3))
                payload.append(
                    {
                        "type": "text_fit",
                        "x": x,
                        "y": y,
                        "width": width,
                        "height": label_height,
                        "value": label,
                        "size": 12,
                        "min_size": 8,
                        "fit": "shrink_ellipsis",
                        "color": color,
                        "align": element["align"],
                        **_optional(element, font="font"),
                    }
                )
                y += label_height
                height -= label_height
        lines = value.split("\n") if element["type"] == "text" else [value]
        line_height = max(1, height // len(lines))
        for index, line in enumerate(lines):
            if not line:
                continue
            payload.append(
                {
                    "type": "text_fit",
                    "x": x,
                    "y": y + index * line_height,
                    "width": width,
                    "height": line_height,
                    "value": line,
                    "size": element["font_size"],
                    "min_size": 8,
                    "fit": "shrink_ellipsis",
                    "max_lines": 3 if element["type"] == "text" else 1,
                    "color": color,
                    "align": element["align"],
                    **_text_options(element),
                }
            )

    if pending:
        _set_dither(payload, *pending)
    return payload
