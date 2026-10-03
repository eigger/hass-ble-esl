"""PickSmart write session: START, SIZE, IMAGE, then the parts the tag asks for."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import logging
from typing import TYPE_CHECKING

from blesession import Notifications, NotificationTimeout, SessionTrace

from ..base import STAGE_HANDSHAKE, STAGE_TRANSFER, DevicePreset, WriteResult
from .const import (
    MAX_SAME_PART_REQUESTS,
    NOTIFY_SETTLE_S,
    PART_SIZE,
    REPLY_TIMEOUT_S,
    RESEND_BACKOFF_S,
    SERVICE_UUID_PREFIX,
    START_PROBE_ATTEMPTS,
    START_PROBE_TIMEOUT_S,
)
from .image import encode_image
from .wire import (
    data_packet,
    image_command,
    is_done_reply,
    is_size_reply,
    is_start_reply,
    part_count,
    requested_part,
    size_command,
    start_command,
)

if TYPE_CHECKING:
    from bleak import BleakClient
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


class PickSmartError(Exception):
    """The tag answered out of protocol."""


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> bytes:
    """Encode `image` for `preset`; CPU-bound, so callers run it in a worker thread."""
    return encode_image(image, preset)


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[bytes],
    *,
    pacing_s: float = 0.0,
    trace: SessionTrace,
) -> WriteResult:
    """Find the command and image characteristics, then send the payload."""
    uuids = [
        characteristic.uuid
        for service in client.services
        if service.uuid.lower().startswith(SERVICE_UUID_PREFIX)
        for characteristic in service.characteristics
    ]
    if len(uuids) < 2:
        # Before any protocol stage: reported as a `session` failure.
        raise PickSmartError(f"Insufficient characteristics: {uuids}")
    command_uuid, image_uuid = sorted(uuids, key=lambda uuid: int(uuid[4:8], 16))[:2]
    session = PickSmartSession(client, command_uuid, image_uuid, address, pacing_s=pacing_s)
    quicklz = preset.extra.get("encoding") == "quicklz"
    return await session.send(await prepared, quicklz=quicklz, trace=trace)


class PickSmartSession:
    """One connected PickSmart tag; every write is answered on the command characteristic."""

    def __init__(
        self,
        client: BleakClient,
        command_uuid: str,
        image_uuid: str,
        address: str,
        *,
        pacing_s: float = 0.0,
    ) -> None:
        self.client = client
        self.command_uuid = command_uuid
        self.image_uuid = image_uuid
        self.address = address
        self.pacing_s = max(0.0, pacing_s)

    async def send(
        self,
        payload: bytes,
        *,
        quicklz: bool,
        pacing_s: float | None = None,
        trace: SessionTrace | None = None,
    ) -> WriteResult:
        """Open the transfer, then answer the tag's part requests until it has them all."""
        pacing = self.pacing_s if pacing_s is None else max(0.0, pacing_s)
        if trace is None:
            trace = SessionTrace()
        trace.note(settle_s=NOTIFY_SETTLE_S, bytes=len(payload))
        async with Notifications(self.client, self.command_uuid, settle=NOTIFY_SETTLE_S) as replies:
            with trace.timed(STAGE_HANDSHAKE):
                part = await self._open(replies, len(payload), quicklz, trace)
            trace.note(parts=part_count(len(payload)))
            await self._send_parts(replies, payload, part, trace, pacing=pacing)
        return WriteResult(success=True)

    async def _open(
        self, replies: Notifications, size: int, quicklz: bool, trace: SessionTrace
    ) -> int:
        """START (probed), SIZE, IMAGE; returns the first part the tag asks for."""
        for probe in range(1, START_PROBE_ATTEMPTS + 1):
            trace.note(start_probes=probe)
            try:
                reply = await self._ask(
                    replies, self.command_uuid, start_command(), "START", START_PROBE_TIMEOUT_S
                )
                break
            except NotificationTimeout:
                if probe == START_PROBE_ATTEMPTS:
                    raise NotificationTimeout(
                        START_PROBE_TIMEOUT_S,
                        step="START",
                        message=(
                            f"No response from tag to START after {probe} probes "
                            f"({START_PROBE_TIMEOUT_S:g}s each)"
                        ),
                    ) from None
                _LOGGER.debug(
                    "%s: START unanswered (%d/%d), resending",
                    self.address,
                    probe,
                    START_PROBE_ATTEMPTS,
                )
        if not is_start_reply(reply):
            raise PickSmartError(f"Unexpected start response: {reply.hex()}")

        reply = await self._ask(
            replies, self.command_uuid, size_command(size, quicklz=quicklz), "SIZE"
        )
        if not is_size_reply(reply):
            raise PickSmartError(f"Unexpected size response: {reply.hex()}")

        reply = await self._ask(replies, self.command_uuid, image_command(), "IMAGE START")
        part = requested_part(reply)
        if part is None:
            raise PickSmartError(f"Unexpected image start response: {reply.hex()}")
        return part

    async def _send_parts(
        self,
        replies: Notifications,
        payload: bytes,
        part: int,
        trace: SessionTrace,
        *,
        pacing: float = 0.0,
    ) -> None:
        """Send each part the tag asks for; asking for the same part again means resend.

        The counters land on the trace even when the loop raises: a stalled
        transfer is exactly when they matter.
        """
        size = len(payload)
        total = part_count(size)
        last_part = -1
        same_part = 0
        sends = resends = 0
        completed_by_tag = False
        try:
            with trace.timed(STAGE_TRANSFER):
                while part * PART_SIZE < size:
                    sends += 1
                    reply = await self._ask(
                        replies,
                        self.image_uuid,
                        data_packet(part, payload),
                        f"part {part}/{total}",
                        pace=True,
                        pacing=pacing,
                    )
                    if is_done_reply(reply):
                        # Anything before the last part is a short transfer,
                        # whatever the tag thinks.
                        if (part + 1) * PART_SIZE < size:
                            raise PickSmartError(
                                f"Tag reported completion after part {part}/{total}"
                            )
                        completed_by_tag = True
                        break
                    next_part = requested_part(reply)
                    if next_part is None:
                        raise PickSmartError(
                            f"Unexpected reply after part {part}/{total}: {reply.hex()}"
                        )
                    if next_part == last_part:
                        same_part += 1
                        resends += 1
                        if same_part >= MAX_SAME_PART_REQUESTS:
                            raise PickSmartError(
                                f"Transfer stalled: part {next_part}/{total} "
                                f"requested {same_part} times"
                            )
                        _LOGGER.debug(
                            "%s: tag re-requested part %d/%d (%d/%d), resending",
                            self.address,
                            next_part,
                            total,
                            same_part,
                            MAX_SAME_PART_REQUESTS,
                        )
                        # A tag still committing the previous part tends to
                        # reject a resend sent straight away.
                        await asyncio.sleep(RESEND_BACKOFF_S * (same_part - 1))
                    else:
                        same_part = 1
                        last_part = next_part
                    part = next_part
        finally:
            # sends = parts + resends; round_trip_ms * sends ~= transfer time
            transfer_s = trace.timings.get(STAGE_TRANSFER, 0.0)
            trace.note(
                completed_by_tag=completed_by_tag,
                sends=sends,
                resends=resends,
                round_trip_ms=round(transfer_s / sends * 1000) if sends else 0,
            )

    async def _ask(
        self,
        replies: Notifications,
        uuid: str,
        packet: bytes,
        step: str,
        timeout: float | None = None,
        *,
        pace: bool = False,
        pacing: float | None = None,
    ) -> bytes:
        """Write `packet` and return the tag's reply; `pace` adds the retry pacing."""
        delay = self.pacing_s if pacing is None else pacing
        return await replies.request(
            uuid,
            packet,
            timeout=REPLY_TIMEOUT_S if timeout is None else timeout,
            step=step,
            pace_s=delay if pace else 0.0,
        )
