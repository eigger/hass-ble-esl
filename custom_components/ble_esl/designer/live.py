"""Write what an entity-bound component drew as templates, so a payload follows the entity.

The component is drawn from the entity's state as it is now. Here the pieces
that come straight from the state (a sensor's value, a data field, the icon a
rule picks, a bar's progress) are replaced by a template that gives the same
thing now and follows the entity later, in the states the designer handles
specially too (unavailable, rounded numbers). A piece is only replaced when its
template renders, as Home Assistant renders action data, exactly what was
drawn; anything else stays as drawn, and the component is then reported as
not live.
"""

import json
import math

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template

_UNAVAILABLE = "['unavailable', 'unknown']"


def _literal(value):
    return json.dumps(str(value), ensure_ascii=False)


def shown_value(element):
    """(prelude, expression) for the value a data field shows, as the designer shows it.

    Mirrors ``layout.sensor_values``: an unavailable state is capitalised and a
    number is rounded to the element's decimals; the unit is blank without a state.
    """
    entity = _literal(element["entity_id"])
    field = element.get("data_field")
    if field == "state":
        prelude = f"{{% set v = states({entity}) %}}"
        expression = f"v | capitalize if v in {_UNAVAILABLE} else v"
        decimals = element.get("decimals")
        if decimals is not None:
            expression = (
                f"v | capitalize if v in {_UNAVAILABLE} else "
                f"(('%.{decimals}f' | format(v | float)) if v | float(none) is not none else v)"
            )
        return prelude, expression
    if field == "attribute":
        attribute = _literal(element["attribute"])
        value = f"state_attr({entity}, {attribute})"
        return "", f"({value} if {value} is not none else '')"
    if field == "name":
        return "", f"(state_attr({entity}, 'friendly_name') or {entity})"
    if field == "unit" and element.get("show_unit", True):
        return (
            f"{{% set v = states({entity}) %}}",
            f"'' if v in {_UNAVAILABLE} else (state_attr({entity}, 'unit_of_measurement') or '')",
        )
    return None


def render(hass, template):
    """What Home Assistant renders the template to in action data (a number stays one)."""
    try:
        return Template(template, hass).async_render(parse_result=True)
    except HomeAssistantError:
        return None


def renders_as(hass, template, drawn):
    """Whether the template renders to exactly the text that was drawn."""
    rendered = render(hass, template)
    # A number comes out as its own text, as it is drawn: 21.3 stays, 21.50 would not.
    return isinstance(rendered, str | int | float) and str(rendered) == str(drawn)


def icon_chain(element, prelude, expression, fallback):
    """A template giving the icon the element's rules pick for a value.

    Rules are tried in order, then the per-state icons, as the designer does.
    """
    branches = []
    for rule in element.get("icon_rules", []):
        icon = fallback if rule["icon"] == "{{icon}}" else rule["icon"]
        if rule["kind"] == "state":
            test = f"v | string == {_literal(rule['state'])}"
        else:
            low, high = rule.get("min"), rule.get("max")
            test = "n is not none"
            if low is not None:
                test += f" and n >= {low!r}"
            if high is not None:
                test += f" and n < {high!r}"
        branches.append((test, icon))
    branches.extend(
        (f"v | string == {_literal(state)}", icon)
        for state, icon in element.get("state_icons", {}).items()
    )
    body = "".join(
        f"{{% {'if' if not index else 'elif'} {test} %}}{icon}"
        for index, (test, icon) in enumerate(branches)
    )
    body = body + f"{{% else %}}{fallback}{{% endif %}}" if branches else fallback
    # The rules read the value as shown: ``w``, then ``v`` as text and ``n`` as a number.
    return f"{prelude}{{% set w = {expression} %}}{{% set v = w %}}{{% set n = w | float(none) %}}{body}"


