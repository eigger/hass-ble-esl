"""PickSmart model catalog; the advertisement names the model (device id) and firmware."""

from __future__ import annotations

import dataclasses

from ..base import CONFIDENCE_HARDWARE, DevicePreset
from .image import ENCODINGS


def _preset(
    device_id: int,
    name: str,
    width: int,
    height: int,
    colors: str,
    *,
    rotation: int = 0,
    mirror_x: bool = False,
    mirror_y: bool = False,
    encoding: str | None = None,
    resample: tuple[int, int] | None = None,
    black_plane: bool = False,
) -> DevicePreset:
    encoding = encoding or ("2bpp" if colors == "BWRY" else "planes")
    if encoding not in ENCODINGS:
        raise ValueError(f"{name}: unknown encoding {encoding}")
    extra: dict[str, int | bool | str] = {
        "rotation": rotation,
        "mirror_x": mirror_x,
        "mirror_y": mirror_y,
        "encoding": encoding,
    }
    if resample:
        extra["resample"] = resample
    if black_plane:
        extra["black_plane"] = True
    key = f"0x{device_id:04X}"
    return DevicePreset(
        key=key,
        display_name=name,
        width=width,
        height=height,
        colors=colors,
        confidence=CONFIDENCE_HARDWARE,
        extra=extra,
    )


PRESETS: dict[str, DevicePreset] = {
    preset.key: preset
    for preset in (
        _preset(
            0x00A0, '2.1" TFT BW', 250, 132, "BW", rotation=90, mirror_x=True, resample=(125, 264)
        ),
        _preset(0x000B, '2.1" EPD BWR', 212, 104, "BWR", rotation=270, mirror_x=True),
        _preset(0x010B, '2.1" EPD BWR', 250, 128, "BWR", rotation=270, mirror_x=True),
        _preset(0x0028, '2.9" EPD BW', 296, 128, "BW", rotation=90),
        _preset(0x0033, '2.9" EPD BWR', 296, 128, "BWR", rotation=90),
        _preset(0x002E, '2.9" EPD BWRY', 296, 128, "BWRY", rotation=90),
        _preset(
            0x022B,
            '3.7" EPD BWR',
            240,
            416,
            "BWR",
            rotation=180,
            mirror_x=True,
            encoding="lines",
        ),
        _preset(0x004B, '4.2" EPD BWR', 400, 300, "BWR"),
        _preset(0x004E, '4.2" EPD BWRY', 400, 300, "BWRY"),
        _preset(
            0x012B,
            '7.5" EPD BWR',
            800,
            480,
            "BWR",
            mirror_y=True,
            encoding="quicklz",
            black_plane=True,
        ),
        _preset(0x008B, '10.2" EPD BWR', 960, 640, "BWR", encoding="quicklz"),
    )
}

# (device id, firmware) -> the encoding that firmware expects instead.
FIRMWARE_ENCODINGS = {(0x012B, 0x8101): "lines"}


def preset_for_device(device_id: int, firmware: int) -> DevicePreset | None:
    """The catalog preset for `device_id`, with the encoding its `firmware` needs."""
    preset = PRESETS.get(f"0x{device_id:04X}")
    if preset is None:
        return None
    encoding = FIRMWARE_ENCODINGS.get((device_id, firmware))
    if encoding is None:
        return preset
    return dataclasses.replace(preset, extra={**preset.extra, "encoding": encoding})
