"""Tests for WOLINK device presets and choices sorting."""

from __future__ import annotations

from custom_components.ble_esl.esl_ble.wolink.devices import (
    PRESETS,
    preset_for_advertisement,
)


def test_presets_catalog():
    """Verify all 12 device presets and their properties."""
    assert len(PRESETS) == 12

    # 2.9" BWRY
    assert PRESETS["290"].width == 296
    assert PRESETS["290"].height == 128
    assert PRESETS["290"].extra.get("rotation") == 270
    assert PRESETS["290"].extra.get("mirror_x") is True

    # 2.9" BWR: two 1bpp columns
    assert PRESETS["290-bwr"].colors == "BWR"
    assert PRESETS["290-bwr"].width == 296
    assert PRESETS["290-bwr"].height == 128
    assert PRESETS["290-bwr"].extra.get("rotation") == 270
    assert PRESETS["290-bwr"].extra.get("mirror_x") is False
    assert PRESETS["290-bwr"].extra.get("mirror_y") is False
    assert PRESETS["290-bwr"].extra.get("display_version") == 0x0303

    assert PRESETS["350"].extra.get("display_version") == 0x0201
    assert PRESETS["370"].extra.get("rotation") == 90
    assert PRESETS["750"].extra.get("rotation") == 0

    assert PRESETS["102"].colors == "BWR"
    assert PRESETS["133"].colors == "BWR"


def test_model_selector_ordering():
    """The config-flow model list orders models by panel size (area)."""
    from custom_components.ble_esl.config_flow import _model_selector_options

    options = _model_selector_options("wolink")
    assert len(options) == 12

    keys = [o["value"] for o in options]
    expected_order = sorted(PRESETS.keys(), key=lambda k: PRESETS[k].width * PRESETS[k].height)
    assert keys == expected_order

    for option in options:
        preset = PRESETS[option["value"]]
        assert option["label"] == f"{preset.display_name} — {preset.width}x{preset.height}"


def test_preset_for_advertisement_uses_display_version():
    """Known display versions select a preset; anything else stays manual."""
    assert preset_for_advertisement(bytes.fromhex("3000000e033003030b9d")).key == "290-bwr"
    assert preset_for_advertisement(bytes.fromhex("3000000e033002010b8b")).key == "350"
    assert preset_for_advertisement(bytes.fromhex("3000000e033004010beb")) is None
    assert preset_for_advertisement(bytes.fromhex("12340201040306050bb8")) is None
    assert preset_for_advertisement(b"\x01\x02") is None
    assert preset_for_advertisement(None) is None
