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
    """Verify all 12 device presets and their properties."""
    assert len(PRESETS) == 12

    # Verified hardware presets
    assert PRESETS["290"].confidence == CONFIDENCE_HARDWARE
    assert PRESETS["290"].verified is True
    assert PRESETS["290"].width == 296
    assert PRESETS["290"].height == 128
    assert PRESETS["290"].extra.get("mirror") is True
    assert PRESETS["290"].extra.get("rotate_cw") is True
    assert "split_planes" not in PRESETS["290"].extra

    # 2.9" BWR: two 1bpp planes. Scan flags are provisional, so it stays unverified.
    assert PRESETS["290-bwr"].colors == "BWR"
    assert PRESETS["290-bwr"].width == 296
    assert PRESETS["290-bwr"].height == 128
    assert PRESETS["290-bwr"].confidence == CONFIDENCE_ESTIMATED
    assert PRESETS["290-bwr"].verified is False
    assert PRESETS["290-bwr"].extra.get("split_planes") is True
    assert PRESETS["290-bwr"].extra.get("row_major") is True
    assert PRESETS["290-bwr"].extra.get("mirror") is False

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

    # 10.2" and 13.3" are BWR colors but still interleaved 2bpp, not split planes.
    assert PRESETS["102"].colors == "BWR"
    assert PRESETS["133"].colors == "BWR"
    assert "split_planes" not in PRESETS["102"].extra
    assert "split_planes" not in PRESETS["133"].extra


def test_model_selector_ordering():
    """The config-flow model list puts verified hardware/reported models first
    and marks the rest as unverified."""
    from custom_components.ble_esl.config_flow import _model_selector_options

    options = _model_selector_options("wolink")
    assert len(options) == 12

    keys = [o["value"] for o in options]
    # First 4 must be verified: 290, 350, 750, 420 (hardware/reported confidence, then area)
    assert set(keys[:4]) == {"290", "350", "750", "420"}

    for option in options:
        preset = PRESETS[option["value"]]
        assert ("(unverified)" in option["label"]) is (not preset.verified)
