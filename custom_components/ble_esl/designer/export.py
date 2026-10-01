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


def export_yaml(payload, background, device_id):
    """YAML for ``ble_esl.write``, plus whatever imagespec rejects in the payload."""
    dump = partial(
        yaml.dump,
        Dumper=_PlainDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    service = {
        "action": "ble_esl.write",
        "target": {"device_id": device_id or "<your device>"},
        "data": {"background": background, "payload": payload},
    }
    return {
        "payload": dump(payload),
        "service": dump(service),
        "issues": [f"{issue.path}: {issue.message}" for issue in validate_payload(payload)],
    }
