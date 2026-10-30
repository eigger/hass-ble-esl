"""Read the ``design`` an older release saved in an automation's action data.

New saves keep only the payload; actions saved earlier still run from their design.
"""

import json

PREFIX = "{{ "
SUFFIX = " | from_json }}"


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
