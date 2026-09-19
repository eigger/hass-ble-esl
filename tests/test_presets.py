"""Tests for WOLINK device presets and choices sorting."""

from __future__ import annotations

from custom_components.ble_esl.esl_ble.base import (
    CONFIDENCE_COMMUNITY,
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
)
from custom_components.ble_esl.esl_ble.wolink.devices import (
    PRESETS,
)


def test_presets_catalog():
    """Verify all 11 device presets and their properties."""
    assert len(PRESETS) == 11

    # Verified hardware presets
    assert PRESETS["290"].confidence == CONFIDENCE_HARDWARE
    assert PRESETS["290"].verified is True
    assert PRESETS["290"].width == 296
    assert PRESETS["290"].height == 128
    assert PRESETS["290"].extra.get("mirror") is True
    assert PRESETS["290"].extra.get("rotate_cw") is True

    assert PRESETS["350"].confidence == CONFIDENCE_HARDWARE
    assert PRESETS["350"].verified is True

    assert PRESETS["750"].confidence == CONFIDENCE_HARDWARE
    assert PRESETS["750"].verified is True
    assert PRESETS["750"].extra.get("row_major") is True

    assert PRESETS["420"].confidence == CONFIDENCE_REPORTED
    assert PRESETS["420"].verified is True

    # Community / Estimated presets
    assert PRESETS["266"].confidence == CONFIDENCE_COMMUNITY
    assert PRESETS["266"].verified is False

    assert PRESETS["154"].confidence == CONFIDENCE_ESTIMATED
    assert PRESETS["154"].verified is False

    # BWR colors for 10.2" and 13.3"
    assert PRESETS["102"].colors == "BWR"
    assert PRESETS["133"].colors == "BWR"


def test_model_selector_ordering():
    """The config-flow model list puts verified hardware/reported models first
    and marks the rest as unverified."""
    from custom_components.ble_esl.config_flow import _model_selector_options

    options = _model_selector_options("wolink")
    assert len(options) == 11

    keys = [o["value"] for o in options]
    # First 4 must be verified: 290, 350, 750, 420 (hardware/reported confidence, then area)
    assert set(keys[:4]) == {"290", "350", "750", "420"}

    for option in options:
        preset = PRESETS[option["value"]]
        assert ("(unverified)" in option["label"]) is (not preset.verified)
