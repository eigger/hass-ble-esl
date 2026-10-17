# Development

Tests run against a real Home Assistant core (`pytest-homeassistant-custom-component`), laid out like Home Assistant Core's component tests under `tests/components/ble_esl/` (the visual editor's browser tests are in `tests/frontend/`). They need the Python version current Home Assistant requires (3.14):

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pip install -r <(python -c "import json; print('\n'.join(json.load(open('custom_components/ble_esl/manifest.json'))['requirements']))")
pip install -r <(python scripts/ha_component_requirements.py bluetooth usb recorder diagnostics frontend panel_custom websocket_api)
pytest
```

`ble_esl` is a HACS custom integration; it follows Home Assistant Core's structure but makes no claim to Core inclusion or a quality tier. The shared rules it follows are recorded in [STANDARDS.md](../STANDARDS.md) and checked in [ADOPTION_CHECKLIST.md](../ADOPTION_CHECKLIST.md).

## Verified environments

CI ([tests.yml](../.github/workflows/tests.yml)) runs the suite against a real Home Assistant in separate environments; the workflow asserts the installed version:

| Job | Python | Home Assistant | Test plugin | Libraries |
|---|---|---|---|---|
| current | 3.14 | 2026.10.1 | `pytest-homeassistant-custom-component` 0.13.372 | latest allowed by `manifest.json` |
| current, minimum libraries | 3.14 | 2026.10.1 | 0.13.372 | exact `blesession` / `imagespec` lower bounds from `manifest.json` |
| minimum HA | 3.13 | 2025.12.0 (`hacs.json`) | 0.13.298 | latest allowed by `manifest.json` |

The minimum environment lives in `requirements_test_min.txt` and `constraints/homeassistant-min.txt` (the `pycares<5` pin is needed by HA 2025.12's `aiodns==3.5.0`). Dependabot leaves both alone: raising the declared minimum needs a real incompatibility with an older Home Assistant and an explicit decision, not a test-tool bump. Test helpers must keep working on both releases (for example `device_of` in the test conftest). Not covered: physical tags beyond those listed in the README.

`ruff check .` and `ruff format --check .` (version pinned in `requirements_lint.txt`) must pass; adding a protocol is described in [esl_ble/README.md](../custom_components/ble_esl/esl_ble/README.md). New dependencies go in `manifest.json` `requirements` (runtime), not in the test requirements, and are exercised by the real-Home-Assistant tests.

The designer frontend's current ownership boundaries, host contracts, UX
invariants, and incremental migration constraints are recorded in the
[designer architecture baseline](designer-architecture.md).
