"""BLE writer and session management for easyTag protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient

from ..base import DevicePreset, Notifications, WriteResult, WriteTiming
from .const import (
    EVERY_5TH_BONUS,
    FEEDBACK_TIMEOUT,
    INTER_PACKET_DELAY,
    NOTIFY_UUID,
    POST_CCCD_DELAY,
    PRE_HEADER_DELAY,
    WRITE_UUID,
)
from .protocol import (
    build_image_frames,
    build_status_frames,
    encode_image,
    parse_notify,
    quantize_image,
)

if TYPE_CHECKING:
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


class EasyTagError(Exception):
    """easyTag device error."""


class EasyTagClient:
    """Client handling a single connected easyTag BLE session."""

    def __init__(self, client: BleakClient, preset: DevicePreset, address: str) -> None:
        self.client = client
        self.preset = preset
        self.address = address

    async def _send_frames(self, frames: list[bytes], *, pacing_s: float = 0.0) -> WriteResult:
        """Send header + data frames and read the battery/temperature reply."""
        settle = POST_CCCD_DELAY + PRE_HEADER_DELAY
        timing = WriteTiming(settle_s=settle, parts=len(frames), bytes=sum(map(len, frames)))
        with timing.reported():
            async with Notifications(self.client, NOTIFY_UUID, settle=settle) as replies:
                # Anything notified during the settle window is not our reply.
                replies.clear()
                base_delay = INTER_PACKET_DELAY + pacing_s
                # Send header (frame 0) and data frames (frames 1..N). The tag
                # does not acknowledge frames, so transfer_s is pacing only.
                with timing.stage("transfer_s"):
                    for idx, frame in enumerate(frames):
                        await self.client.write_gatt_char(WRITE_UUID, frame, response=False)
                        await asyncio.sleep(base_delay + (EVERY_5TH_BONUS if idx % 5 == 0 else 0))

                # The only acknowledgement is the status reply after the panel
                # has redrawn, so finish_s covers the refresh.
                with timing.stage("finish_s"):
                    reply = await replies.next(FEEDBACK_TIMEOUT, step="image frames")

            if not reply:
                raise EasyTagError("Empty notify payload from tag")
            parsed = parse_notify(self.address, reply)
        return WriteResult(
            success=True,
            battery_mv=parsed.get("battery_mv"),
            temperature_c=parsed.get("temperature_c"),
            timing=timing,
        )

    async def write_frames(
        self,
        frames: list[bytes],
        *,
        pacing_s: float = 0.0,
    ) -> WriteResult:
        """Transmit already-built image frames."""
        return await self._send_frames(frames, pacing_s=pacing_s)

    async def read_status(self) -> WriteResult:
        """Send status query ping frame (0xF0) and await battery/temp notify."""
        frames = build_status_frames(self.address)
        return await self._send_frames(frames)


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> list[bytes]:
    """Quantize (with dithering), encode and frame an image for `preset`.

    Pure-Python per-pixel work (seconds for the larger panels); callers run
    it in a worker thread so the event loop stays responsive.
    """
    dither = preset.extra.get("dither", True)
    plane_bw, plane_red = quantize_image(
        image, preset.width, preset.height, preset.colors, dither=dither
    )
    payload = encode_image(plane_bw, plane_red, preset.width, preset.height)
    return build_image_frames(address, payload)


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[list[bytes]],
    *,
    pacing_s: float = 0.0,
) -> WriteResult:
    """Send pre-built frames over an open link and read the battery/temperature reply."""
    frames = await prepared
    easytag = EasyTagClient(client, preset, address)
    return await easytag.write_frames(frames, pacing_s=pacing_s)
