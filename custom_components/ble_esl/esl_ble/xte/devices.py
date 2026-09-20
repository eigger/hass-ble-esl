"""XTE model catalog.

Adding a model is one DevicePreset here. Everything else derives from it:
model detection from ``extra["device_number"]`` (the tag type the
advertisement carries), image packing from ``width`` / ``height`` /
``colors`` (the palette must exist in ``const.PALETTES``) plus an optional
``extra["rotation"]`` for panels whose native buffer is rotated from the
as-viewed image, and the write guard from membership in PRESETS.

Two kinds of entry:

* captured — has a device number; the advertisement selects it automatically.
* size-only — no device number yet; offered in the model picker when an
  XTE tag with an unknown device number is discovered. Once a report pairs
  a device number with the size, fill it in and the same key keeps working.
"""

from __future__ import annotations

from ..base import CONFIDENCE_COMMUNITY, CONFIDENCE_ESTIMATED, CONFIDENCE_REPORTED, DevicePreset
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

# Size-only entries for the rest of the family. Resolutions follow the
# listed panel sizes; device numbers and buffer orientation are unknown
# until a tag of that size is seen (an unknown device number is logged once
# per address). Keys follow the PSJ-<size> naming of the captured models.
_SIZE_ONLY = (
    ("psj-154", '1.54" BWRY', 200, 200),
    ("psj-266", '2.66" BWRY', 296, 152),
    ("psj-290", '2.9" BWRY', 296, 128),
    ("psj-350", '3.5" BWRY', 384, 184),
    ("psj-370", '3.7" BWRY', 416, 240),
)

PRESETS: dict[str, DevicePreset] = {preset.key: preset for preset in (PSJ_420, PSJ_213)}
PRESETS.update(
    {
        key: DevicePreset(
            key=key,
            display_name=name,
            width=width,
            height=height,
            colors="BWRY",
            confidence=CONFIDENCE_ESTIMATED,
        )
        for key, name, width, height in _SIZE_ONLY
    }
)


def preset_for_advertisement(data: bytes | None) -> DevicePreset | None:
    """The captured model whose device number the manufacturer data carries, or None."""
    advertisement = parse_advertisement(data)
    if advertisement is None:
        return None
    for preset in PRESETS.values():
        if preset.extra.get("device_number") == advertisement.device_number:
            return preset
    return None
