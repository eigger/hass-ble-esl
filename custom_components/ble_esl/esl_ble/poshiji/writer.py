"""Poshiji XTE BLE session and image writer."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from PIL import Image
from ..base import WriteResult
from .const import SERVICE_UUID, WRITE_UUID, NOTIFY_UUID
from .protocol import make_image_object, pack_pixels, make_blocks, make_command

_LOGGER = logging.getLogger(__name__)

class XteClient:
    """Send the observed transaction, requiring both application responses."""

    def __init__(self, client, attempt: int = 1, write_delay_ms: int = 0):
        self.client = client
        self.delay = max(0, write_delay_ms) / 1000 + 0.05 * max(0, attempt - 1)
        self.responses: asyncio.Queue[bytes] = asyncio.Queue()
        self.timeout = 5.0

    def _notification(self, _sender, data: bytearray) -> None:
        self.responses.put_nowait(bytes(data))

    async def _write(self, characteristic, data: bytes, chunk_size: int) -> None:
        for offset in range(0, len(data), chunk_size):
            await self.client.write_gatt_char(
                characteristic, data[offset:offset + chunk_size], response=False
            )
            if self.delay:
                await asyncio.sleep(self.delay)

    async def _command(self, characteristic, payload: bytes, chunk_size: int,
                       expected_payload: bytes) -> None:
        while not self.responses.empty():
            self.responses.get_nowait()
        await self._write(characteristic, make_command(payload), chunk_size)
        async with asyncio.timeout(self.timeout):
            while True:
                response = await self.responses.get()
                if not response.startswith(b"XTE\x04"):
                    continue
                if len(response) < 6:
                    raise ValueError("Truncated XTE response")
                length = response[4]
                if length < 7 or length > len(response):
                    raise ValueError("Invalid XTE response length")
                body = response[6:length]
                if sum(body) & 0xFF != response[5]:
                    raise ValueError("Invalid XTE response checksum")
                # Only the captured positive responses are currently known.
                # Never treat an arbitrary notification as transfer success.
                if body != expected_payload:
                    raise ValueError(f"Unexpected XTE response: {body.hex()}")
                return

    async def write_image(self, image: Image.Image) -> bool:
        service = self.client.services.get_service(SERVICE_UUID)
        if service is None:
            raise ValueError("XTE service missing")
        write_char = service.get_characteristic(WRITE_UUID)
        notify_char = service.get_characteristic(NOTIFY_UUID)
        if write_char is None or notify_char is None:
            raise ValueError("XTE characteristics missing")
        if "write-without-response" not in write_char.properties or "notify" not in notify_char.properties:
            raise ValueError("XTE characteristic properties do not match")
        chunk_size = min(244, write_char.max_write_without_response_size)
        # 244 is the captured upper bound, not a minimum ATT payload. Preserve
        # each XTE block and its checksum while splitting its byte stream to
        # fit the backend's advertised write limit (often 20 on some backends).
        if chunk_size < 20:
            raise ValueError(f"Invalid XTE write-without-response size: {chunk_size}")
        _LOGGER.debug("XTE write chunk size: %s bytes", chunk_size)
        image_object = await asyncio.to_thread(lambda: make_image_object(pack_pixels(image)))
        blocks = make_blocks(image_object)
        await self.client.start_notify(notify_char, self._notification)
        try:
            await self._command(write_char, b"\x01" + len(image_object).to_bytes(4, "big"),
                                chunk_size, bytes.fromhex("01ffbd"))
            for block in blocks:
                await self._write(write_char, block, chunk_size)
            await self._command(write_char, b"\x04\x00", chunk_size, bytes.fromhex("04ff"))
            return True
        finally:
            # Disconnect in update_image is still attempted if unsubscribe fails.
            await self.client.stop_notify(notify_char)


async def update_image(ble_device, preset, image, *, attempt=1, write_delay_ms=0) -> WriteResult:
    """Connect and send a PSJ-420 image, preserving errors for HA diagnostics."""
    if (preset.key, preset.width, preset.height, preset.colors) != ("psj-420", 400, 300, "BWRY"):
        return WriteResult(success=False, error="Unsupported Poshiji preset")
    client = None
    try:
        client = await establish_connection(BleakClient, ble_device, ble_device.address)
        success = await XteClient(client, attempt, write_delay_ms).write_image(image)
        return WriteResult(success=success)
    except Exception as exc:
        error = str(exc) or type(exc).__name__
        _LOGGER.error("Poshiji update failed for %s: %s", ble_device.address, error)
        return WriteResult(success=False, error=error)
    finally:
        if client and client.is_connected:
            with contextlib.suppress(Exception):
                await client.disconnect()
