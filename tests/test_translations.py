"""Translation files: same keys everywhere, and everything the code names exists."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest
import yaml

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "ble_esl"
STRINGS = json.loads((COMPONENT / "strings.json").read_text())
TRANSLATIONS = sorted((COMPONENT / "translations").glob("*.json"))


def flat(node: dict, path: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in node.items():
        full = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            out.update(flat(value, full))
        else:
            out[full] = value
    return out


BASE = flat(STRINGS)


def test_strings_has_no_unresolved_key_references():
    """[%key:...%] references are only resolved for core integrations."""
    assert not [k for k, v in BASE.items() if "[%key:" in v]


@pytest.mark.parametrize("path", TRANSLATIONS, ids=[p.stem for p in TRANSLATIONS])
def test_translation_matches_strings(path: Path):
    translated = flat(json.loads(path.read_text()))
    assert set(translated) == set(BASE), (
        f"missing {sorted(set(BASE) - set(translated))}, extra {sorted(set(translated) - set(BASE))}"
    )
    assert all(isinstance(v, str) and v.strip() for v in translated.values())
    # Placeholders must survive translation.
    for key, source in BASE.items():
        assert set(re.findall(r"\{\w+\}", source)) == set(
            re.findall(r"\{\w+\}", translated[key])
        ), key


def test_entity_translation_keys_exist():
    used: dict[str, set[str]] = {}
    for platform in ("sensor", "binary_sensor", "image", "text", "switch"):
        source = (COMPONENT / f"{platform}.py").read_text()
        used[platform] = set(re.findall(r'_attr_translation_key = "(\w+)"', source))
    for platform, keys in used.items():
        declared = set(STRINGS["entity"].get(platform, {}))
        assert keys <= declared, f"{platform}: {sorted(keys - declared)} not in strings.json"


def test_service_fields_match_services_yaml():
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    assert set(services) == set(STRINGS["services"])
    for name, spec in services.items():
        assert set(spec.get("fields", {})) == set(STRINGS["services"][name]["fields"]), name
