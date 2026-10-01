"""ETAG image transfer with checked notifications."""

import asyncio

from ..base import WriteResult
from .const import CHARACTERISTIC, FIRMWARE, SERVICE
from .image import encode_image, quantize
from .wire import packets


def prepare(preset, image, address):
    return encode_image(image, preset)


async def write_session(client, address, preset, prepared, *, pacing_s=0.0, trace):
    firmware = (await client.read_gatt_char(FIRMWARE)).decode()
    if not any(panel in firmware for panel in ("SE0213NP61-TNG-A0", "SE0213MN50-TNG-A0")):
        raise ValueError(f"Unsupported ETAG panel firmware: {firmware}")
    image = await prepared
    with trace.timed("transfer"):
        await EtagConnection(client, firmware).write(
            image, timeout=30, log=[], progress=lambda done, total: None
        )
    return WriteResult(success=True)


class EtagConnection:
    """Transfer one image and check every command acknowledgment."""

    def __init__(self, client, firmware):
        self.client = client
        self.firmware = firmware

    async def write(self, image, *, timeout, log, progress):
        image = quantize(image)
        char = self.client.services.get_service(SERVICE).get_characteristic(CHARACTERISTIC)
        outgoing = list(packets(image, self.firmware))
        if char.max_write_without_response_size < max(map(len, outgoing)):
            raise ValueError("Bluetooth write size is too small for the app's 240-byte packets")
        queue = asyncio.Queue()

        def notification(_, data):
            raw = bytes(data)
            log.append({"rx": raw.hex()})
            queue.put_nowait(raw)

        await self.client.start_notify(char, notification)
        for n, packet in enumerate(outgoing, 1):
            log.append({"tx": packet.hex()})
            await self.client.write_gatt_char(char, packet, response=False)
            reply = await asyncio.wait_for(queue.get(), timeout=timeout)
            if not (reply.startswith(b"\x91") and reply.endswith(b"\x19")):
                raise RuntimeError(f"Unexpected response: {reply.hex()}")
            command = packet[1]
            expected = {5: 6, 0x11: 0x12, 7: 8, 1: 2, 3: 4}[command]
            if reply[1] != expected:
                raise RuntimeError(f"Expected response {expected:02x}, got {reply.hex()}")
            if command == 1:
                if (
                    int.from_bytes(reply[2:4], "little") != int.from_bytes(packet[3:5], "big")
                    or reply[4] != 0
                ):
                    raise RuntimeError(f"Image packet rejected: {reply.hex()}")
            elif command != 7 and reply[2] != 0:
                raise RuntimeError(f"Command rejected: {reply.hex()}")
            progress(n, len(outgoing))
        await asyncio.sleep(1)
