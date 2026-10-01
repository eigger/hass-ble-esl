"""ETAG write session: handshake, image packets, refresh; every packet acknowledged."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import inspect
import logging
from typing import TYPE_CHECKING

from blesession import Notifications, SessionTrace

from ..base import (
    STAGE_FINISH,
    STAGE_HANDSHAKE,
    STAGE_TRANSFER,
    DevicePreset,
    WriteRefused,
    WriteResult,
)
from .const import (
    CHARACTERISTIC_UUID,
    FIRMWARE_UUID,
    PANELS,
    REFRESH_SETTLE_S,
    REPLY_TIMEOUT_S,
    SERVICE_UUID,
)
from .image import encode_image
from .wire import (
    HANDSHAKE,
    MAX_PACKET,
    REFRESH,
    EtagError,
    check_reply,
    image_packet_count,
    image_packets,
)

if TYPE_CHECKING:
    from bleak import BleakClient
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from PIL import Image

_LOGGER = logging.getLogger(__name__)


def prepare(preset: DevicePreset, image: Image.Image, address: str) -> dict[str, list[bytes]]:
    """Frame the image for every supported panel; the firmware picks one after connecting."""
    return {
        panel: list(image_packets(planes)) for panel, planes in encode_image(image, preset).items()
    }


def panel_for(firmware: str) -> str | None:
    """The supported panel the firmware string names, or None."""
    return next((panel for panel in PANELS if panel in firmware), None)


async def write_session(
    client: BleakClient,
    address: str,
    preset: DevicePreset,
    prepared: Awaitable[dict[str, list[bytes]]],
    *,
    pacing_s: float = 0.0,
    trace: SessionTrace,
) -> WriteResult:
    """Read the panel firmware, then send the packets that panel needs."""
    firmware = (await client.read_gatt_char(FIRMWARE_UUID)).decode(errors="replace")
    panel = panel_for(firmware)
    if panel is None:
        # Retrying cannot change the firmware, so do not hold the BLE lock again.
        _close(prepared)
        raise WriteRefused(f"Unsupported ETAG panel firmware: {firmware.strip(chr(0))}")
    trace.note(firmware=panel)

    async def packets() -> list[bytes]:
        return (await prepared)[panel]

    await EtagSession(client, address, pacing_s=pacing_s).send(
        packets(), total=image_packet_count(preset.width, preset.height), trace=trace
    )
    return WriteResult(success=True)


def _close(awaitable: object) -> None:
    """Close an encode that was never awaited, so Python does not warn about it."""
    if inspect.iscoroutine(awaitable):
        awaitable.close()


class EtagSession:
    """One connected ETAG tag."""

    def __init__(self, client: BleakClient, address: str, *, pacing_s: float = 0.0) -> None:
        self.client = client
        self.address = address
        self.pacing_s = max(0.0, pacing_s)
        self.reply_timeout_s = REPLY_TIMEOUT_S

    async def send(
        self,
        packets: Awaitable[list[bytes]],
        *,
        total: int,
        trace: SessionTrace | None = None,
    ) -> None:
        """Handshake, image packets, refresh.

        `packets` is awaited only after the handshake, so a slow encode
        overlaps it; `total` is the image packet count it must have.
        """
        if trace is None:
            trace = SessionTrace()
        try:
            char = self._characteristic()
            async with Notifications(self.client, char) as replies:
                with trace.timed(STAGE_HANDSHAKE):
                    await self._run(replies, char, HANDSHAKE)
                image = await packets
                if len(image) != total:
                    raise EtagError(f"Expected {total} image packets, got {len(image)}")
                trace.note(
                    parts=len(HANDSHAKE) + total + len(REFRESH),
                    bytes=sum(map(len, image)),
                )
                with trace.timed(STAGE_TRANSFER):
                    await self._run(replies, char, image, paced=True)
                with trace.timed(STAGE_FINISH):
                    await self._run(replies, char, REFRESH)
                    await asyncio.sleep(REFRESH_SETTLE_S)
        finally:
            _close(packets)  # never needed when the link failed first

    def _characteristic(self) -> BleakGATTCharacteristic:
        service = self.client.services.get_service(SERVICE_UUID)
        char = service.get_characteristic(CHARACTERISTIC_UUID) if service is not None else None
        if char is None:
            raise EtagError("ETAG FFE0/FFE1 characteristic missing")
        if char.max_write_without_response_size < MAX_PACKET:
            raise EtagError(
                f"Bluetooth write size {char.max_write_without_response_size} is too small "
                f"for the app's {MAX_PACKET}-byte packets"
            )
        return char

    async def _run(
        self,
        replies: Notifications,
        char: BleakGATTCharacteristic,
        batch: list[bytes] | tuple[bytes, ...],
        *,
        paced: bool = False,
    ) -> None:
        for packet in batch:
            replies.clear()
            _LOGGER.debug("ETAG %s tx: %s", self.address, packet.hex())
            await self.client.write_gatt_char(char, packet, response=False)
            reply = await replies.next(self.reply_timeout_s, step=f"command {packet[1]:#04x}")
            _LOGGER.debug("ETAG %s rx: %s", self.address, reply.hex())
            check_reply(packet, reply)
            if paced and self.pacing_s:
                await asyncio.sleep(self.pacing_s)
