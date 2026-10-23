import asyncio
import base64
import concurrent.futures
from dataclasses import replace
from io import BytesIO
import logging
import math
import os
import threading

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.exceptions import HomeAssistantError
from imagespec import RenderContext, RenderError, render
from imagespec.dispatch import render_element
from imagespec.state import RenderState
from PIL import Image

_LOGGER = logging.getLogger(__name__)

# How long a render thread waits for the recorder to answer one history query.
HISTORY_TIMEOUT_S = 60

PALETTES: dict[str, list[str]] = {
    "BW": ["black", "white"],
    "BWR": ["black", "white", "red"],
    "BWRY": ["black", "white", "red", "yellow"],
}


def encode_png(image: Image.Image) -> bytes:
    """PNG-encode a rendered image (CPU-bound; run in an executor)."""
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


async def _run_on_recorder(hass, func):
    return await get_instance(hass).async_add_executor_job(func)


def _make_context(hass, *, default_font, palette):
    def font_resolver(name):
        base_name = os.path.basename(name)

        # 1. Check local ble_esl component fonts directory
        local_font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        local_path = os.path.join(local_font_dir, base_name)
        if os.path.exists(local_path):
            return local_path

        # 2. Check Home Assistant www/fonts
        www_fonts_dir = hass.config.path("www/fonts")
        www_path = os.path.join(www_fonts_dir, base_name)
        if os.path.exists(www_path):
            return www_path

        return None

    def history_provider(entity_ids, start, end):
        """Read history on the recorder's executor, as Home Assistant requires.

        The render runs on a generic executor thread (CPU-bound, so it must not
        hold the recorder's database thread); only the query is handed over, and
        this thread waits for it. Callers must therefore be off the event loop, as every
        render already is; on the loop this would block the very thing it waits for.
        """
        if hass.loop_thread_id == threading.get_ident():
            raise RuntimeError("render_image must run in an executor, not on the event loop")

        def query():
            return get_significant_states(
                hass,
                start_time=start,
                entity_ids=list(entity_ids),
                significant_changes_only=False,
                minimal_response=True,
                no_attributes=False,
            )

        future = asyncio.run_coroutine_threadsafe(_run_on_recorder(hass, query), hass.loop)
        try:
            return future.result(HISTORY_TIMEOUT_S)
        except concurrent.futures.TimeoutError as err:
            future.cancel()
            raise HomeAssistantError("Timed out reading history from the recorder") from err

    return RenderContext(
        font_resolver=font_resolver,
        history_provider=history_provider,
        default_font=default_font,
        palette=palette,
        allow_local_images=True,
    )


def oriented_preset(preset, rotation):
    """Logical canvas dimensions for a tag mounted sideways."""
    if rotation % 180:
        return replace(preset, width=preset.height, height=preset.width)
    return preset


def rotated_size(width, height, angle):
    """Expanded Pillow rotation dimensions, without allocating a pixel surface."""
    angle = angle % 360
    if angle % 90 == 0:
        return (height, width) if angle in (90, 270) else (width, height)
    sine = abs(round(math.sin(math.radians(angle)), 15))
    cosine = abs(round(math.cos(math.radians(angle)), 15))
    extent_x, extent_y = width * cosine + height * sine, width * sine + height * cosine
    return (
        math.ceil(width / 2 + extent_x / 2) - math.floor(width / 2 - extent_x / 2),
        math.ceil(height / 2 + extent_y / 2) - math.floor(height / 2 - extent_y / 2),
    )


def _prepare_payload(payload, context):
    """Lower free-angle groups to portable imagespec images in the render worker.

    imagespec 1.1 accepts numeric group angles but only draws quarter turns.
    Rasterizing just these groups keeps alpha/layer order and leaves the source
    components and their live bindings intact in the designer document.
    """
    prepared = []
    for element in payload:
        item = dict(element)
        if "elements" in item:
            item["elements"] = _prepare_payload(item["elements"], context)
        angle = float(item.get("rotate", 0) or 0)
        if item.get("type") == "group" and angle % 90:
            width, height = round(item["width"]), round(item["height"])
            state = RenderState(Image.new("RGBA", (width, height)), width, height, context)
            render_element(state, {**item, "x": 0, "y": 0, "rotate": 0})
            tile = state.img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
            item = {
                "type": "dlimg",
                "x": item.get("x", 0),
                "y": item.get("y", 0),
                "xsize": tile.width,
                "ysize": tile.height,
                "url": "data:image/png;base64," + base64.b64encode(encode_png(tile)).decode(),
                "dither": item.get("dither", False),
            }
        prepared.append(item)
    return prepared


def prepare_payload(hass, preset, payload):
    """Produce a portable payload for export; call in an executor."""
    palette = PALETTES.get(preset.colors, ["black", "white", "red", "yellow"])
    return _prepare_payload(
        payload, _make_context(hass, default_font="NotoSansKR-Regular.ttf", palette=palette)
    )


def render_image(
    hass,
    preset,
    payload,
    *,
    rotate: int = 0,
    background: str = "white",
) -> Image.Image:
    """Render an imagespec payload for the device preset (CPU-bound; run in an executor)."""
    colors = getattr(preset, "colors", "BWRY")
    palette = PALETTES.get(colors, ["black", "white", "red", "yellow"])

    try:
        return render(
            payload=prepare_payload(hass, preset, payload),
            width=preset.width,
            height=preset.height,
            rotate=int(rotate),
            rotate_mode="canvas",  # ESL panel: fixed resolution, background rotates
            background=background,
            dither=False,
            context=_make_context(hass, default_font="NotoSansKR-Regular.ttf", palette=palette),
        )
    except RenderError as err:
        raise HomeAssistantError(str(err)) from err
