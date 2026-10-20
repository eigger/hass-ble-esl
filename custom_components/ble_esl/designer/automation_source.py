"""Keep component templates intact while HA renders an automation's action data."""

import json

PREFIX = "{{ "
SUFFIX = " | from_json }}"


def encode_design(document):
    """Return one constant expression; nested component Jinja stays literal.

    HA renders action data recursively, but does not render a template's result
    again. Decode the JSON only once HA reaches the write action, leaving the
    component renderer to supply its own value/entity context.
    """
    return (
        PREFIX + json.dumps(json.dumps(document, ensure_ascii=False), ensure_ascii=False) + SUFFIX
    )


def decode_design(value):
    """Accept HA's rendered object or our exact constant expression, without eval."""
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.startswith(PREFIX) or not value.endswith(SUFFIX):
        raise ValueError("Expected a designer document or encoded designer source")
    document = json.loads(json.loads(value[len(PREFIX) : -len(SUFFIX)]))
    if not isinstance(document, dict):
        raise ValueError("The designer source must be an object")
    return document
