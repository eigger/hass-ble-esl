"""ETAG image transfer with checked notifications."""

import asyncio
import inspect

from blesession import SessionTrace

from ..base import STAGE_FINISH, STAGE_HANDSHAKE, STAGE_TRANSFER, WriteRefused, WriteResult
from .const import CHARACTERISTIC, FIRMWARE, PANELS, SERVICE
from .image import encode, encode_image
from .wire import HANDSHAKE, MAX_PACKET, REFRESH, image_packets

REPLY_TIMEOUT_S = 30
REPLIES = {5: 6, 0x11: 0x12, 7: 8, 1: 2, 3: 4}
CMD_IMAGE = 1


def prepare(preset, image, address):
    """Frame the image for every supported panel; the firmware picks one after connecting."""
    return {
        panel: list(image_packets(planes)) for panel, planes in encode_image(image, preset).items()
    }


def panel_for(firmware):
    return next((panel for panel in PANELS if panel in firmware), None)


async def write_session(client, address, preset, prepared, *, pacing_s=0.0, trace):
    firmware = (await client.read_gatt_char(FIRMWARE)).decode(errors="replace")
    panel = panel_for(firmware)
    if panel is None:
        # Retrying cannot change the firmware, so do not hold the BLE lock again.
        raise WriteRefused(f"Unsupported ETAG panel firmware: {firmware.strip(chr(0))}")
    trace.note(firmware=panel)

    async def image():
        return (await prepared)[panel]

    await EtagConnection(client, firmware, pacing_s=pacing_s).send(image(), trace=trace)
    return WriteResult(success=True)


class EtagConnection:
    """Transfer one image and check every command acknowledgment."""

    def __init__(self, client, firmware, *, pacing_s=0.0):
        self.client = client
        self.firmware = firmware
        self.pacing_s = max(0.0, pacing_s)

    async def write(self, image, *, timeout, log, progress):
        """Frame and send an image (the standalone entry point)."""
        await self.send(
            list(image_packets(encode(image, self.firmware))),
            timeout=timeout,
            log=log,
            progress=progress,
        )

    def _characteristic(self):
        service = self.client.services.get_service(SERVICE)
        char = service.get_characteristic(CHARACTERISTIC) if service is not None else None
        if char is None:
            raise RuntimeError("ETAG FFE0/FFE1 characteristic missing")
        return char

    async def send(self, image, *, timeout=REPLY_TIMEOUT_S, log=None, progress=None, trace=None):
        """Handshake, image packets, refresh; every packet is acknowledged.

        `image` is the list of image packets, or an awaitable of it: it is
        awaited only after the handshake, so a slow encode overlaps it.
        """
        if trace is None:
            trace = SessionTrace()
        log = [] if log is None else log
        char = self._characteristic()
        if char.max_write_without_response_size < MAX_PACKET:
            raise RuntimeError(
                f"Bluetooth write size {char.max_write_without_response_size} is too small "
                f"for the app's {MAX_PACKET}-byte packets"
            )
        queue = asyncio.Queue()

        def notification(_, data):
            raw = bytes(data)
            log.append({"rx": raw.hex()})
            queue.put_nowait(raw)

        await self.client.start_notify(char, notification)
        sent = 0
        total = None

        async def run(batch, *, paced=False):
            nonlocal sent
            for packet in batch:
                await self._exchange(char, queue, packet, timeout, log)
                sent += 1
                if progress is not None:
                    progress(sent, total)
                if paced and self.pacing_s:
                    await asyncio.sleep(self.pacing_s)

        if not inspect.isawaitable(image):
            total = len(HANDSHAKE) + len(image) + len(REFRESH)
        try:
            with trace.timed(STAGE_HANDSHAKE):
                await run(HANDSHAKE)
        except BaseException:
            if inspect.iscoroutine(image):
                image.close()  # never needed; avoid a "never awaited" warning
            raise
        if inspect.isawaitable(image):
            image = await image
            total = len(HANDSHAKE) + len(image) + len(REFRESH)
        trace.note(parts=total, bytes=sum(map(len, image)))
        with trace.timed(STAGE_TRANSFER):
            await run(image, paced=True)
        with trace.timed(STAGE_FINISH):
            await run(REFRESH)
            await asyncio.sleep(1)

    async def _exchange(self, char, queue, packet, timeout, log):
        log.append({"tx": packet.hex()})
        await self.client.write_gatt_char(char, packet, response=False)
        reply = await asyncio.wait_for(queue.get(), timeout=timeout)
        if not (reply.startswith(b"\x91") and reply.endswith(b"\x19")):
            raise RuntimeError(f"Unexpected response: {reply.hex()}")
        command = packet[1]
        expected = REPLIES[command]
        if len(reply) < 4 or reply[1] != expected:
            raise RuntimeError(f"Expected response {expected:02x}, got {reply.hex()}")
        if command == CMD_IMAGE:
            if (
                len(reply) < 6
                or int.from_bytes(reply[2:4], "little") != int.from_bytes(packet[3:5], "big")
                or reply[4] != 0
            ):
                raise RuntimeError(f"Image packet rejected: {reply.hex()}")
        elif command != 7 and reply[2] != 0:
            raise RuntimeError(f"Command rejected: {reply.hex()}")
