"""XTE models confirmed on hardware.

Adding a model is one DevicePreset here. Everything else derives from it:
discovery and model detection from ``extra["device_number"]`` (the tag type
the advertisement carries), image packing from ``width`` / ``height`` /
``colors`` (the palette must exist in ``const.PALETTES``) plus an optional
``extra["rotation"]`` for panels whose native buffer is rotated from the
as-viewed image, and the write guard from membership in PRESETS.

Unknown device numbers are not claimed: some tag types (97, 102, 106, 109,
119, 122) use a different two-plane pixel layout, so a model must be
captured before it is added rather than guessed from its size.
"""

from __future__ import annotations

from ..base import CONFIDENCE_COMMUNITY, CONFIDENCE_REPORTED, DevicePreset
from .protocol import parse_advertisement

PSJ_420 = DevicePreset(
    key="psj-420",
    display_name='PSJ-420 4.2" BWRY',
    width=400,
    height=300,
    colors="BWRY",
    confidence=CONFIDENCE_REPORTED,
    extra={"device_number": 153},
)
# Viewed landscape 250x122; the panel scans along the short edge, so the
# native buffer is portrait 122x250 (rotate 90 degrees counter-clockwise,
# rows padded to 124 pixels). Pushed successfully by a community user with
# this same transaction; not re-tested with this integration.
PSJ_213 = DevicePreset(
    key="psj-213",
    display_name='PSJ-213 2.13" BWRY',
    width=250,
    height=122,
    colors="BWRY",
    confidence=CONFIDENCE_COMMUNITY,
    extra={"device_number": 140, "rotation": 90},
)

PRESETS: dict[str, DevicePreset] = {preset.key: preset for preset in (PSJ_420, PSJ_213)}


def preset_for_advertisement(data: bytes | None) -> DevicePreset | None:
    """The model whose device number the manufacturer data carries, or None."""
    advertisement = parse_advertisement(data)
    if advertisement is None:
        return None
    for preset in PRESETS.values():
        if preset.extra["device_number"] == advertisement.device_number:
            return preset
    return None
