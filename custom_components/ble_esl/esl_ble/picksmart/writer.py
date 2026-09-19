"""BLE writer and session management for PickSmart (gicisky) protocol."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from bleak import BleakClient

from ..base import DevicePreset, WriteResult
from .const import (
    CMD_IMAGE,
    CMD_SIZE,
    CMD_START,
    FEEDBACK_TIMEOUT,
    MAX_SAME_PART_REQUESTS,
    RESEND_BACKOFF_S,
    RESP_IMAGE_DATA,
    SERVICE_UUID_PREFIX,
)
from .protocol import (
    encode_image,
    make_cmd_packet,
    make_size_packet,
)

if TYPE_CHECKING:
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> bytes:
    """Encode an image to the PickSmart byte stream (CPU-bound; run in a thread)."""
    return encode_image(image, preset)


class PickSmartError(Exception):
    """PickSmart device error."""


class PickSmartClient:
    """Client handling PickSmart request-response BLE image transfer."""

    def __init__(
        self,
        client: BleakClient,
        cmd_uuid: str,
        img_uuid: str,
        preset: DevicePreset,
        address: str,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> None:
        self.client = client
        self.cmd_uuid = cmd_uuid
        self.img_uuid = img_uuid
        self.preset = preset
        self.address = address
        self.attempt = attempt
        self.write_delay_ms = write_delay_ms
        self._event = asyncio.Event()
        self._response_data: bytes | None = None

    def _notification_handler(self, _sender: Any, data: bytearray) -> None:
        self._response_data = bytes(data)
        self._event.set()

    async def _write_with_response(
        self,
        uuid: str,
        packet: bytes,
        step: str,
        timeout: float | None = None,
    ) -> bytes:
        if timeout is None:
            timeout = FEEDBACK_TIMEOUT
        self._response_data = None
        self._event.clear()

        delay = (self.write_delay_ms / 1000.0) + (0.05 * (self.attempt - 1))
        await self.client.write_gatt_char(uuid, packet, response=False)
        if delay > 0:
            await asyncio.sleep(delay)

        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except TimeoutError as exc:
            # asyncio's TimeoutError has an empty str(); say what was awaited.
            raise PickSmartError(
                f"No response from tag within {timeout:g}s after {step}"
            ) from exc
        if self._response_data is None:
            raise PickSmartError(f"Empty response from tag after {step}")
        return self._response_data

    async def write_image(self, image: Image.Image) -> WriteResult:
        """Encode (off the event loop) and run the transfer handshake.

        Convenience for direct use and the session tests; the integration goes
        through BleBackend.write_image(), which encodes off the loop once and
        overlaps it with connecting.
        """
        payload = await asyncio.to_thread(prepare, self.preset, image, self.address)
        return await self.write_payload(payload)

    async def write_payload(self, payload: bytes) -> WriteResult:
        """Execute 4-step image transfer handshake with an encoded payload."""
        compression2 = bool(self.preset.extra.get("compression2", False))
        packet_size = len(payload)

        await self.client.start_notify(
            self.cmd_uuid, self._notification_handler
        )
        try:
            await asyncio.sleep(1.0)  # settle time after start_notify (matches hass-gicisky)

            # Step 1: START (0x01) -> [01 F4 00]
            start_resp = await self._write_with_response(
                self.cmd_uuid,
                make_cmd_packet(CMD_START, packet_size, compression2),
                "START",
            )
            if (
                len(start_resp) < 3
                or start_resp[0] != 0x01
                or start_resp[1] != 0xF4
                or start_resp[2] != 0x00
            ):
                raise PickSmartError(f"Unexpected start response: {start_resp.hex()}")

            # Step 2: SIZE_DATA (0x02) -> [02]
            size_resp = await self._write_with_response(
                self.cmd_uuid,
                make_cmd_packet(CMD_SIZE, packet_size, compression2),
                "SIZE",
            )
            if len(size_resp) < 1 or size_resp[0] != 0x02:
                raise PickSmartError(f"Unexpected size response: {size_resp.hex()}")

            # Step 3: IMAGE START (0x03) -> [05 00 ... part]
            img_start_resp = await self._write_with_response(
                self.cmd_uuid,
                make_cmd_packet(CMD_IMAGE, packet_size, compression2),
                "IMAGE START",
            )
            if (
                len(img_start_resp) < 6
                or img_start_resp[0] != RESP_IMAGE_DATA
                or img_start_resp[1] != 0x00
            ):
                raise PickSmartError(
                    f"Unexpected image start response: {img_start_resp.hex()}"
                )

            # Step 4: IMAGE_DATA chunk loop. The tag drives the transfer by
            # answering each chunk with the part it wants next; asking for the
            # same part again is its way of requesting a resend.
            part = int.from_bytes(img_start_resp[2:6], "little")
            last_part = -1
            same_part_count = 0
            total_parts = (packet_size + 239) // 240

            while part * 240 < packet_size:
                data_packet = make_size_packet(part, payload)
                resp = await self._write_with_response(
                    self.img_uuid, data_packet, f"part {part}/{total_parts}"
                )

                if (
                    len(resp) < 6
                    or resp[0] != RESP_IMAGE_DATA
                    or resp[1] != 0x00
                ):
                    # Not a "send me part N" frame. Only known to be fine when
                    # the chunk just sent was the last one; before that the
                    # image is incomplete whatever the frame means.
                    if (part + 1) * 240 < packet_size:
                        raise PickSmartError(
                            f"Tag ended transfer after part {part}/{total_parts} "
                            f"with {resp.hex()}"
                        )
                    _LOGGER.debug(
                        "%s: transfer ended by tag after last part %d/%d with %s",
                        self.address,
                        part,
                        total_parts,
                        resp.hex(),
                    )
                    break

                new_part = int.from_bytes(resp[2:6], "little")
                if new_part == last_part:
                    same_part_count += 1
                    if same_part_count >= MAX_SAME_PART_REQUESTS:
                        raise PickSmartError(
                            f"Transfer stalled: part {new_part}/{total_parts} "
                            f"requested {same_part_count} times"
                        )
                    _LOGGER.debug(
                        "%s: tag re-requested part %d/%d (%d/%d), resending",
                        self.address,
                        new_part,
                        total_parts,
                        same_part_count,
                        MAX_SAME_PART_REQUESTS,
                    )
                    # Back off a little before resending; a tag that is still
                    # committing the previous chunk tends to reject a resend
                    # sent straight away, which is what hits the stall limit.
                    await asyncio.sleep(RESEND_BACKOFF_S * (same_part_count - 1))
                else:
                    same_part_count = 1
                    last_part = new_part

                part = new_part

            return WriteResult(success=True)
        finally:
            with contextlib.suppress(Exception):
                if self.client and self.client.is_connected:
                    await self.client.stop_notify(self.cmd_uuid)


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[bytes],
    *,
    attempt: int = 1,
    write_delay_ms: int = 0,
) -> WriteResult:
    """Resolve the command/image characteristics and run the transfer handshake."""
    char_uuids = [
        c.uuid
        for svc in client.services
        if svc.uuid.lower().startswith(SERVICE_UUID_PREFIX)
        for c in svc.characteristics
    ]
    if len(char_uuids) < 2:
        return WriteResult(success=False, error=f"Insufficient characteristics: {char_uuids}")
    cmd_uuid, img_uuid = sorted(char_uuids, key=lambda x: int(x[4:8], 16))[:2]

    picksmart = PickSmartClient(
        client, cmd_uuid, img_uuid, preset, address,
        attempt=attempt, write_delay_ms=write_delay_ms,
    )
    return await picksmart.write_payload(await prepared)
