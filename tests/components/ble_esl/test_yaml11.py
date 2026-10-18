"""The Home Assistant YAML editor reads a bare ``y`` as a boolean."""

import yaml

from custom_components.ble_esl.designer.export import _PlainDumper
from custom_components.ble_esl.yaml11 import Yaml11SafeDumper, repair_yaml11_keys


def test_repairs_string_and_bool_keys() -> None:
    payload = [{"type": "text", "x": 1, "true": 22}, {"type": "icon", True: 5}]
    assert repair_yaml11_keys(payload) == [
        {"type": "text", "x": 1, "y": 22},
        {"type": "icon", "y": 5},
    ]
    # The caller's payload is not mutated.
    assert payload[0] == {"type": "text", "x": 1, "true": 22}


def test_leaves_correct_payloads_alone() -> None:
    payload = [{"type": "text", "x": 1, "y": 2, "true": 3}, {"type": "line"}]
    assert repair_yaml11_keys(payload) is payload
    assert repair_yaml11_keys("{{ template }}") == "{{ template }}"


def test_only_top_level_keys_are_repaired() -> None:
    payload = [{"type": "plot", "data": [{"true": 1}]}]
    assert repair_yaml11_keys(payload) is payload


def test_dumper_quotes_yaml11_booleans() -> None:
    for dumper in (Yaml11SafeDumper, _PlainDumper):
        text = yaml.dump({"y": 10, "color": "y", "text": "yes", "name": "Yacht"}, Dumper=dumper)
        assert '"y": 10' in text
        assert 'color: "y"' in text
        assert 'text: "yes"' in text
        assert "name: Yacht" in text
        assert yaml.safe_load(text) == {"y": 10, "color": "y", "text": "yes", "name": "Yacht"}
