"""ETAG command framing and image packets."""

import struct

from .const import SIZE
from .image import encode

# APK SendPublishTemplateActivity.h2, type 1. These are app commands,
# not Bluetooth pairing or firmware flashing.
HANDSHAKE = (
    bytes.fromhex("ac05ca"),
    bytes.fromhex("ac1100112233445566778899112233445566ca"),
    bytes.fromhex("ac07ca"),
)
REFRESH = (bytes.fromhex("ac03ca"),)
CHUNK = 230
HEADER = ">BBBHHH"
MAX_PACKET = struct.calcsize(HEADER) + CHUNK + 1
# Two planes of one 16-byte padded column per x, whichever the panel.
PLANE_BYTES = SIZE[0] * ((SIZE[1] + 7) // 8)
IMAGE_PACKETS = 2 * ((PLANE_BYTES + CHUNK - 1) // CHUNK)


def packets(image, firmware):
    return frames(encode(image, firmware))


def frames(planes):
    yield from HANDSHAKE
    yield from image_packets(planes)
    yield from REFRESH


def image_packets(planes):
    for plane, data in enumerate(planes):
        count = (len(data) + CHUNK - 1) // CHUNK
        for index in range(count):
            chunk = data[index * CHUNK : (index + 1) * CHUNK]
            yield struct.pack(HEADER, 0xAC, 1, plane, index, count, len(chunk)) + chunk + b"\xca"
