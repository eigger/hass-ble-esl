"""Poshiji models confirmed on hardware.

Adding a model is one DevicePreset here. Everything else derives from it:
discovery and model detection from ``extra["advertisement"]``, image
packing from ``width`` / ``height`` / ``colors`` (the palette must exist in
``const.PALETTES``), and the write guard from membership in PRESETS.
"""

from __future__ import annotations

from ..base import CONFIDENCE_REPORTED, DevicePreset

# ``extra["advertisement"]`` is the model fingerprint: the manufacturer data
# (id 0x5258) minus its final byte. Two PSJ-420 advertisements differed only
# in that byte (1e/1b, observed to change after a screen update); its meaning
# is unconfirmed, so it is excluded from the fingerprint while the exact
# length and the remaining bytes are kept to avoid claiming other XTE models.
PSJ_420 = DevicePreset(
    key="psj-420",
    display_name='PSJ-420 4.2" BWRY',
    width=400,
    height=300,
    colors="BWRY",
    confidence=CONFIDENCE_REPORTED,
    extra={"advertisement": bytes.fromhex("fd024002009964060102ffff")},
)

PRESETS: dict[str, DevicePreset] = {preset.key: preset for preset in (PSJ_420,)}


def preset_for_advertisement(data: bytes | None) -> DevicePreset | None:
    """The model whose fingerprint the manufacturer data carries, or None."""
    if data is None:
        return None
    for preset in PRESETS.values():
        fingerprint: bytes = preset.extra["advertisement"]
        if len(data) == len(fingerprint) + 1 and data.startswith(fingerprint):
            return preset
    return None
