"""Hipoink ETAG protocol, verified on a 2.13-inch BWR tag."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import AdvertisementInfo, Capabilities, EslProtocol
from . import writer
from .devices import PRESETS, preset_for_advertisement
from .parser import EtagParser, is_etag_advertisement

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


class EtagProtocol(EslProtocol):
    """ETAG ESL protocol."""

    id = "etag"
    label = "ETAG"
    name = "Hipoink / ETAG (FFE0)"
    capabilities = Capabilities(
        passive_battery=False,
        session_battery=False,
        session_temperature=False,
        palettes=("BWR",),
    )
    PRESETS = PRESETS
    parser_cls = EtagParser
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """ETAG advertisements carry no readings, only the model."""
        preset = preset_for_advertisement(service_info)
        if preset is None:
            return None
        return AdvertisementInfo(model_key=preset.key)


__all__ = [
    "PRESETS",
    "EtagParser",
    "EtagProtocol",
    "is_etag_advertisement",
    "preset_for_advertisement",
]
