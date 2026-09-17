"""Device presets and lookup for PickSmart (gicisky) ESL protocol."""

from __future__ import annotations

import dataclasses

from ..base import CONFIDENCE_HARDWARE, DevicePreset

PRESETS: dict[str, DevicePreset] = {
    "0x00A0": DevicePreset(
        key="0x00A0",
        display_name="2.1\" TFT BW",
        width=250,
        height=132,
        colors="BW",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "tft": True,
            "rotation": 90,
            "mirror_x": True,
        },
    ),
    "0x000B": DevicePreset(
        key="0x000B",
        display_name="2.1\" EPD BWR",
        width=212,
        height=104,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "rotation": 270,
            "mirror_x": True,
        },
    ),
    "0x010B": DevicePreset(
        key="0x010B",
        display_name="2.1\" EPD BWR",
        width=250,
        height=128,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "rotation": 270,
            "mirror_x": True,
        },
    ),
    "0x0028": DevicePreset(
        key="0x0028",
        display_name="2.9\" EPD BW",
        width=296,
        height=128,
        colors="BW",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "rotation": 90,
        },
    ),
    "0x0033": DevicePreset(
        key="0x0033",
        display_name="2.9\" EPD BWR",
        width=296,
        height=128,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "rotation": 90,
        },
    ),
    "0x002E": DevicePreset(
        key="0x002E",
        display_name="2.9\" EPD BWRY",
        width=296,
        height=128,
        colors="BWRY",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "rotation": 90,
            "four_color": True,
        },
    ),
    "0x022B": DevicePreset(
        key="0x022B",
        display_name="3.7\" EPD BWR",
        width=240,
        height=416,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "rotation": 180,
            "mirror_x": True,
            "compression": True,
        },
    ),
    "0x004B": DevicePreset(
        key="0x004B",
        display_name="4.2\" EPD BWR",
        width=400,
        height=300,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={
        },
    ),
    "0x004E": DevicePreset(
        key="0x004E",
        display_name="4.2\" EPD BWRY",
        width=400,
        height=300,
        colors="BWRY",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "four_color": True,
        },
    ),
    "0x012B": DevicePreset(
        key="0x012B",
        display_name="7.5\" EPD BWR",
        width=800,
        height=480,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "mirror_y": True,
            "invert_luminance": True,
            "compression2": True,
        },
    ),
    "0x008B": DevicePreset(
        key="0x008B",
        display_name="10.2\" EPD BWR",
        width=960,
        height=640,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={
            "compression2": True,
        },
    ),
}


def apply_firmware_quirks(preset: DevicePreset, firmware: int) -> DevicePreset:
    """Apply model-specific firmware quirks to a preset."""
    if preset.key == "0x012B" and firmware == 0x8101:
        new_extra = dict(preset.extra)
        new_extra["compression"] = True
        new_extra["compression2"] = False
        return dataclasses.replace(preset, extra=new_extra)
    return preset


def get_device_preset(device_id: int, firmware: int) -> DevicePreset | None:
    """Retrieve device preset by device_id and apply firmware-specific adjustments."""
    key = f"0x{device_id:04X}"
    preset = PRESETS.get(key)
    if preset is None:
        return None
    return apply_firmware_quirks(preset, firmware)


def preset_choices() -> list[tuple[str, str]]:
    """Return model choices for config flow."""
    def sort_key(item: tuple[str, DevicePreset]) -> tuple[int, int]:
        _, p = item
        return (0 if p.verified else 1, p.width * p.height)

    out = []
    for key, preset in sorted(PRESETS.items(), key=sort_key):
        label = f"{preset.display_name} — {preset.width}x{preset.height}"
        if not preset.verified:
            label += " (unverified)"
        out.append((key, label))
    return out
