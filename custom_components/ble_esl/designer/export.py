"""The designer's display as YAML for a ``ble_esl.write`` automation."""

from functools import partial

from imagespec import validate as validate_payload
import yaml


class _PlainDumper(yaml.SafeDumper):
    """Never emit &anchors: a payload pasted into an automation must read as written."""

    def ignore_aliases(self, data):
        return True

    def increase_indent(self, flow=False, indentless=False):
        # Indent list items under their key, as in Home Assistant's own YAML.
        return super().increase_indent(flow, False)


def template_syntax(value, path="payload"):
    """Paths of strings Home Assistant would render as a template in an automation."""
    if isinstance(value, str):
        return [path] if any(mark in value for mark in ("{{", "{%", "{#")) else []
    if isinstance(value, dict):
        children = ((f"{path}.{key}", item) for key, item in value.items())
    elif isinstance(value, list):
        children = ((f"{path}[{index}]", item) for index, item in enumerate(value))
    else:
        return []
    return [found for child, item in children for found in template_syntax(item, child)]


def export_yaml(payload, background, device_id, issues=()):
    """YAML for ``ble_esl.write``, plus what imagespec or an automation would trip on."""
    dump = partial(
        yaml.dump,
        Dumper=_PlainDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**6,
    )
    service = {
        "action": "ble_esl.write",
        "target": {"device_id": device_id or "<your device>"},
        "data": {"background": background, "payload": payload},
    }
    return {
        "payload": dump(payload),
        "service": dump(service),
        "issues": [
            *issues,
            *(f"{issue.path}: {issue.message}" for issue in validate_payload(payload)),
            *(
                f"{path}: contains template syntax; Home Assistant renders it when the automation runs"
                for path in template_syntax(payload)
            ),
        ],
    }
