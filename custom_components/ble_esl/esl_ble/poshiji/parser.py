"""Recognize Poshiji advertisements without inventing battery readings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, MANUFACTURER_ID
from .devices import preset_for_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def is_poshiji_advertisement(info: BluetoothServiceInfoBleak) -> bool:
    return preset_for_advertisement(info.manufacturer_data.get(MANUFACTURER_ID)) is not None


class PoshijiBluetoothDeviceData(BleParser):
    """Parser for Poshiji tags; the advertisement carries no readings."""

    brand = BRAND
    fallback_name = "Poshiji"
    is_advertisement = staticmethod(is_poshiji_advertisement)
