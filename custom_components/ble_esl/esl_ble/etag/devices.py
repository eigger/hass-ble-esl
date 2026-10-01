"""ETAG model catalog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import DevicePreset
from .parser import is_etag_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

PRESETS: dict[str, DevicePreset] = {
    "etag213": DevicePreset("etag213", "ETAG 2.13", 250, 122, "BWR"),
}


def preset_for_advertisement(service_info: BluetoothServiceInfoBleak) -> DevicePreset | None:
    """The preset an ETAG advertisement names; the 2.13" is the only model seen so far."""
    return PRESETS["etag213"] if is_etag_advertisement(service_info) else None
