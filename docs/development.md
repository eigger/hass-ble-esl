# Development

Tests run against a real Home Assistant core (`pytest-homeassistant-custom-component`), laid out like Home Assistant Core's component tests under `tests/components/ble_esl/` (the visual editor's browser tests are in `tests/components/ble_esl/frontend/`). They need the Python version current Home Assistant requires (3.14):

```bash
python3.14 -m venv .venv && source .venv/bin/activate
export STANDARDS_CHECKOUT="$(mktemp -d)"
git clone https://github.com/eigger/hass-repo-standards.git "$STANDARDS_CHECKOUT"
git -C "$STANDARDS_CHECKOUT" checkout 0ec31111a81b0ee5702f1d8a17f03616a10a5db6
python -m pip install packaging==26.3
export RUNNER_TEMP="$(mktemp -d)"
export INPUT_DOMAIN=ble_esl
export INPUT_REQUIREMENTS=requirements_test.txt
export INPUT_TEST_PROFILE=ha
export INPUT_EXPECTED_HA_VERSION=2026.10.1
export INPUT_HA_COMPONENTS="bluetooth usb recorder diagnostics frontend panel_custom websocket_api"
python "$STANDARDS_CHECKOUT/actions/python-environment/install.py"
export PAYLOAD_REPOSITORY="$PWD"
export PAYLOAD_DOMAIN=ble_esl
export PYTHONPATH="$STANDARDS_CHECKOUT/scripts${PYTHONPATH:+:$PYTHONPATH}"
python "$STANDARDS_CHECKOUT/scripts/run_payload_contract.py"
python -m pytest tests/components/ble_esl/ -v --timeout 120 --ignore=tests/components/ble_esl/test_payload_examples.py
```

`ble_esl` is a HACS custom integration; it follows Home Assistant Core's structure but makes no claim to Core inclusion or a quality tier. The shared rules it follows are recorded in [STANDARDS.md](../STANDARDS.md) and checked in [ADOPTION_CHECKLIST.md](../ADOPTION_CHECKLIST.md).

## Documented payload contract

The shared installer resolves manifest, test and required HA component dependencies together and runs `pip check`. The payload command above uses those already installed versions; it does not replace imagespec. It executes both [documented action examples](payload.md) with the real HA loader, action schema and production renderer, without dispatching a device command. Run it before the ordinary regression command. A skipped or failed payload contract is not a successful verification.

`test_payload_examples.py` is the exact central collector scaffold. A plain `pytest` including it intentionally fails; it must be collected through `run_payload_contract.py` / the central plugin. After that succeeds, exclude only this scaffold from ordinary regression tests as shown above. The reusable Tests and dependency update workflows perform this sequence automatically.

Use a separate Python 3.14 virtual environment for exact minimum libraries, with `INPUT_DEPENDENCY_MODE=minimum` and `INPUT_MINIMUM_PACKAGES='["imagespec", "blesession"]'` set **before** invoking the same installer and contract. For the separate minimum HA environment use Python 3.13, `INPUT_REQUIREMENTS=requirements_test_min.txt`, `INPUT_CONSTRAINTS=constraints/homeassistant-min.txt` and `INPUT_EXPECTED_HA_VERSION=2025.12.0`; leave dependency mode as current unless explicitly testing another minimum-library combination. Do not install newer renderer packages after resolving an environment to obtain a passing result. Record actual Python, HA, plugin, imagespec and blesession versions with the commands and results. These commands describe reproducible checks; completed checks and remaining gaps for this change are recorded in [ADOPTION_CHECKLIST.md](../ADOPTION_CHECKLIST.md).

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
