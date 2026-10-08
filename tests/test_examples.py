"""Example automations and action snippets are complete YAML documents."""

from pathlib import Path

import pytest
import yaml

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize(
    "path", sorted(EXAMPLES.rglob("*.yaml")), ids=lambda path: str(path.relative_to(EXAMPLES))
)
def test_example_is_an_automation_or_action_yaml_document(path):
    automation = yaml.safe_load(path.read_text())
    assert isinstance(automation, dict)
    actions = automation.get("actions", automation.get("action"))
    if isinstance(actions, str):
        assert actions == "ble_esl.write"
        assert "payload" in automation["data"]
    else:
        assert isinstance(actions, list)
        assert actions
