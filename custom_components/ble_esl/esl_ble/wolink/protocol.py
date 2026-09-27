"""WOLINK wire formats: advertisement, unlock, commands, status and compression."""

from __future__ import annotations

from dataclasses import dataclass
import struct
import zlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .const import AES_KEY, OP_REFRESH_COMPRESSED, OP_WRITE_DATA

ADVERTISEMENT_LENGTH = 10


@dataclass(frozen=True)
class Advertisement:
    """The five big-endian words after company id 0xBBAA."""

    product_id: int
    app_version: int
    hardware_version: int
    display_version: int
    battery_mv: int


def parse_advertisement(data: bytes | None) -> Advertisement | None:
    """Decode WOLINK manufacturer data, or None if it is too short."""
    if data is None or len(data) < ADVERTISEMENT_LENGTH:
        return None
    return Advertisement(*struct.unpack_from(">5H", data))


def battery_plausible(millivolts: int) -> bool:
    """A coin or AA-class cell reads between 1.5 and 4.2 V."""
    return 1500 <= millivolts <= 4200


def unlock_response(nonce: bytes) -> bytes:
    """The auth characteristic's nonce, AES-128-ECB encrypted with the vendor key."""
    encryptor = Cipher(algorithms.AES(AES_KEY), modes.ECB()).encryptor()
    return encryptor.update(bytes(nonce)) + encryptor.finalize()


def write_data_command(offset: int, data: bytes) -> bytes:
    """Store `data` at `offset` of the tag's image buffer."""
    return struct.pack("<HI", OP_WRITE_DATA, offset) + data


def refresh_command(size: int) -> bytes:
    """Redraw the panel from the first `size` stored bytes, block compressed."""
    return struct.pack("<HI", OP_REFRESH_COMPRESSED, size)


def status_error(frame: bytes) -> int:
    """Error code of a status frame (byte 1), 0 when there is none."""
    return frame[1] if len(frame) >= 2 else 0


def status_idle(frame: bytes) -> bool:
    """The tag is done: byte 0 is 0x00 (not busy) or 0xFF (refresh finished)."""
    return bool(frame) and frame[0] in (0x00, 0xFF)


COMPRESSION_MAGIC = b"\xa5\xa6"
COMPRESSION_FORMAT = 0x02
COMPRESSION_BLOCK = 8192


def compress(data: bytes) -> bytes:
    """Block-compressed picture: raw DEFLATE per 8 KiB, behind a four-byte header.

    Header `A5 A6 <block count> 02`, then per block its 1-based index, its
    compressed size (u16 little endian) and the deflate stream.
    """
    blocks = [data[i : i + COMPRESSION_BLOCK] for i in range(0, len(data), COMPRESSION_BLOCK)]
    if not 1 <= len(blocks) <= 255:
        raise ValueError(f"{len(data)} bytes do not fit 1-255 compression blocks")
    out = bytearray(COMPRESSION_MAGIC)
    out += bytes((len(blocks), COMPRESSION_FORMAT))
    for index, block in enumerate(blocks, start=1):
        deflate = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
        stream = deflate.compress(block) + deflate.flush()
        out += bytes((index,)) + struct.pack("<H", len(stream)) + stream
    return bytes(out)
