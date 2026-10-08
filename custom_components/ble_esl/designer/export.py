"""The designer's display as YAML for a ``ble_esl.write`` automation."""

from functools import partial
import math

from imagespec import validate as validate_payload
import yaml


class _PlainDumper(yaml.SafeDumper):
    """Never emit &anchors: a payload pasted into an automation must read as written."""

    def ignore_aliases(self, data):
        return True

    def increase_indent(self, flow=False, indentless=False):
        # Indent list items under their key, as in Home Assistant's own YAML.
        return super().increase_indent(flow, False)


def _json_value_errors(value, path="payload"):
    """Reject values JSON/HA cannot safely persist, including NaN and infinities."""
    if isinstance(value, dict):
        errors = []
        for key, item in value.items():
            if not isinstance(key, str):
                errors.append(f"{path}: object keys must be strings")
            errors.extend(_json_value_errors(item, f"{path}.{key}"))
        return errors
    if isinstance(value, list):
        return [
            error
            for index, item in enumerate(value)
            for error in _json_value_errors(item, f"{path}[{index}]")
        ]
    if value is None or isinstance(value, (str, bool, int)):
        return []
    if isinstance(value, float):
        return [] if math.isfinite(value) else [f"{path}: number must be finite"]
    return [f"{path}: value is not a JSON scalar"]


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


def plain(value):
    """The value as YAML can write it: Home Assistant returns its own list, dict
    and str subclasses from a rendered template."""
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return str(value)
    return value


def export_yaml(payload, background, device_id, issues=(), live=None):
    """YAML for ``ble_esl.write``, plus what imagespec or an automation would trip on.

    ``live`` is the same payload with its templates left as written: the
    automation then renders them each time it runs, instead of freezing today's
    values.
    """
    dump = partial(
        yaml.dump,
        Dumper=_PlainDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**6,
    )
    payload = plain(payload)
    live = None if live is None else plain(live)
    service = {
        "action": "ble_esl.write",
        "target": {"device_id": device_id or "<your device>"},
        "data": {"background": background, "payload": payload},
    }
    payload_errors = [f"{issue.path}: {issue.message}" for issue in validate_payload(payload)]
    scalar_errors = _json_value_errors(payload)
    if live is not None:
        scalar_errors.extend(_json_value_errors(live))
    render_errors = [issue for issue in issues if issue.startswith("render:")]
    warnings = [issue for issue in issues if not issue.startswith("render:")]
    template_paths = dict.fromkeys(
        [*template_syntax(payload), *(template_syntax(live) if live is not None else [])]
    )
    template_warnings = [
        f"{path}: contains template syntax; Home Assistant renders it when the automation runs"
        for path in template_paths
    ]
    result = {
        "payload": dump(payload),
        "service": dump(service),
        "issues": [
            *issues,
            *payload_errors,
            *template_warnings,
        ],
        "validation_errors": list(dict.fromkeys([*render_errors, *payload_errors, *scalar_errors])),
        "warnings": [*warnings, *template_warnings],
    }
    if live is not None:
        result["live_payload"] = dump(live)
        result["live_service"] = dump(
            {**service, "data": {"background": background, "payload": live}}
        )
    return result


def automation_draft(exported, name):
    """Prefill a new automation without triggers, using templates when available."""
    action = yaml.safe_load(exported.get("live_service", exported["service"]))
    return {
        "alias": name,
        "description": "",
        "triggers": [],
        "conditions": [],
        "actions": [action],
        "mode": "single",
    }
