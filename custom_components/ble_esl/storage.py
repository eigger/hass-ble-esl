"""The last rendered and last written image of a tag, kept across restarts.

Both are runtime state the write pipeline needs from the previous run:
Prevent Duplicate Send compares a new render against the last image the
tag *received*, and Display In Sync compares the last render against it.
Without them, every restart rewrote every tag on its next automation run
and left Last Updated Content / Preview Content unknown until then.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SAVE_DELAY_S = 1.0
"""Renders can come in bursts (debounced automations); coalesce the writes."""


@dataclass
class StoredImage:
    """A PNG and when it was produced."""

    png: bytes
    at: datetime


@dataclass
class StoredImages:
    """What the store holds for one tag."""

    written: StoredImage | None = None
    """The last image the tag received (Last Updated Content)."""
    preview: StoredImage | None = None
    """The last image rendered, sent or not (Preview Content)."""


class ImageStore:
    """`.storage/ble_esl.<entry_id>.images`: the two PNGs of one tag."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.images"
        )
        self._images = StoredImages()

    @property
    def images(self) -> StoredImages:
        return self._images

    async def async_load(self) -> StoredImages:
        """Read the store; a missing or unreadable file is simply empty."""
        raw = await self._store.async_load()
        if isinstance(raw, dict):
            self._images = StoredImages(
                written=_decode(raw.get("written")),
                preview=_decode(raw.get("preview")),
            )
        return self._images

    def set_written(self, png: bytes, at: datetime) -> None:
        self._images.written = StoredImage(png, at)
        self._schedule_save()

    def set_preview(self, png: bytes, at: datetime) -> None:
        self._images.preview = StoredImage(png, at)
        self._schedule_save()

    async def async_flush(self) -> None:
        """Write now; for unload, so a reload inside the save delay loses nothing."""
        await self._store.async_save(self._as_dict())

    async def async_remove(self) -> None:
        """Delete the file; for when the config entry is removed."""
        await self._store.async_remove()

    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._as_dict, SAVE_DELAY_S)

    def _as_dict(self) -> dict[str, Any]:
        return {
            "written": _encode(self._images.written),
            "preview": _encode(self._images.preview),
        }


def _encode(image: StoredImage | None) -> dict[str, str] | None:
    if image is None:
        return None
    return {"png": base64.b64encode(image.png).decode("ascii"), "at": image.at.isoformat()}


def _decode(raw: Any) -> StoredImage | None:
    if not isinstance(raw, dict):
        return None
    try:
        png = base64.b64decode(raw["png"])
        at = dt_util.parse_datetime(raw["at"])
    except (KeyError, TypeError, ValueError):
        _LOGGER.debug("Ignoring an unreadable stored image (keys: %s)", sorted(raw))
        return None
    if at is None or not png:
        return None
    return StoredImage(png, at)
