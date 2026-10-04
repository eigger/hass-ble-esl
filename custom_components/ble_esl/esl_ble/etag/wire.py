"""ETAG command framing, image packets and reply checks."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from blesession import DeviceError

from .const import CMD_IMAGE, CMD_VERSION, REPLIES

if TYPE_CHECKING:
    from collections.abc import Iterator

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


class EtagError(DeviceError):
    """The tag's reply was unusable, or the link cannot carry the app's packets."""


def plane_bytes(width: int, height: int) -> int:
    """One plane: a byte-aligned column per x."""
    return width * ((height + 7) // 8)


def image_packet_count(width: int, height: int) -> int:
    """Image packets for both planes; the same for either panel orientation."""
    return 2 * ((plane_bytes(width, height) + CHUNK - 1) // CHUNK)


def image_packets(planes: tuple[bytes, bytes]) -> Iterator[bytes]:
    """Each plane as numbered chunks: header, up to 230 bytes, trailer."""
    for plane, data in enumerate(planes):
        count = (len(data) + CHUNK - 1) // CHUNK
        for index in range(count):
            chunk = data[index * CHUNK : (index + 1) * CHUNK]
            yield struct.pack(HEADER, 0xAC, 1, plane, index, count, len(chunk)) + chunk + b"\xca"


def frames(planes: tuple[bytes, bytes]) -> Iterator[bytes]:
    """The whole transfer in order: handshake, image packets, refresh."""
    yield from HANDSHAKE
    yield from image_packets(planes)
    yield from REFRESH


def check_reply(packet: bytes, reply: bytes) -> None:
    """Raise EtagError unless `reply` is the tag's successful answer to `packet`."""
    if not (reply.startswith(b"\x91") and reply.endswith(b"\x19")):
        raise EtagError(f"Unexpected response: {reply.hex()}")
    command = packet[1]
    expected = REPLIES[command]
    if len(reply) < 4 or reply[1] != expected:
        raise EtagError(f"Expected response {expected:02x}, got {reply.hex()}")
    if command == CMD_IMAGE:
        if (
            len(reply) < 6
            or int.from_bytes(reply[2:4], "little") != int.from_bytes(packet[3:5], "big")
            or reply[4] != 0
        ):
            raise EtagError(f"Image packet rejected: {reply.hex()}")
    elif command != CMD_VERSION and reply[2] != 0:
        raise EtagError(f"Command rejected: {reply.hex()}")
