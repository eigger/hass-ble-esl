"""Recognize PSJ-420 advertisements without inventing battery readings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, MANUFACTURER_ID
from .devices import PSJ_420
from .protocol import is_psj420_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def is_poshiji_advertisement(info: BluetoothServiceInfoBleak) -> bool:
    return is_psj420_advertisement(info.manufacturer_data.get(MANUFACTURER_ID))


class PoshijiBluetoothDeviceData(BleParser):
    """Parser for Poshiji tags; the advertisement carries no readings."""

    brand = BRAND
    fallback_name = PSJ_420.display_name
    is_advertisement = staticmethod(is_poshiji_advertisement)

    def __init__(self, preset=None) -> None:
        super().__init__(preset or PSJ_420)
