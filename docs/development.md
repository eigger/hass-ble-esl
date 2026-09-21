# Development

Tests run against a real Home Assistant core (`pytest-homeassistant-custom-component`), so they need the Python version current Home Assistant requires (3.14):

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pip install -r <(python -c "import json; print('\n'.join(json.load(open('custom_components/ble_esl/manifest.json'))['requirements']))")
pip install -r <(python scripts/ha_component_requirements.py bluetooth usb recorder diagnostics)
pytest
```

CI tests against the Home Assistant release the test package pins (currently 2026.9); the declared minimum in `hacs.json` (2025.12) is supported but not exercised by the suite. `ruff check` and `ruff format --check` (version pinned in `requirements_lint.txt`) must pass; adding a protocol is described in [esl_ble/README.md](../custom_components/ble_esl/esl_ble/README.md).
