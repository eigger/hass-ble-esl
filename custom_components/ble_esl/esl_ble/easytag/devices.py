"""Device presets and choices for easyTag ESL protocol."""

from __future__ import annotations


from ..base import (
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
    DevicePreset,
)

PRESETS: dict[str, DevicePreset] = {
    "33": DevicePreset(
        key="33",
        display_name="1.54\" BWR (ET0154-33B)",
        width=200,
        height=200,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "36": DevicePreset(
        key="36",
        display_name="2.13\" BWR (ETR0213-36B)",
        width=250,
        height=122,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "39": DevicePreset(
        key="39",
        display_name="2.13\" BW (ETR0213-39B)",
        width=250,
        height=122,
        colors="BW",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "3A": DevicePreset(
        key="3A",
        display_name="2.66\" BWR (ET0266-3A)",
        width=296,
        height=152,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "3D": DevicePreset(
        key="3D",
        display_name="2.9\" BWR (ET0290-3DB)",
        width=296,
        height=128,
        colors="BWR",
        confidence=CONFIDENCE_HARDWARE,
        extra={"dither": True},
    ),
    "FF": DevicePreset(
        key="FF",
        display_name="2.9\" BWR Gen1 (ETR290-FF)",
        width=296,
        height=128,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "55": DevicePreset(
        key="55",
        display_name="3.5\" BWR (ET0350-55B)",
        width=384,
        height=184,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "40": DevicePreset(
        key="40",
        display_name="4.2\" BWR (ET0420-40B)",
        width=400,
        height=300,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "43": DevicePreset(
        key="43",
        display_name="4.2\" BWR (ET0420-43B)",
        width=400,
        height=300,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "4F": DevicePreset(
        key="4F",
        display_name="5.8\" BWR (ETR0580-4FB)",
        width=648,
        height=480,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "44": DevicePreset(
        key="44",
        display_name="7.5\" BWR (ET0750-44B)",
        width=800,
        height=480,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
    "64": DevicePreset(
        key="64",
        display_name="10.2\" BWR (ET1020-64)",
        width=960,
        height=640,
        colors="BWR",
        confidence=CONFIDENCE_REPORTED,
        extra={"dither": True},
    ),
}


def preset_choices() -> list[tuple[str, str]]:
    """Return model choices for config flow, verified hardware first."""
    def sort_key(item: tuple[str, DevicePreset]) -> tuple[int, int]:
        _, p = item
        order = {
            CONFIDENCE_HARDWARE: 0,
            CONFIDENCE_REPORTED: 1,
        }
        return (order.get(p.confidence, 2), p.width * p.height)

    out = []
    for key, preset in sorted(PRESETS.items(), key=sort_key):
        label = f"{preset.display_name} — {preset.width}x{preset.height}"
        if not preset.verified:
            label += " (unverified)"
        out.append((key, label))
    return out
