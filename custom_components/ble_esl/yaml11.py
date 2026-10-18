"""Home Assistant's frontend YAML editor reads YAML 1.1, where ``y`` is a boolean.

A pasted ``y: 22`` is saved back as ``'true': 22`` (and a colour ``y`` as
``true``), so the automation then fails with "Missing required argument 'y'".
PyYAML, which Home Assistant itself uses, is not affected.
"""

from collections.abc import Mapping
import logging
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)

# Plain scalars that YAML 1.1 reads as booleans (compared case-insensitively).
_YAML11_BOOLS = frozenset({"y", "n", "yes", "no", "on", "off"})


class Yaml11SafeDumper(yaml.SafeDumper):
    """Quote strings YAML 1.1 would turn into booleans, so the editor keeps them."""

    def represent_str(self, data):
        if data.lower() in _YAML11_BOOLS:
            return self.represent_scalar("tag:yaml.org,2002:str", data, style='"')
        return super().represent_str(data)


Yaml11SafeDumper.add_representer(str, Yaml11SafeDumper.represent_str)


def repair_yaml11_keys(payload: Any) -> Any:
    """Restore the ``y`` coordinate key a YAML 1.1 editor turned into ``true``.

    Only top-level elements are touched, and only when ``y`` is absent, so a
    correctly written payload is returned unchanged.
    """
    if not isinstance(payload, list):
        return payload
    repaired = []
    changed = False
    for element in payload:
        if isinstance(element, Mapping) and "y" not in element:
            bad = next((key for key in ("true", True) if key in element), None)
            if bad is not None:
                element = {("y" if key == bad else key): value for key, value in element.items()}
                changed = True
        repaired.append(element)
    if changed:
        _LOGGER.warning(
            "A payload element had the key 'true' instead of 'y' (the Home Assistant "
            "YAML editor reads a bare y as a boolean); using 'y'. Write it as \"y\": ..."
        )
    return repaired if changed else payload
