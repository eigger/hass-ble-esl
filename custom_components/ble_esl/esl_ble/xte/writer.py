"""XTE write session: start command, blocks, end command, each command answered."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
from typing import TYPE_CHECKING

from blesession import Notifications, SessionTrace, write_chunks

from ..base import STAGE_FINISH, STAGE_HANDSHAKE, STAGE_TRANSFER, DevicePreset, WriteResult
from .const import (
    CMD_END,
    CMD_START,
    MAX_CHUNK,
    MIN_CHUNK,
    NOTIFY_SETTLE_S,
    NOTIFY_UUID,
    REPLY_END,
    REPLY_START,
    REPLY_TIMEOUT_S,
    SERVICE_UUID,
    WRITE_UUID,
)
from .image import buffer_size, encode_image
from .wire import XteError, blocks, check_reply, command, image_object

if TYPE_CHECKING:
    from bleak import BleakClient
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> bytes:
    """Encode `image` into an XTEK object; CPU-bound, so callers run it in a worker thread."""
    return image_object(encode_image(image, preset), *buffer_size(preset))


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[bytes],
    *,
    pacing_s: float = 0.0,
    trace: SessionTrace,
) -> WriteResult:
    """Send the object once the link is up."""
    obj = await prepared
    await XteSession(client, address, pacing_s=pacing_s).send(obj, trace=trace)
    return WriteResult(success=True)


class XteSession:
    """One connected XTE tag."""

    def __init__(self, client: BleakClient, address: str, *, pacing_s: float = 0.0) -> None:
        self.client = client
        self.address = address
        self.pacing_s = max(0.0, pacing_s)
        self.settle_s = NOTIFY_SETTLE_S
        self.reply_timeout_s = REPLY_TIMEOUT_S

    async def send(self, obj: bytes, *, trace: SessionTrace | None = None) -> None:
        """Announce the object, write its blocks, then end; both commands must be answered."""
        if trace is None:
            trace = SessionTrace()
        write_char, notify_char = self._characteristics()
        size = self.chunk_size(write_char)
        frames = blocks(obj)
        trace.note(settle_s=self.settle_s, parts=len(frames), bytes=len(obj), chunk_size=size)
        async with Notifications(self.client, notify_char, settle=self.settle_s) as replies:
            with trace.timed(STAGE_HANDSHAKE):
                start = bytes((CMD_START,)) + len(obj).to_bytes(4, "big")
                await self._command(replies, write_char, start, size, REPLY_START)
            # Blocks are not acknowledged, so the transfer stage is pacing plus
            # the write-without-response throughput.
            with trace.timed(STAGE_TRANSFER):
                for frame in frames:
                    await self._write(write_char, frame, size)
            # The end command is answered once the tag has taken the image.
            with trace.timed(STAGE_FINISH):
                await self._command(replies, write_char, bytes((CMD_END, 0)), size, REPLY_END)

    def _characteristics(self) -> tuple[BleakGATTCharacteristic, BleakGATTCharacteristic]:
        service = self.client.services.get_service(SERVICE_UUID)
        if service is None:
            raise XteError("XTE service missing")
        write_char = service.get_characteristic(WRITE_UUID)
        notify_char = service.get_characteristic(NOTIFY_UUID)
        if write_char is None or notify_char is None:
            raise XteError("XTE characteristics missing")
        if (
            "write-without-response" not in write_char.properties
            or "notify" not in notify_char.properties
        ):
            raise XteError("XTE characteristic properties do not match")
        return write_char, notify_char

    def chunk_size(self, write_char: BleakGATTCharacteristic) -> int:
        """The protocol's write-without-response limit, at most 244 bytes."""
        size = min(MAX_CHUNK, write_char.max_write_without_response_size)
        if size < MIN_CHUNK:
            raise XteError(f"Invalid XTE write-without-response size: {size}")
        _LOGGER.debug("XTE %s write chunk size: %s bytes", self.address, size)
        return size

    async def _command(
        self,
        replies: Notifications,
        char: BleakGATTCharacteristic,
        payload: bytes,
        size: int,
        expected: bytes,
    ) -> None:
        replies.clear()
        await self._write(char, command(payload), size)
        await replies.wait_for(
            lambda frame: self._check_reply(frame, expected),
            self.reply_timeout_s,
            step=f"command {payload[0]:#04x}",
        )

    def _check_reply(self, frame: bytes, expected: bytes) -> bool:
        _LOGGER.debug("XTE status from %s: %s", self.address, frame.hex())
        return check_reply(frame, expected)

    async def _write(self, char: BleakGATTCharacteristic, frame: bytes, size: int) -> None:
        """One command or block as consecutive ATT writes, then the pacing pause.

        The pause is per frame, not per ATT write: at a 20-byte limit a block
        is up to 61 writes.
        """
        await write_chunks(self.client, char, frame, size, step="write")
        if self.pacing_s:
            await asyncio.sleep(self.pacing_s)
