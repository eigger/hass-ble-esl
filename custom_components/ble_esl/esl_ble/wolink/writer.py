"""WOLINK write session: unlock, upload the compressed picture, refresh."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
from typing import TYPE_CHECKING

from blesession import Notifications, SessionTrace

from ..base import STAGE_FINISH, STAGE_HANDSHAKE, STAGE_TRANSFER, DevicePreset, WriteResult
from .const import AUTH_CHAR, DATA_CHAR, DEVICE_ERRORS, ERROR_UNLOCK_FAILED, STATUS_CHAR
from .image import encode_image
from .wire import (
    compress,
    refresh_command,
    status_error,
    status_idle,
    unlock_response,
    write_data_command,
)

if TYPE_CHECKING:
    from bleak import BleakClient
    from PIL import Image

_LOGGER = logging.getLogger(__name__)

# Compressed payload, and the uncompressed size it expands to.
PreparedImage = tuple[bytes, int]

UNLOCK_SETTLE_S = 0.5
MIN_CHUNK = 200
MAX_CHUNK = 506  # 512-byte ATT attribute limit minus the 6-byte command header
MTU_OVERHEAD = 9  # ATT write header (3) and command header (6)


class WolinkError(Exception):
    """The tag reported an error code."""

    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__(f"device error {code}: {DEVICE_ERRORS.get(code, 'unknown')}")


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> PreparedImage:
    """Encode and compress `image`; CPU-bound, so callers run it in a worker thread."""
    raw = encode_image(image, preset)
    return compress(raw), len(raw)


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[PreparedImage],
    *,
    pacing_s: float = 0.0,
    trace: SessionTrace,
) -> WriteResult:
    """Unlock, then send the picture; `prepared` is awaited once the link is up."""
    payload, raw_size = await prepared
    session = WolinkSession(client, address, pacing_s=pacing_s)
    with trace.timed(STAGE_HANDSHAKE):
        await session.unlock()
    await session.send(payload, raw_size, pacing_s=pacing_s, trace=trace)
    return WriteResult(success=True)


def refresh_timeout(raw_size: int) -> float:
    """How long the panel may take to redraw, by picture size."""
    if raw_size > 100_000:
        return 120.0
    if raw_size > 20_000:
        return 60.0
    return 30.0


class WolinkSession:
    """One connected WOLINK tag."""

    def __init__(self, client: BleakClient, address: str, *, pacing_s: float = 0.0) -> None:
        self.client = client
        self.address = address
        self.pacing_s = max(0.0, pacing_s)

    async def unlock(self) -> None:
        """Answer the auth nonce; a wrong answer makes the tag drop the link.

        Nothing else may be written or subscribed before this.
        """
        nonce = await self.client.read_gatt_char(AUTH_CHAR)
        await self.client.write_gatt_char(AUTH_CHAR, unlock_response(nonce), response=True)
        await asyncio.sleep(UNLOCK_SETTLE_S)
        if not self.client.is_connected:
            raise WolinkError(ERROR_UNLOCK_FAILED)

    def chunk_size(self) -> int:
        """Largest data chunk the negotiated MTU carries, never below 200 bytes."""
        mtu = getattr(self.client, "mtu_size", None)
        if isinstance(mtu, int) and mtu > 0:
            return max(MIN_CHUNK, min(mtu - MTU_OVERHEAD, MAX_CHUNK))
        return MIN_CHUNK

    async def send(
        self,
        payload: bytes,
        raw_size: int,
        *,
        pacing_s: float | None = None,
        trace: SessionTrace | None = None,
    ) -> None:
        """Upload `payload`, then refresh and wait for the tag to go idle."""
        pacing = self.pacing_s if pacing_s is None else max(0.0, pacing_s)
        if trace is None:
            trace = SessionTrace()
        trace.note(bytes=len(payload))
        async with Notifications(self.client, STATUS_CHAR) as status:
            with trace.timed(STAGE_TRANSFER):
                await self.upload(payload, trace, pacing_s=pacing)
                # Frames during the upload only say busy, unless they carry an error.
                for frame in status.clear():
                    if code := status_error(frame):
                        raise WolinkError(code)
            with trace.timed(STAGE_FINISH):
                await self.client.write_gatt_char(
                    DATA_CHAR, refresh_command(len(payload)), response=True
                )
                await status.wait_for(self._refreshed, refresh_timeout(raw_size), step="refresh")

    async def upload(
        self, payload: bytes, trace: SessionTrace, *, pacing_s: float | None = None
    ) -> None:
        """Write `payload` in MTU-sized chunks; `sends` records how far it got."""
        pacing = self.pacing_s if pacing_s is None else max(0.0, pacing_s)
        size = self.chunk_size()
        sends = 0
        trace.note(parts=(len(payload) + size - 1) // size, sends=sends, chunk_size=size)
        try:
            for offset in range(0, len(payload), size):
                chunk = write_data_command(offset, payload[offset : offset + size])
                await self.client.write_gatt_char(DATA_CHAR, chunk, response=True)
                sends += 1
                if pacing > 0:
                    await asyncio.sleep(pacing)
        finally:
            trace.note(sends=sends)

    def _refreshed(self, frame: bytes) -> bool:
        _LOGGER.debug("WOLINK status from %s after refresh: %s", self.address, frame.hex())
        if code := status_error(frame):
            raise WolinkError(code)
        return status_idle(frame)
