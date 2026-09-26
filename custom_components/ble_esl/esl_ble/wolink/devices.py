"""Preset registry for WOLINK BLE ESL devices."""

from __future__ import annotations

from ..base import (
    CONFIDENCE_COMMUNITY,
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
    DevicePreset,
)
from .protocol import ROTATIONS, parse_manufacturer_data


def _p(
    key: str,
    name: str,
    w: int,
    h: int,
    *,
    rotation: int,
    mirror_x: bool = False,
    mirror_y: bool = False,
    split_planes: bool = False,
    disp_ver: int | None = None,
    colors: str = "BWRY",
    confidence: str = CONFIDENCE_ESTIMATED,
) -> DevicePreset:
    if rotation not in ROTATIONS:
        raise ValueError(f"{key}: rotation must be one of {ROTATIONS}, got {rotation}")
    extra: dict[str, bool | int] = {
        "rotation": rotation,
        "mirror_x": mirror_x,
        "mirror_y": mirror_y,
    }
    if split_planes:
        # Two 1bpp frames (black/white, then red) instead of interleaved 2bpp.
        extra["split_planes"] = True
    if disp_ver is not None:
        extra["disp_ver"] = disp_ver
    return DevicePreset(
        key=key,
        display_name=name,
        width=w,
        height=h,
        colors=colors,
        confidence=confidence,
        extra=extra,
    )


PRESETS: dict[str, DevicePreset] = {
    p.key: p
    for p in (
        _p(
            "290",
            '2.9" BWRY',
            296,
            128,
            rotation=270,
            mirror_x=True,
            confidence=CONFIDENCE_HARDWARE,
        ),
        _p(
            "290-bwr",
            '2.9" BWR',
            296,
            128,
            rotation=270,
            split_planes=True,
            disp_ver=0x0303,
            colors="BWR",
            confidence=CONFIDENCE_HARDWARE,
        ),
        _p(
            "350",
            '3.5" BWRY',
            384,
            184,
            rotation=270,
            disp_ver=0x0201,
            confidence=CONFIDENCE_HARDWARE,
        ),
        _p(
            "750",
            '7.5" BWRY',
            800,
            480,
            rotation=0,
            confidence=CONFIDENCE_HARDWARE,
        ),
        _p(
            "420",
            '4.2" BWRY',
            400,
            300,
            rotation=0,
            confidence=CONFIDENCE_REPORTED,
        ),
        _p(
            "266",
            '2.66" BWRY',
            296,
            152,
            rotation=270,
            mirror_x=True,
            confidence=CONFIDENCE_COMMUNITY,
        ),
        _p("154", '1.54" BWRY', 200, 200, rotation=270),
        _p("213", '2.13" BWRY', 250, 122, rotation=270),
        _p("370", '3.7" BWRY', 240, 416, rotation=90),
        _p("583", '5.83" BWRY', 648, 480, rotation=270),
        _p("102", '10.2" BWR', 960, 640, rotation=270, colors="BWR"),
        _p("133", '13.3" BWR', 1600, 1200, rotation=270, colors="BWR"),
    )
}


def preset_for_advertisement(data: bytes | None) -> DevicePreset | None:
    """The preset whose display version the manufacturer data carries, or None."""
    if not data:
        return None
    try:
        parsed = parse_manufacturer_data(data)
    except ValueError:
        return None
    disp_ver = parsed["disp_ver"]
    for preset in PRESETS.values():
        if preset.extra.get("disp_ver") == disp_ver:
            return preset
    return None