def live_items(hass, element, state, items):
    """Template the items an entity-bound component drew; True when it now follows the entity.

    ``element`` is the component as designed, ``items`` the payload it drew,
    changed in place.
    """
    kind = element["type"]
    if element.get("field_templates"):
        return False
    if kind == "sensor":
        return _sensor_value(hass, element, state, items)
    if kind in ("icon", "conditional_icon") and len(items) == 1 and items[0].get("type") == "icon":
        from .layout import sensor_icon

        # A binary or weather state picks its own icon: a fixed fallback would be wrong later.
        if state.entity_id.startswith(("binary_sensor.", "weather.")):
            return False
        if kind == "icon":
            # The rules read the raw state; what shows without a match is the data field.
            if element["data_field"] != "icon":
                return False
            prelude, expression = "", f"states({_literal(element['entity_id'])})"
            fallback = sensor_icon(state)
        else:
            source = shown_value(element)
            if source is None:
                return False
            prelude, expression = source
            fallback = sensor_icon(state) if element["icon"] == "{{icon}}" else element["icon"]
        template = icon_chain(element, prelude, expression, fallback)
        if not renders_as(hass, template, items[0]["value"]):
            return False
        items[0]["value"] = template
        return True
    source = shown_value(element)
    if source is None:
        return False
    prelude, expression = source
    if kind == "text":
        # Home Assistant turns rendered text that is only a number back into one, so
        # 20.00 would come out as 20.0: more than one decimal cannot be followed.
        if element.get("data_field") == "state" and (element.get("decimals") or 0) >= 2:
            return False
        # One line of text: a value spread over several lines is split when drawn.
        texts = [item for item in items if item.get("type") == "text_fit"]
        template = f"{prelude}{{{{ {expression} }}}}"
        if len(texts) != 1 or not renders_as(hass, template, texts[0]["value"]):
            return False
        texts[0]["value"] = template
        return True
    if kind in ("progress_bar", "gauge") and len(items) == 1:
        low, high = element["min_value"], element["max_value"]
        scaled = f"(x - {low!r}) / {high - low!r} * 100" if kind == "progress_bar" else "x"
        number = f"{prelude}{{% set x = ({expression}) | float(none) %}}"
        progress = f"{number}{{{{ {scaled} if x is not none else 0 }}}}"
        try:
            same = math.isclose(float(render(hass, progress)), float(items[0]["progress"]))
        except (TypeError, ValueError):
            return False
        if not same:
            return False
        items[0]["progress"] = progress
        # No reading draws nothing, as the designer does without a number.
        items[0]["visible"] = f"{number}{{{{ x is not none }}}}"
        return True
    return False


def _sensor_value(hass, element, state, items):
    """A sensor's value text with its unit, followed from the entity.

    Only a plain value with a unit: Home Assistant turns rendered text that is
    only a number back into one (21.50 would come out as 21.5), and the unit
    keeps it text. The unit is read from the entity, as the designer reads it.
    """
    from .layout import format_decimals, normalize_unit  # Imported here: layout imports this.

    if (
        state.entity_id.startswith(("weather.", "binary_sensor."))
        or state.state in ("unavailable", "unknown")
        or element.get("data_field")
        or not element.get("show_unit", True)
    ):
        return False
    unit = normalize_unit(state.attributes.get("unit_of_measurement", ""))
    texts = [index for index, item in enumerate(items) if item.get("type") == "text_fit"]
    if not unit or not texts:
        return False
    decimals = element.get("decimals")
    shown = state.state if decimals is None else format_decimals(state.state, decimals)
    last = items[texts[-1]]
    if last["value"] != f"{shown} {unit}":
        return False
    entity = _literal(state.entity_id)
    value = "v" if decimals is None else f"(('%.{decimals}f' | format(n)) if n is not none else v)"
    template = (
        f"{{% set v = states({entity}) %}}{{% set n = v | float(none) %}}"
        f"{{% set u = state_attr({entity}, 'unit_of_measurement') or '' %}}"
        "{% set u = {'⁰C': '°C', '⁰F': '°F', '℃': '°C', '℉': '°F'}.get(u, u) %}"
        f"{{{{ v | capitalize if v in {_UNAVAILABLE} else {value} ~ (' ' ~ u if u else '') }}}}"
    )
    if not renders_as(hass, template, last["value"]):
        return False
    last["value"] = template
    return True
