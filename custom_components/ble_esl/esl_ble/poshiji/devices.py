"""Poshiji models confirmed by the device owner."""

from ..base import CONFIDENCE_REPORTED, DevicePreset

PSJ_420 = DevicePreset(
    key="psj-420", display_name="PSJ-420 4.2\" BWRY",
    width=400, height=300, colors="BWRY", confidence=CONFIDENCE_REPORTED,
)
PRESETS = {PSJ_420.key: PSJ_420}
