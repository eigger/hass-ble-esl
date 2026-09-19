"""BLE writer and session management for PickSmart (gicisky) protocol."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from bleak import BleakClient
from bleak_retry_connector import establish_connection

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
    from bleak.backends.device import BLEDevice
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


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
        """Encode (off the event loop) and run the transfer handshake."""
        payload = await asyncio.to_thread(encode_image, image, self.preset)
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
                    _LOGGER.debug(
                        "%s: transfer ended by tag after part %d/%d with %s",
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


async def update_image(
    ble_device: BLEDevice,
    preset: DevicePreset,
    image: Image.Image,
    *,
    attempt: int = 1,
    write_delay_ms: int = 0,
) -> WriteResult:
    """Connect, resolve characteristics, and write image to PickSmart ESL."""
    # Connect inside the try so connection failures surface as a failed
    # WriteResult (and count toward retries) instead of escaping as raw exceptions.
    client: BleakClient | None = None
    # Encode in a worker thread while the connection is being established:
    # the event loop stays free, the radio starts immediately (sleepy tags
    # have short advertising windows), and the link is held only for
    # whatever part of the encode outlasts the connect.
    encode = asyncio.create_task(asyncio.to_thread(encode_image, image, preset))
    try:
        client = await establish_connection(
            BleakClient, ble_device, ble_device.address
        )
        char_uuids = [
            c.uuid
            for svc in client.services
            if svc.uuid.lower().startswith(SERVICE_UUID_PREFIX)
            for c in svc.characteristics
        ]
        if len(char_uuids) < 2:
            return WriteResult(
                success=False, error=f"Insufficient characteristics: {char_uuids}"
            )

        sorted_uuids = sorted(char_uuids, key=lambda x: int(x[4:8], 16))
        cmd_uuid, img_uuid = sorted_uuids[0], sorted_uuids[1]

        picksmart = PickSmartClient(
            client,
            cmd_uuid,
            img_uuid,
            preset,
            ble_device.address,
            attempt=attempt,
            write_delay_ms=write_delay_ms,
        )
        return await picksmart.write_payload(await encode)
    except Exception as exc:
        # The caller logs each failed attempt and raises after the last one;
        # keep the traceback available at debug level without a second ERROR.
        _LOGGER.debug("Write to %s failed", ble_device.address, exc_info=exc)
        return WriteResult(success=False, error=str(exc) or type(exc).__name__)
    finally:
        encode.cancel()  # no-op once awaited; drops the result if connect failed
        with contextlib.suppress(Exception):
            if client and client.is_connected:
                await client.disconnect()
