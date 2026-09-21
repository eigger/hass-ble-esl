"""BLE writer and session management for PickSmart (gicisky) protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient

from ..base import (
    DevicePreset,
    Notifications,
    NotificationTimeout,
    WriteResult,
    WriteTiming,
)
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
        pacing_s: float = 0.0,
    ) -> None:
        self.client = client
        self.cmd_uuid = cmd_uuid
        self.img_uuid = img_uuid
        self.preset = preset
        self.address = address
        self.pacing_s = pacing_s
        self._replies: Notifications | None = None

    async def _write_with_response(
        self,
        uuid: str,
        packet: bytes,
        step: str,
        timeout: float | None = None,
        pace: bool = False,
    ) -> bytes:
        """Write `packet` and return the tag's reply; `pace` adds the retry pacing."""
        assert self._replies is not None, "inside write_payload()'s notification session"
        self._replies.clear()
        await self.client.write_gatt_char(uuid, packet, response=False)
        if pace and self.pacing_s > 0:
            await asyncio.sleep(self.pacing_s)
        return await self._replies.next(FEEDBACK_TIMEOUT if timeout is None else timeout, step=step)

    async def write_payload(self, payload: bytes) -> WriteResult:
        """Execute 4-step image transfer handshake with an encoded payload."""
        compression2 = bool(self.preset.extra.get("compression2", False))
        timing = WriteTiming(settle_s=NOTIFY_SETTLE_S, bytes=len(payload))
        # Let the caller report how far the attempt got (see write_prepared).
        with timing.reported():
            return await self._transfer(payload, compression2, timing)

    async def _handshake(self, packet_size: int, compression2: bool, timing: WriteTiming) -> int:
        """Steps 1-3: START (probed), SIZE, IMAGE START. Returns the first part wanted."""
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
        return int.from_bytes(img_start_resp[2:6], "little")

    async def _transfer(
        self, payload: bytes, compression2: bool, timing: WriteTiming
    ) -> WriteResult:
        packet_size = len(payload)
        async with Notifications(self.client, self.cmd_uuid, settle=NOTIFY_SETTLE_S) as replies:
            self._replies = replies
            with timing.stage("start_s"):
                part = await self._handshake(packet_size, compression2, timing)

            # Step 4: IMAGE_DATA chunk loop.
            total_parts = (packet_size + 239) // 240
            timing["parts"] = total_parts
            await self._send_parts(payload, part, total_parts, timing)
            return WriteResult(success=True, timing=timing)

    async def _send_parts(
        self, payload: bytes, part: int, total_parts: int, timing: WriteTiming
    ) -> None:
        """Step 4: the IMAGE_DATA loop.

        The tag drives the transfer by answering each chunk with the part it
        wants next; asking for the same part again is its way of requesting a
        resend. The counters land in `timing` even when the loop raises.
        """
        packet_size = len(payload)
        last_part = -1
        same_part_count = 0
        sends = resends = 0
        timing["completed_by_tag"] = False
        try:
            with timing.stage("transfer_s"):
                while part * 240 < packet_size:
                    sends += 1
                    data_packet = make_size_packet(part, payload)
                    resp = await self._write_with_response(
                        self.img_uuid, data_packet, f"part {part}/{total_parts}", pace=True
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
                        timing["completed_by_tag"] = True
                        break
                    if (
                        len(resp) < 6
                        or resp[0] != RESP_IMAGE_DATA
                        or resp[1] != RESP_STATUS_NEXT_PART
                    ):
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

        finally:
            # A stalled transfer is exactly when the counters matter, so they
            # are filled in whether or not the loop finished.
            # sends = parts + resends; round_trip_ms * sends ~= transfer_s
            timing["sends"], timing["resends"] = sends, resends
            transfer_s = float(timing.get("transfer_s", 0.0))
            timing["round_trip_ms"] = round(transfer_s / sends * 1000) if sends else 0


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[bytes],
    *,
    pacing_s: float = 0.0,
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
        pacing_s=pacing_s,
    )
    return await picksmart.write_payload(await prepared)
