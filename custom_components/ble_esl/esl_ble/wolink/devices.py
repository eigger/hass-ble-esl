"""Preset registry for WOLINK BLE ESL devices."""

from __future__ import annotations

from ..base import (
    CONFIDENCE_COMMUNITY,
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
    DevicePreset,
)
from .protocol import parse_manufacturer_data


def _p(
    key: str,
    name: str,
    w: int,
    h: int,
    *,
    mirror: bool = False,
    rotate_cw: bool = False,
    row_major: bool = False,
    split_planes: bool = False,
    disp_ver: int | None = None,
    colors: str = "BWRY",
    confidence: str = CONFIDENCE_ESTIMATED,
) -> DevicePreset:
    extra: dict[str, bool | int] = {
        "mirror": mirror,
        "rotate_cw": rotate_cw,
        "row_major": row_major,
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
            mirror=True,
            rotate_cw=True,
            confidence=CONFIDENCE_HARDWARE,
        ),
        # 2.9" BWR reads two 1bpp planes, 128 pixels per column (discussion 55).
        # LED at the top-left: column 0 is the left edge, bit 0 of each column
        # is the bottom. That is the default scan, so no rotate or mirror.
        _p(
            "290-bwr",
            '2.9" BWR',
            296,
            128,
            split_planes=True,
            disp_ver=0x0303,
            colors="BWR",
            confidence=CONFIDENCE_HARDWARE,
        ),
        _p("350", '3.5" BWRY', 384, 184, disp_ver=0x0201, confidence=CONFIDENCE_HARDWARE),
        _p(
            "750",
            '7.5" BWRY',
            800,
            480,
            row_major=True,
            confidence=CONFIDENCE_HARDWARE,
        ),
        _p(
            "420",
            '4.2" BWRY',
            400,
            300,
            row_major=True,
            confidence=CONFIDENCE_REPORTED,
        ),
        _p(
            "266",
            '2.66" BWRY',
            296,
            152,
            mirror=True,
            rotate_cw=True,
            confidence=CONFIDENCE_COMMUNITY,
        ),
        _p("154", '1.54" BWRY', 200, 200),
        _p("213", '2.13" BWRY', 250, 122),
        _p("370", '3.7" BWRY', 240, 416),
        _p("583", '5.83" BWRY', 648, 480),
        _p("102", '10.2" BWR', 960, 640, colors="BWR"),
        _p("133", '13.3" BWR', 1600, 1200, colors="BWR"),
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
