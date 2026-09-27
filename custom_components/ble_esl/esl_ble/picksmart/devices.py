"""PickSmart model catalog; the advertisement names the model (device id) and firmware."""

from __future__ import annotations

import dataclasses

from ..base import CONFIDENCE_HARDWARE, DevicePreset
from .image import FORMATS


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
    payload_format: str | None = None,
    tft: bool = False,
    invert_luminance: bool = False,
) -> DevicePreset:
    payload_format = payload_format or ("2bpp" if colors == "BWRY" else "planes")
    if payload_format not in FORMATS:
        raise ValueError(f"{name}: unknown format {payload_format}")
    extra: dict[str, int | bool | str] = {
        "rotation": rotation,
        "mirror_x": mirror_x,
        "mirror_y": mirror_y,
        "format": payload_format,
    }
    if tft:
        extra["tft"] = True
    if invert_luminance:
        extra["invert_luminance"] = True
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
        _preset(0x00A0, '2.1" TFT BW', 250, 132, "BW", rotation=90, mirror_x=True, tft=True),
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
            payload_format="lines",
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
            payload_format="quicklz",
            invert_luminance=True,
        ),
        _preset(0x008B, '10.2" EPD BWR', 960, 640, "BWR", payload_format="quicklz"),
    )
}

# (device id, firmware) -> the format that firmware expects instead.
FIRMWARE_FORMATS = {(0x012B, 0x8101): "lines"}


def preset_for_device(device_id: int, firmware: int) -> DevicePreset | None:
    """The catalog preset for `device_id`, with the format its `firmware` needs."""
    preset = PRESETS.get(f"0x{device_id:04X}")
    if preset is None:
        return None
    payload_format = FIRMWARE_FORMATS.get((device_id, firmware))
    if payload_format is None:
        return preset
    return dataclasses.replace(preset, extra={**preset.extra, "format": payload_format})
