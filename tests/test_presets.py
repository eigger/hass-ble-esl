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
    preset_for_advertisement,
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

    # 2.9" BWR: two 1bpp columns. Community report, so it stays unverified.
    assert PRESETS["290-bwr"].colors == "BWR"
    assert PRESETS["290-bwr"].width == 296
    assert PRESETS["290-bwr"].height == 128
    assert PRESETS["290-bwr"].confidence == CONFIDENCE_COMMUNITY
    assert PRESETS["290-bwr"].verified is False
    assert PRESETS["290-bwr"].extra.get("split_planes") is True
    assert PRESETS["290-bwr"].extra.get("rotate_cw") is False
    assert PRESETS["290-bwr"].extra.get("row_major") is False
    assert PRESETS["290-bwr"].extra.get("mirror") is False
    assert PRESETS["290-bwr"].extra.get("disp_ver") == 0x0303

    assert PRESETS["350"].confidence == CONFIDENCE_HARDWARE
    assert PRESETS["350"].extra.get("disp_ver") == 0x0201
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
    # Community confidence sorts after hardware/reported, so 290-bwr stays out.
    assert "290-bwr" not in keys[:4]

    for option in options:
        preset = PRESETS[option["value"]]
        assert ("(unverified)" in option["label"]) is (not preset.verified)


def test_preset_for_advertisement_uses_display_version():
    """Known display versions select a preset; anything else stays manual."""
    assert preset_for_advertisement(bytes.fromhex("3000000e033003030b9d")).key == "290-bwr"
    assert preset_for_advertisement(bytes.fromhex("3000000e033002010b8b")).key == "350"
    assert preset_for_advertisement(bytes.fromhex("3000000e033004010beb")) is None
    assert preset_for_advertisement(bytes.fromhex("12340201040306050bb8")) is None
    assert preset_for_advertisement(b"\x01\x02") is None
    assert preset_for_advertisement(None) is None
