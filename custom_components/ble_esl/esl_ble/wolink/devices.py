"""WOLINK model catalog."""

from __future__ import annotations

from ..base import (
    CONFIDENCE_COMMUNITY,
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
    DevicePreset,
)
from .image import ROTATIONS
from .protocol import parse_advertisement


def _preset(
    key: str,
    name: str,
    width: int,
    height: int,
    *,
    rotation: int,
    mirror_x: bool = False,
    mirror_y: bool = False,
    display_version: int | None = None,
    colors: str = "BWRY",
    confidence: str = CONFIDENCE_ESTIMATED,
) -> DevicePreset:
    if rotation not in ROTATIONS:
        raise ValueError(f"{key}: rotation must be one of {ROTATIONS}, got {rotation}")
    extra: dict[str, int | bool] = {
        "rotation": rotation,
        "mirror_x": mirror_x,
        "mirror_y": mirror_y,
    }
    if display_version is not None:
        extra["display_version"] = display_version
    return DevicePreset(
        key=key,
        display_name=name,
        width=width,
        height=height,
        colors=colors,
        confidence=confidence,
        extra=extra,
    )


PRESETS: dict[str, DevicePreset] = {
    preset.key: preset
    for preset in (
        _preset(
            "290",
            '2.9" BWRY',
            296,
            128,
            rotation=270,
            mirror_x=True,
            confidence=CONFIDENCE_HARDWARE,
        ),
        _preset(
            "290-bwr",
            '2.9" BWR',
            296,
            128,
            rotation=270,
            display_version=0x0303,
            colors="BWR",
            confidence=CONFIDENCE_HARDWARE,
        ),
        _preset(
            "350",
            '3.5" BWRY',
            384,
            184,
            rotation=270,
            display_version=0x0201,
            confidence=CONFIDENCE_HARDWARE,
        ),
        _preset("750", '7.5" BWRY', 800, 480, rotation=0, confidence=CONFIDENCE_HARDWARE),
        _preset("420", '4.2" BWRY', 400, 300, rotation=0, confidence=CONFIDENCE_REPORTED),
        _preset(
            "266",
            '2.66" BWRY',
            296,
            152,
            rotation=270,
            mirror_x=True,
            confidence=CONFIDENCE_COMMUNITY,
        ),
        _preset("154", '1.54" BWRY', 200, 200, rotation=270),
        _preset("213", '2.13" BWRY', 250, 122, rotation=270),
        _preset("370", '3.7" BWRY', 240, 416, rotation=90),
        _preset("583", '5.83" BWRY', 648, 480, rotation=270),
        _preset("102", '10.2" BWR', 960, 640, rotation=270, colors="BWR"),
        _preset("133", '13.3" BWR', 1600, 1200, rotation=270, colors="BWR"),
    )
}


def preset_for_advertisement(data: bytes | None) -> DevicePreset | None:
    """The preset whose display version the advertisement carries, or None."""
    advertisement = parse_advertisement(data)
    if advertisement is None:
        return None
    for preset in PRESETS.values():
        if preset.extra.get("display_version") == advertisement.display_version:
            return preset
    return None
