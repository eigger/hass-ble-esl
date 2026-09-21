"""BLE writer and session management for WOLINK protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient
from blesession import Notifications, SessionTrace
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..base import STAGE_FINISH, STAGE_HANDSHAKE, STAGE_TRANSFER, DevicePreset, WriteResult
from .const import (
    AES_KEY,
    AUTH_CHAR,
    BATTERY_CHAR,
    CHUNK_DELAY_S,
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
    from PIL import Image

_LOGGER = logging.getLogger(__name__)

# (compressed payload, uncompressed length) — the latter picks the refresh timeout.
PreparedImage = tuple[bytes, int]


class WolinkError(Exception):
    """WOLINK device error."""

    def __init__(self, code: int) -> None:
        self.code = code
        msg = ERROR_MESSAGES.get(code, "unknown")
        super().__init__(f"device error {code}: {msg}")


class WolinkClient:
    """Client handling a single connected WOLINK BLE session."""

    def __init__(self, client: BleakClient, preset: DevicePreset, address: str) -> None:
        self.client = client
        self.preset = preset
        self.address = address

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

    @staticmethod
    def _completion_timeout(raw_len: int) -> float:
        """How long the panel may take to refresh after the upload, by image size."""
        if raw_len > 100000:
            return 120.0
        if raw_len > 20000:
            return 60.0
        return 30.0

    @staticmethod
    def _status_error(data: bytes) -> int:
        """Error code carried by a status frame (byte 1), 0 if none."""
        return data[1] if len(data) >= 2 else 0

    def _completed(self, data: bytes) -> bool:
        """Accept a status frame after the refresh: error -> raise, idle -> done."""
        if err := self._status_error(data):
            raise WolinkError(err)
        return bool(data) and data[0] in (0x00, 0xFF)

    async def _write_chunked(
        self,
        payload: bytes,
        trace: SessionTrace,
        chunk_size: int = 200,
        pacing_s: float = 0.0,
    ) -> None:
        """Write compressed image payload in chunks, `pacing_s` slower than usual.

        `parts` is the chunk count of the image; `sends` counts the chunks
        written so far, so a failure mid-transfer still says how far it got.
        """
        delay = CHUNK_DELAY_S + pacing_s
        offset = 0
        sends = 0
        trace.note(parts=(len(payload) + chunk_size - 1) // chunk_size, sends=sends)
        try:
            while offset < len(payload):
                chunk = payload[offset : offset + chunk_size]
                cmd = cmd_load_image_chunk(offset, chunk)
                await self.client.write_gatt_char(DATA_CHAR, cmd, response=True)
                offset += len(chunk)
                sends += 1
                await asyncio.sleep(delay)
        finally:
            trace.note(sends=sends)

    async def write_prepared(
        self,
        prepared: PreparedImage,
        *,
        pacing_s: float = 0.0,
        trace: SessionTrace | None = None,
    ) -> WriteResult:
        """Send an already-encoded image and trigger the refresh.

        `trace` carries the stages before this one (authentication) when the
        caller timed them (see write_session).
        """
        payload, raw_len = prepared
        refresh = cmd_refresh_compressed(len(payload))

        if raw_len > 100000:
            est_seconds = int((len(payload) / 200) * (CHUNK_DELAY_S + pacing_s))
            _LOGGER.info(
                "Sending large image (%d bytes, %d chunks) to %s — estimated transfer time: ~%ds",
                raw_len,
                (len(payload) + 199) // 200,
                self.address,
                est_seconds,
            )
        timeout = self._completion_timeout(raw_len)
        if trace is None:
            trace = SessionTrace()
        trace.note(bytes=len(payload))

        async with Notifications(self.client, STATUS_CHAR) as status:
            with trace.timed(STAGE_TRANSFER):
                await self._write_chunked(payload, trace, pacing_s=pacing_s)
                # Status frames during the upload are only busy indications,
                # but an error reported before the refresh is still an error
                # — of the transfer, so it is raised inside its stage: the
                # trace attributes a failure to the block it escapes from.
                for frame in status.clear():
                    if err := self._status_error(frame):
                        raise WolinkError(err)
            # The finish stage is the panel refresh: the tag reports idle once
            # the e-paper has been redrawn, seconds to a minute by panel size.
            with trace.timed(STAGE_FINISH):
                await self.client.write_gatt_char(DATA_CHAR, refresh, response=True)
                await status.wait_for(self._completed, timeout, step="refresh")
        return WriteResult(success=True)


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> PreparedImage:
    """Quantize, pack and compress an image for `preset`.

    Pure-Python per-pixel work (seconds for the larger panels); callers run
    it in a worker thread so the event loop stays responsive.
    """
    plane_bw, plane_red, plane_yellow = quantize_image(
        image, preset.width, preset.height, preset.colors
    )
    raw = encode_planes(plane_bw, plane_red, plane_yellow, preset)
    return compress_wolink_blocks(raw), len(raw)


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[PreparedImage],
    *,
    pacing_s: float = 0.0,
    trace: SessionTrace,
) -> WriteResult:
    """Authenticate and send an encode over an open link.

    `prepared` is awaited once the link is up (the caller owns it and may
    await it again on a retry); authentication must precede any other write.
    """
    payload = await prepared
    wolink = WolinkClient(client, preset, address)
    with trace.timed(STAGE_HANDSHAKE):
        await wolink.authenticate()
    return await wolink.write_prepared(payload, pacing_s=pacing_s, trace=trace)
