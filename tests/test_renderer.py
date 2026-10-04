from concurrent.futures import ThreadPoolExecutor
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from homeassistant.exceptions import HomeAssistantError
import pytest

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


def test_empty_payload_renders_solid_background():
    """An explicit empty element list is a valid blank-screen request."""
    image = render_image(_hass(), PRESETS["290"], [], background="yellow")

    assert {image.getpixel((x, y)) for x in range(image.width) for y in range(image.height)} == {
        image.getpixel((0, 0))
    }


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


_PLOT = {
    "type": "plot",
    "x_start": 0,
    "y_start": 0,
    "x_end": 100,
    "y_end": 50,
    "duration": 3600,
    "data": [{"entity": "sensor.pressure"}],
}


async def test_plot_reads_history_on_the_recorder_executor(hass):
    """Home Assistant warns when history is read off the recorder's executor.

    The render stays on the generic executor; only the query is handed to the
    recorder, and the render thread waits for it without blocking the loop.
    """
    recorder_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fake_recorder")
    seen = {}

    class FakeRecorder:
        def async_add_executor_job(self, func):
            return hass.loop.run_in_executor(recorder_pool, func)

    def fake_history(_hass, **kwargs):
        seen["query"] = threading.current_thread().name
        seen["entity_ids"] = kwargs["entity_ids"]
        stamp = "2026-10-04T00:00:00+00:00"
        head = SimpleNamespace(state="1.0", last_changed=stamp)
        return {
            "sensor.pressure": [head, {"state": "2.0", "last_changed": "2026-10-04T00:30:00+00:00"}]
        }

    def render():
        seen["render"] = threading.current_thread().name
        seen["render_id"] = threading.get_ident()
        return render_image(hass, PRESETS["290"], [_PLOT])

    try:
        with (
            patch("custom_components.ble_esl.renderer.get_instance", return_value=FakeRecorder()),
            patch("custom_components.ble_esl.renderer.get_significant_states", fake_history),
        ):
            await hass.async_add_executor_job(render)
    finally:
        recorder_pool.shutdown()

    assert seen["query"].startswith("fake_recorder")
    assert not seen["render"].startswith("fake_recorder")
    assert seen["render_id"] != hass.loop_thread_id
    assert seen["entity_ids"] == ["sensor.pressure"]


async def test_plot_history_timeout_is_a_render_error(hass):
    """A recorder that never answers fails the render instead of hanging it."""

    class StuckRecorder:
        def async_add_executor_job(self, func):
            return hass.loop.create_future()

    with (
        patch("custom_components.ble_esl.renderer.get_instance", return_value=StuckRecorder()),
        patch("custom_components.ble_esl.renderer.HISTORY_TIMEOUT_S", 0.05),
        pytest.raises(HomeAssistantError, match="recorder"),
    ):
        await hass.async_add_executor_job(render_image, hass, PRESETS["290"], [_PLOT])
