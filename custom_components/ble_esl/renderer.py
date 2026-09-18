import logging
import os

from homeassistant.components.recorder.history import get_significant_states
from homeassistant.exceptions import HomeAssistantError
from imagespec import RenderContext, RenderError, render

_LOGGER = logging.getLogger(__name__)

PALETTES: dict[str, list[str]] = {
    "BW": ["black", "white"],
    "BWR": ["black", "white", "red"],
    "BWRY": ["black", "white", "red", "yellow"],
}


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
        return get_significant_states(
            hass,
            start_time=start,
            entity_ids=list(entity_ids),
            significant_changes_only=False,
            minimal_response=True,
            no_attributes=False,
        )

    icons_dir = os.path.join(os.path.dirname(__file__), "fonts")

    return RenderContext(
        font_resolver=font_resolver,
        history_provider=history_provider,
        default_font=default_font,
        palette=palette,
        icons_dir=icons_dir,
        allow_local_images=True,
    )


def render_image(entity_id, preset, service, hass):
    """Render an image using imagespec tailored to the device preset."""
    colors = getattr(preset, "colors", "BWRY")
    palette = PALETTES.get(colors, ["black", "white", "red", "yellow"])

    try:
        return render(
            payload=service.data.get("payload", ""),
            width=preset.width,
            height=preset.height,
            rotate=int(service.data.get("rotate", 0)),
            rotate_mode="canvas",  # ESL panel: fixed resolution, background rotates
            background=service.data.get("background", "white"),
            dither=False,
            context=_make_context(
                hass, default_font="NotoSansKR-Regular.ttf", palette=palette
            ),
        )
    except RenderError as err:
        raise HomeAssistantError(str(err)) from err
