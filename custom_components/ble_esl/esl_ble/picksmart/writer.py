"""BLE writer and session management for PickSmart (gicisky) protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
import time
from typing import TYPE_CHECKING

from bleak import BleakClient

from ..base import DevicePreset, Notifications, NotificationTimeout, WriteResult
from .const import (
    CMD_IMAGE,
    CMD_SIZE,
    CMD_START,
    FEEDBACK_TIMEOUT,
    MAX_SAME_PART_REQUESTS,
    NOTIFY_SETTLE_S,
    RESEND_BACKOFF_S,
    RESP_IMAGE_DATA,
    RESP_STATUS_COMPLETE,
    RESP_STATUS_NEXT_PART,
    SERVICE_UUID_PREFIX,
    START_PROBE_ATTEMPTS,
    START_PROBE_TIMEOUT_S,
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
        self._replies: Notifications | None = None

    async def _write_with_response(
        self,
        uuid: str,
        packet: bytes,
        step: str,
        timeout: float | None = None,
    ) -> bytes:
        assert self._replies is not None, "inside write_payload()'s notification session"
        self._replies.clear()
        delay = (self.write_delay_ms / 1000.0) + (0.05 * (self.attempt - 1))
        await self.client.write_gatt_char(uuid, packet, response=False)
        if delay > 0:
            await asyncio.sleep(delay)
        return await self._replies.next(FEEDBACK_TIMEOUT if timeout is None else timeout, step=step)

    async def write_payload(self, payload: bytes) -> WriteResult:
        """Execute 4-step image transfer handshake with an encoded payload."""
        compression2 = bool(self.preset.extra.get("compression2", False))
        timing: dict[str, float | int | bool] = {"settle_s": NOTIFY_SETTLE_S}
        try:
            return await self._transfer(payload, compression2, timing)
        except Exception as exc:
            # Let the caller report how far the attempt got (see write_prepared).
            exc.timing = timing  # type: ignore[attr-defined]
            raise

    async def _transfer(
        self, payload: bytes, compression2: bool, timing: dict[str, float | int | bool]
    ) -> WriteResult:
        packet_size = len(payload)
        t0 = time.monotonic()
        async with Notifications(self.client, self.cmd_uuid, settle=NOTIFY_SETTLE_S) as replies:
            self._replies = replies
            # Step 1: START (0x01) -> [01 F4 00], probed (see const.py).
            start_packet = make_cmd_packet(CMD_START, packet_size, compression2)
            for probe in range(1, START_PROBE_ATTEMPTS + 1):
                timing["start_probes"] = probe
                try:
                    start_resp = await self._write_with_response(
                        self.cmd_uuid, start_packet, "START", timeout=START_PROBE_TIMEOUT_S
                    )
                    break
                except NotificationTimeout:
                    if probe == START_PROBE_ATTEMPTS:
                        raise NotificationTimeout(
                            f"No response from tag to START after {probe} probes "
                            f"({START_PROBE_TIMEOUT_S:g}s each)"
                        ) from None
                    _LOGGER.debug(
                        "%s: START unanswered (%d/%d), resending",
                        self.address,
                        probe,
                        START_PROBE_ATTEMPTS,
                    )
            timing["start_s"] = round(time.monotonic() - t0 - NOTIFY_SETTLE_S, 3)
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
                or img_start_resp[1] != RESP_STATUS_NEXT_PART
            ):
                raise PickSmartError(f"Unexpected image start response: {img_start_resp.hex()}")

            # Step 4: IMAGE_DATA chunk loop. The tag drives the transfer by
            # answering each chunk with the part it wants next; asking for the
            # same part again is its way of requesting a resend.
            part = int.from_bytes(img_start_resp[2:6], "little")
            last_part = -1
            same_part_count = 0
            total_parts = (packet_size + 239) // 240
            sends = resends = 0
            completed_by_tag = False
            transfer_started = time.monotonic()

            while part * 240 < packet_size:
                sends += 1
                data_packet = make_size_packet(part, payload)
                resp = await self._write_with_response(
                    self.img_uuid, data_packet, f"part {part}/{total_parts}"
                )

                if (
                    len(resp) >= 2
                    and resp[0] == RESP_IMAGE_DATA
                    and resp[1] == RESP_STATUS_COMPLETE
                ):
                    # The tag confirms it has everything (seen after the last
                    # part on every tag tested); anything earlier is a short
                    # transfer whatever the tag thinks.
                    if (part + 1) * 240 < packet_size:
                        raise PickSmartError(
                            f"Tag reported completion after part {part}/{total_parts}"
                        )
                    completed_by_tag = True
                    break
                if len(resp) < 6 or resp[0] != RESP_IMAGE_DATA or resp[1] != RESP_STATUS_NEXT_PART:
                    raise PickSmartError(
                        f"Unexpected reply after part {part}/{total_parts}: {resp.hex()}"
                    )

                new_part = int.from_bytes(resp[2:6], "little")
                if new_part == last_part:
                    same_part_count += 1
                    resends += 1
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

            transfer_s = time.monotonic() - transfer_started
            timing.update(
                {
                    "parts": total_parts,
                    "sends": sends,  # parts + resends; round_trip_ms * sends ~= transfer_s
                    "resends": resends,
                    "transfer_s": round(transfer_s, 3),
                    "round_trip_ms": round(transfer_s / sends * 1000) if sends else 0,
                    "completed_by_tag": completed_by_tag,
                }
            )
            return WriteResult(success=True, timing=timing)


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
        client,
        cmd_uuid,
        img_uuid,
        preset,
        address,
        attempt=attempt,
        write_delay_ms=write_delay_ms,
    )
    return await picksmart.write_payload(await prepared)
