"""XTE model catalog.

A captured model has a device number and is picked from the advertisement.
A size-only model has none yet and is offered in the model picker when a tag
with an unknown device number shows up; its key stays when the number is
filled in. `rotation` turns the picture into the panel's buffer (counter-
clockwise, as PIL's `Image.rotate`).
"""

from __future__ import annotations

from ..base import DevicePreset
from .wire import parse_advertisement


def _preset(
    key: str,
    name: str,
    width: int,
    height: int,
    *,
    device_number: int | None = None,
    rotation: int = 0,
) -> DevicePreset:
    extra: dict[str, int] = {}
    if device_number is not None:
        extra["device_number"] = device_number
    if rotation:
        extra["rotation"] = rotation
    return DevicePreset(
        key=key,
        display_name=name,
        width=width,
        height=height,
        colors="BWRY",
        extra=extra,
    )


PRESETS: dict[str, DevicePreset] = {
    preset.key: preset
    for preset in (
        _preset(
            "psj-420",
            'PSJ-420 4.2" BWRY',
            400,
            300,
            device_number=153,
        ),
        _preset(
            "psj-213",
            'PSJ-213 2.13" BWRY',
            250,
            122,
            device_number=140,
            rotation=90,
        ),
        _preset("psj-154", '1.54" BWRY', 200, 200),
        _preset("psj-266", '2.66" BWRY', 296, 152, rotation=90),
        _preset("psj-290", '2.9" BWRY', 296, 128, rotation=90),
        _preset("psj-350", '3.5" BWRY', 384, 184),
        _preset("psj-370", '3.7" BWRY', 416, 240),
        _preset("psj-750", '7.5" BWRY', 800, 480),
    )
}


def preset_for_advertisement(data: bytes | None) -> DevicePreset | None:
    """The captured model whose device number the advertisement carries, or None."""
    advertisement = parse_advertisement(data)
    if advertisement is None:
        return None
    for preset in PRESETS.values():
        if preset.extra.get("device_number") == advertisement.device_number:
            return preset
    return None
