"""ETAG advertisement parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import BleParser
from .const import BRAND, NAME_PREFIX

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def is_etag_advertisement(info: BluetoothServiceInfoBleak) -> bool:
    """A local name starting with "ETAG-"."""
    return isinstance(info.name, str) and info.name.startswith(NAME_PREFIX)


class EtagParser(BleParser):
    """ETAG advertisements carry no readings."""

    brand = BRAND
    fallback_name = "ETAG 2.13"
    is_advertisement = staticmethod(is_etag_advertisement)
