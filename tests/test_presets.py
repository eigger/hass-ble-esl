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
    preset_choices,
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


def test_preset_choices_ordering():
    """Verify preset_choices orders verified hardware/reported models before unverified ones."""
    choices = preset_choices()
    assert len(choices) == 11

    keys = [k for k, _ in choices]
    # First 4 must be verified: 290, 350, 750, 420 (in sorted order of hardware/reported confidence and area)
    verified_keys = {"290", "350", "750", "420"}
    assert set(keys[:4]) == verified_keys

    # Check unverified markers
    for key, label in choices:
        preset = PRESETS[key]
        if not preset.verified:
            assert "(unverified)" in label
        else:
            assert "(unverified)" not in label
