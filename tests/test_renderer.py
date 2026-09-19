from unittest.mock import MagicMock
from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.esl_ble.wolink.devices import PRESETS
from custom_components.ble_esl.renderer import render_image


def test_render_image_bwry():
    """Verify rendering on a BWRY preset (e.g. 290)."""
    preset = PRESETS["290"]

    service = MagicMock()
    service.data = {
        "payload": [
            {
                "type": "rectangle",
                "x_start": 0,
                "y_start": 0,
                "x_end": 100,
                "y_end": 50,
                "fill": "yellow",
            }
        ],
        "rotate": 0,
        "background": "white",
    }

    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")

    image = render_image(hass, preset, service.data["payload"], rotate=service.data.get("rotate", 0), background=service.data.get("background", "white"))

    assert image is not None
    assert image.size == (296, 128)


def test_render_image_bwr():
    """Verify rendering on a BWR preset (e.g. 102)."""
    preset = PRESETS["102"]

    service = MagicMock()
    service.data = {
        "payload": [
            {
                "type": "rectangle",
                "x_start": 0,
                "y_start": 0,
                "x_end": 100,
                "y_end": 50,
                "fill": "red",
            }
        ],
        "rotate": 0,
        "background": "white",
    }

    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")

    image = render_image(hass, preset, service.data["payload"], rotate=service.data.get("rotate", 0), background=service.data.get("background", "white"))

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

    hass = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/mock_fonts")

    service_flat = MagicMock()
    service_flat.data = {
        "payload": [
            {
                "type": "rectangle",
                "x_start": 0,
                "y_start": 0,
                "x_end": 10,
                "y_end": 10,
                "fill": "#b0b0b0",
                "outline": "#b0b0b0",
            }
        ],
        "background": "white",
    }
    img_flat = render_image(hass, preset, service_flat.data["payload"], rotate=service_flat.data.get("rotate", 0), background=service_flat.data.get("background", "white"))

    service_dither = MagicMock()
    service_dither.data = {
        "payload": [
            {
                "type": "rectangle",
                "x_start": 0,
                "y_start": 0,
                "x_end": 10,
                "y_end": 10,
                "fill": "#b0b0b0",
                "outline": "#b0b0b0",
                "dither": "floyd",
            }
        ],
        "background": "white",
    }
    img_dither = render_image(hass, preset, service_dither.data["payload"], rotate=service_dither.data.get("rotate", 0), background=service_dither.data.get("background", "white"))

    w, h = img_flat.size
    unique_flat = {
        img_flat.getpixel((x, y)) for y in range(h) for x in range(w)
    }
    assert len(unique_flat) == 1

    unique_dither = {
        img_dither.getpixel((x, y)) for y in range(h) for x in range(w)
    }
    assert unique_dither == {(0, 0, 0), (255, 255, 255)}
