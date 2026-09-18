"""BLE writer and session management for WOLINK protocol."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..base import DevicePreset, WriteResult
from .const import (
    AES_KEY,
    AUTH_CHAR,
    BATTERY_CHAR,
    DATA_CHAR,
    ERROR_MESSAGES,
    STATUS_CHAR,
)
from .protocol import (
    battery_looks_plausible,
    cmd_load_image_chunk,
    cmd_refresh_compressed,
    compress_wolink_blocks,
    encode_planes,
    quantize_image,
)

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


class WolinkError(Exception):
    """WOLINK device error."""

    def __init__(self, code: int) -> None:
        self.code = code
        msg = ERROR_MESSAGES.get(code, "unknown")
        super().__init__(f"device error {code}: {msg}")


class WolinkClient:
    """Client handling a single connected WOLINK BLE session."""

    def __init__(
        self, client: BleakClient, preset: DevicePreset, address: str
    ) -> None:
        self.client = client
        self.preset = preset
        self.address = address
        self.last_error_code = 0
        self._status_event: asyncio.Event | None = None
        self._armed = False

    async def authenticate(self) -> None:
        """Perform AES-128 ECB challenge-response authentication.

        Note: Writing to other characteristics/descriptors before unlocking triggers
        immediate disconnect on official firmware. Therefore, authentication must be
        performed directly on AUTH_CHAR prior to opening status notifications.
        """
        nonce = await self.client.read_gatt_char(AUTH_CHAR)
        cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(bytes(nonce)) + encryptor.finalize()
        await self.client.write_gatt_char(AUTH_CHAR, encrypted, response=True)
        await asyncio.sleep(0.5)
        if not self.client.is_connected:
            raise WolinkError(5)  # Documented auth failure = immediate disconnect

    async def read_battery_mv(self) -> int | None:
        """Diagnostic read of battery GATT characteristic.

        Note: WOLINK battery is passively provided via 0xBBAA broadcast advertisement.
        This GATT characteristic is not used during standard write sessions.
        """
        try:
            raw = await self.client.read_gatt_char(BATTERY_CHAR)
            if not raw or len(raw) < 2:
                return None
            millivolts = (raw[0] << 8) | raw[1]
            if not battery_looks_plausible(millivolts):
                _LOGGER.warning(
                    "GATT Battery read %d mV is out of plausible range (raw %s)",
                    millivolts,
                    bytes(raw)[:2].hex(),
                )
            return millivolts
        except Exception as exc:
            _LOGGER.debug("Could not read GATT battery: %s", exc)
            return None

    def _handle_status(self, _sender: Any, data: bytearray) -> None:
        """Handle status notification frame (byte 0: BUSY, byte 1: ERR)."""
        if not data:
            return
        busy = data[0]
        err = data[1] if len(data) >= 2 else 0

        if err:
            self.last_error_code = err
            if self._status_event:
                self._status_event.set()
            return

        if not self._armed:
            _LOGGER.debug("Status frame before arming: %s", bytes(data).hex())
            return

        if busy in (0x00, 0xFF):
            self.last_error_code = 0
            if self._status_event:
                self._status_event.set()

    @contextlib.asynccontextmanager
    async def _status_session(self):
        """Subscribe to status notifications before sending image/refresh commands."""
        self._status_event = asyncio.Event()
        self._armed = False
        self.last_error_code = 0
        await self.client.start_notify(STATUS_CHAR, self._handle_status)
        try:
            yield
        finally:
            self._armed = False
            with contextlib.suppress(Exception):
                if self.client and self.client.is_connected:
                    await self.client.stop_notify(STATUS_CHAR)

    def _arm_completion(self) -> None:
        """Arm completion notification check."""
        self._armed = True

    async def _wait_for_completion(self, timeout: float) -> bool:
        """Wait for completion event."""
        if self._status_event is None:
            raise RuntimeError("_wait_for_completion outside a _status_session")
        try:
            await asyncio.wait_for(self._status_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            _LOGGER.warning("Timed out waiting for device notification")
            return False

        if self.last_error_code:
            raise WolinkError(self.last_error_code)
        return True

    async def _write_chunked(
        self,
        payload: bytes,
        chunk_size: int = 200,
        write_delay_ms: int = 0,
        attempt: int = 1,
    ) -> None:
        """Write compressed image payload in chunks with cumulative delay and retry backoff."""
        delay = 0.03 + (write_delay_ms / 1000.0) + (0.05 * (attempt - 1))
        offset = 0
        while offset < len(payload):
            chunk = payload[offset : offset + chunk_size]
            cmd = cmd_load_image_chunk(offset, chunk)
            await self.client.write_gatt_char(DATA_CHAR, cmd, response=True)
            offset += len(chunk)
            await asyncio.sleep(delay)

    async def write_image(
        self,
        image: Image.Image,
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Encode, compress, send, and refresh an image."""
        plane_bw, plane_red, plane_yellow = quantize_image(
            image, self.preset.width, self.preset.height, self.preset.colors
        )
        raw = encode_planes(plane_bw, plane_red, plane_yellow, self.preset)
        payload = compress_wolink_blocks(raw)
        refresh = cmd_refresh_compressed(len(payload))

        if len(raw) > 100000:
            est_seconds = int(
                (len(payload) / 200)
                * (0.03 + (write_delay_ms / 1000.0) + (0.05 * (attempt - 1)))
            )
            _LOGGER.info(
                "Sending large image (%d bytes, %d chunks) to %s — estimated transfer time: ~%ds",
                len(raw),
                (len(payload) + 199) // 200,
                self.address,
                est_seconds,
            )
            timeout = 120.0
        elif len(raw) > 20000:
            timeout = 60.0
        else:
            timeout = 30.0

        async with self._status_session():
            await self._write_chunked(
                payload, write_delay_ms=write_delay_ms, attempt=attempt
            )
            self._arm_completion()
            await self.client.write_gatt_char(DATA_CHAR, refresh, response=True)
            success = await self._wait_for_completion(timeout)

        return WriteResult(success=success)


async def update_image(
    ble_device: BLEDevice,
    preset: DevicePreset,
    image: Image.Image,
    *,
    attempt: int = 1,
    write_delay_ms: int = 0,
) -> WriteResult:
    """Connect, authenticate, and write image to a WOLINK ESL device."""
    client: BleakClient = await establish_connection(
        BleakClient, ble_device, ble_device.address
    )
    try:
        wolink = WolinkClient(client, preset, ble_device.address)
        await wolink.authenticate()
        return await wolink.write_image(
            image, attempt=attempt, write_delay_ms=write_delay_ms
        )
    except Exception as exc:
        _LOGGER.error("Failed to write to %s: %s", ble_device.address, exc)
        return WriteResult(success=False, error=str(exc))
    finally:
        with contextlib.suppress(Exception):
            if client and client.is_connected:
                await client.disconnect()
