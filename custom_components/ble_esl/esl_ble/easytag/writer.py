"""easyTag write session: send the frames, then read the reply once the panel redraws."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TYPE_CHECKING

from blesession import Notifications, SessionTrace

from ..base import STAGE_FINISH, STAGE_TRANSFER, DevicePreset, WriteResult
from .const import (
    EVERY_FIFTH_EXTRA_S,
    NOTIFY_SETTLE_S,
    NOTIFY_UUID,
    PACKET_GAP_S,
    PRE_HEADER_S,
    REPLY_TIMEOUT_S,
    WRITE_UUID,
)
from .image import encode_image
from .protocol import image_frames, parse_reply

if TYPE_CHECKING:
    from bleak import BleakClient
    from PIL import Image


class EasyTagError(Exception):
    """The tag's reply was unusable."""


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> list[bytes]:
    """Encode `image` and frame it for the tag at `address`; CPU-bound (worker thread)."""
    return image_frames(address, encode_image(image, preset))


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[list[bytes]],
    *,
    pacing_s: float = 0.0,
    trace: SessionTrace,
) -> WriteResult:
    """Send the frames once the link is up; the reply carries battery and temperature."""
    frames = await prepared
    return await EasyTagSession(client, address, pacing_s=pacing_s).send(frames, trace=trace)


class EasyTagSession:
    """One connected easyTag tag."""

    def __init__(self, client: BleakClient, address: str, *, pacing_s: float = 0.0) -> None:
        self.client = client
        self.address = address
        self.pacing_s = max(0.0, pacing_s)

    async def send(
        self,
        frames: list[bytes],
        *,
        pacing_s: float | None = None,
        trace: SessionTrace | None = None,
    ) -> WriteResult:
        """Write every frame unacknowledged, then wait for the tag's single reply."""
        pacing = self.pacing_s if pacing_s is None else max(0.0, pacing_s)
        if trace is None:
            trace = SessionTrace()
        settle = NOTIFY_SETTLE_S + PRE_HEADER_S
        trace.note(settle_s=settle, parts=len(frames), bytes=sum(map(len, frames)))
        async with Notifications(self.client, NOTIFY_UUID, settle=settle) as replies:
            replies.clear()  # anything before the header is not our reply
            with trace.timed(STAGE_TRANSFER):
                for index, frame in enumerate(frames):
                    await self.client.write_gatt_char(WRITE_UUID, frame, response=False)
                    extra = EVERY_FIFTH_EXTRA_S if index % 5 == 0 else 0.0
                    await asyncio.sleep(PACKET_GAP_S + pacing + extra)
            with trace.timed(STAGE_FINISH):
                frame = await replies.next(REPLY_TIMEOUT_S, step="image frames")
                if not frame:
                    raise EasyTagError("Empty notify payload from tag")
        reply = parse_reply(self.address, frame)
        return WriteResult(
            success=True,
            battery_mv=None if reply is None else reply.battery_mv,
            temperature_c=None if reply is None else reply.temperature_c,
        )
