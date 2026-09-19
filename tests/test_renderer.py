from unittest.mock import MagicMock

from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.esl_ble.wolink.devices import PRESETS
from custom_components.ble_esl.renderer import render_image


def _hass():
    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")
    return hass


def _rect(fill, size=(100, 50), **extra):
    return {
        "type": "rectangle",
        "x_start": 0,
        "y_start": 0,
        "x_end": size[0],
        "y_end": size[1],
        "fill": fill,
        **extra,
    }


def test_render_image_bwry():
    """Verify rendering on a BWRY preset (e.g. 290)."""
    preset = PRESETS["290"]

    image = render_image(_hass(), preset, [_rect("yellow")], rotate=0, background="white")

    assert image is not None
    assert image.size == (296, 128)


def test_render_image_bwr():
    """Verify rendering on a BWR preset (e.g. 102)."""
    preset = PRESETS["102"]

    image = render_image(_hass(), preset, [_rect("red")], rotate=0, background="white")

    assert image is not None
    assert image.size == (960, 640)


def test_render_image_per_element_dither():
    """Service has no dither; use per-element dither for photos/charts only."""
    preset = DevicePreset(
        key="bw_test",
        display_name="BW Test",
        width=10,
        height=10,
        colors="BW",
    )
    hass = _hass()

    img_flat = render_image(hass, preset, [_rect("#b0b0b0", size=(10, 10), outline="#b0b0b0")])
    img_dither = render_image(
        hass, preset, [_rect("#b0b0b0", size=(10, 10), outline="#b0b0b0", dither="floyd")]
    )

    w, h = img_flat.size
    unique_flat = {img_flat.getpixel((x, y)) for y in range(h) for x in range(w)}
    assert len(unique_flat) == 1

    unique_dither = {img_dither.getpixel((x, y)) for y in range(h) for x in range(w)}
    assert unique_dither == {(0, 0, 0), (255, 255, 255)}
