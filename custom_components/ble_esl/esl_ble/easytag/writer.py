"""BLE writer and session management for easyTag protocol."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from bleak import BleakClient
from bleak_retry_connector import establish_connection

from ..base import DevicePreset, WriteResult
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
    from bleak.backends.device import BLEDevice
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


class EasyTagClient:
    """Client handling a single connected easyTag BLE session."""

    def __init__(
        self, client: BleakClient, preset: DevicePreset, address: str
    ) -> None:
        self.client = client
        self.preset = preset
        self.address = address
        self._notify_event: asyncio.Event | None = None
        self._notify_data: bytearray | None = None

    def _handle_notify(self, _sender: Any, data: bytearray) -> None:
        """Handle incoming notify frame from device."""
        self._notify_data = data
        if self._notify_event:
            self._notify_event.set()

    @contextlib.asynccontextmanager
    async def _notify_session(self):
        """Subscribe to notifications before writing any command frames."""
        self._notify_event = asyncio.Event()
        self._notify_data = None
        await self.client.start_notify(NOTIFY_UUID, self._handle_notify)
        try:
            yield
        finally:
            with contextlib.suppress(Exception):
                if self.client and self.client.is_connected:
                    await self.client.stop_notify(NOTIFY_UUID)

    async def _send_frames(
        self, frames: list[bytes], *, attempt: int = 1, write_delay_ms: int = 0
    ) -> WriteResult:
        """Send header + data frames and await notify response."""
        async with self._notify_session():
            await asyncio.sleep(POST_CCCD_DELAY + PRE_HEADER_DELAY)

            base_delay = (
                INTER_PACKET_DELAY
                + (write_delay_ms / 1000.0)
                + (0.05 * (attempt - 1))
            )

            # Send header (frame 0) and data frames (frames 1..N)
            for idx, frame in enumerate(frames):
                await self.client.write_gatt_char(
                    WRITE_UUID, frame, response=False
                )
                delay = base_delay + (EVERY_5TH_BONUS if (idx % 5 == 0) else 0)
                await asyncio.sleep(delay)

            # Await feedback notification
            try:
                assert self._notify_event is not None
                await asyncio.wait_for(
                    self._notify_event.wait(), timeout=FEEDBACK_TIMEOUT
                )
            except asyncio.TimeoutError:
                _LOGGER.warning(
                    "Timed out waiting for easyTag notify response from %s",
                    self.address,
                )
                return WriteResult(
                    success=False, error="timeout waiting for notify"
                )

            if not self._notify_data:
                return WriteResult(success=False, error="empty notify payload")

            parsed = parse_notify(self.address, bytes(self._notify_data))
            return WriteResult(
                success=True,
                battery_mv=parsed.get("battery_mv"),
                temperature_c=parsed.get("temperature_c"),
            )

    async def write_image(
        self,
        image: Image.Image,
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Encode (off the event loop) and transmit image frames."""
        frames = await asyncio.to_thread(
            prepare_frames, image, self.preset, self.address
        )
        return await self.write_frames(
            frames, attempt=attempt, write_delay_ms=write_delay_ms
        )

    async def write_frames(
        self,
        frames: list[bytes],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Transmit already-built image frames."""
        return await self._send_frames(
            frames, attempt=attempt, write_delay_ms=write_delay_ms
        )

    async def read_status(self) -> WriteResult:
        """Send status query ping frame (0xF0) and await battery/temp notify."""
        frames = build_status_frames(self.address)
        return await self._send_frames(frames)


def prepare_frames(
    image: Image.Image, preset: DevicePreset, address: str
) -> list[bytes]:
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


async def update_image(
    ble_device: BLEDevice,
    preset: DevicePreset,
    image: Image.Image,
    *,
    attempt: int = 1,
    write_delay_ms: int = 0,
) -> WriteResult:
    """Encode (worker thread, overlapping the connect) and write an image."""
    encode = asyncio.create_task(
        asyncio.to_thread(prepare_frames, image, preset, ble_device.address)
    )
    try:
        return await update_prepared(
            ble_device, preset, encode, attempt=attempt, write_delay_ms=write_delay_ms
        )
    finally:
        encode.cancel()  # no-op once awaited; drops the result if connect failed


async def update_prepared(
    ble_device: BLEDevice,
    preset: DevicePreset,
    prepared: Awaitable[list[bytes]],
    *,
    attempt: int = 1,
    write_delay_ms: int = 0,
) -> WriteResult:
    """Connect and send an already-scheduled encode to the tag.

    `prepared` is awaited only once the link is up, so the encode (started by
    the caller in a worker thread) overlaps connecting; the caller owns it and
    may await it again on a retry.
    """
    # Connect inside the try so connection failures surface as a failed
    # WriteResult (and count toward retries) instead of escaping as raw exceptions.
    client: BleakClient | None = None
    try:
        client = await establish_connection(
            BleakClient, ble_device, ble_device.address
        )
        frames = await prepared
        easytag = EasyTagClient(client, preset, ble_device.address)
        return await easytag.write_frames(
            frames, attempt=attempt, write_delay_ms=write_delay_ms
        )
    except Exception as exc:
        # The caller logs each failed attempt and raises after the last one;
        # keep the traceback available at debug level without a second ERROR.
        _LOGGER.debug("Write to %s failed", ble_device.address, exc_info=exc)
        return WriteResult(success=False, error=str(exc) or type(exc).__name__)
    finally:
        with contextlib.suppress(Exception):
            if client and client.is_connected:
                await client.disconnect()
