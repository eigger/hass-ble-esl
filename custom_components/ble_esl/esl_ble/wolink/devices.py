"""Preset registry for WOLINK BLE ESL devices."""

from __future__ import annotations

from ..base import (
    CONFIDENCE_COMMUNITY,
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
    DevicePreset,
)


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
    colors: str = "BWRY",
    confidence: str = CONFIDENCE_ESTIMATED,
) -> DevicePreset:
    extra: dict[str, bool] = {"mirror": mirror, "rotate_cw": rotate_cw, "row_major": row_major}
    if split_planes:
        # Two 1bpp frames (black/white, then red) instead of interleaved 2bpp.
        extra["split_planes"] = True
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
        # Same panel size as 290, but the controller reads two 1bpp planes
        # (discussion 55). Row order is provisional until a marked photo lands.
        _p(
            "290-bwr",
            '2.9" BWR',
            296,
            128,
            row_major=True,
            split_planes=True,
            colors="BWR",
        ),
        _p("350", '3.5" BWRY', 384, 184, confidence=CONFIDENCE_HARDWARE),
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
