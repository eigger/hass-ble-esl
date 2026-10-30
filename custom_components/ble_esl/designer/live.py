"""Write what an entity-bound component drew as templates, so a payload follows the entity.

The component is drawn from the entity's state as it is now. Here the pieces
that come straight from the state (a sensor's value, a data field, the icon a
rule picks, a bar's progress) are replaced by a template that gives the same
thing now and follows the entity later. A piece is only replaced when its
template renders exactly what was drawn; anything else stays as drawn, and the
component is then reported as not live.
"""

import json
import math

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template


def _literal(value):
    return json.dumps(str(value), ensure_ascii=False)


def source_expression(element):
    """The template expression for the value a component shows, or None."""
    entity = _literal(element["entity_id"])
    field = element.get("data_field")
    if field == "state":
        return f"states({entity})"
    if field == "attribute":
        return f"state_attr({entity}, {_literal(element['attribute'])})"
    if field == "name":
        return f"(state_attr({entity}, 'friendly_name') or {entity})"
    if field == "unit":
        return f"(state_attr({entity}, 'unit_of_measurement') or '')"
    return None


def render(hass, template):
    """What Home Assistant renders the template to, as text; None when it cannot."""
    try:
        return str(Template(template, hass).async_render(parse_result=False))
    except HomeAssistantError:
        return None


def icon_chain(element, expression, fallback):
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
    if branches:
        body += f"{{% else %}}{fallback}{{% endif %}}"
    else:
        body = fallback
    return f"{{% set v = {expression} %}}{{% set n = v | float(none) %}}{body}"


def live_items(hass, element, state, items):
    """Template the items an entity-bound component drew; True when it now follows the entity.

    ``items`` is the payload the component produced, changed in place.
    """
    from .importer import value_template  # Imported here: importer needs layout.

    kind = element["type"]
    if element.get("field_templates"):
        return False
    if kind == "sensor":
        templated, _ = value_template(element, state, items)
        changed = [
            (index, new)
            for index, (old, new) in enumerate(zip(items, templated, strict=True))
            if new != old
        ]
        if not changed:
            return False
        for index, new in changed:
            if render(hass, new["value"]) != str(items[index]["value"]):
                return False
        for index, new in changed:
            items[index] = new
        return True
    if state is None:
        return False
    if kind in ("icon", "conditional_icon") and len(items) == 1 and items[0].get("type") == "icon":
        from .layout import sensor_icon

        # A binary or weather state picks its own icon: a fixed fallback would be wrong later.
        if state.entity_id.startswith(("binary_sensor.", "weather.")):
            return False
        if kind == "icon":
            # The rules read the state; what shows without a match is the data field.
            if element["data_field"] != "icon":
                return False
            expression = f"states({_literal(element['entity_id'])})"
            fallback = sensor_icon(state)
        else:
            expression = source_expression(element)
            if expression is None:
                return False
            fallback = sensor_icon(state) if element["icon"] == "{{icon}}" else element["icon"]
        template = icon_chain(element, expression, fallback)
        if render(hass, template) != str(items[0]["value"]):
            return False
        items[0]["value"] = template
        return True
    expression = source_expression(element)
    if expression is None or state is None:
        return False
    if kind == "text":
        # One line of text: a value spread over several lines is split when drawn.
        texts = [item for item in items if item.get("type") == "text_fit"]
        if len(texts) != 1 or render(hass, "{{ " + expression + " }}") != str(texts[0]["value"]):
            return False
        texts[0]["value"] = "{{ " + expression + " }}"
        return True
    if kind in ("progress_bar", "gauge") and len(items) == 1:
        low, high = element["min_value"], element["max_value"]
        number = f"({expression}) | float(none)"
        scaled = f"(x - {low!r}) / {high - low!r} * 100" if kind == "progress_bar" else "x"
        progress = f"{{% set x = {number} %}}{{{{ {scaled} if x is not none else 0 }}}}"
        shown = render(hass, progress)
        try:
            same = math.isclose(float(shown), float(items[0]["progress"]), abs_tol=1e-9)
        except (TypeError, ValueError):
            return False
        if not same:
            return False
        items[0]["progress"] = progress
        # No reading draws nothing, as the designer does without a number.
        items[0]["visible"] = f"{{{{ ({number}) is not none }}}}"
        return True
    return False
