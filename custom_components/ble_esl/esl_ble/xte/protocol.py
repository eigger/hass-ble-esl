"""XTE wire formats: advertisement, image object, command and block frames, replies."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .const import BLOCK_DATA_SIZE

# Manufacturer data (company id 0x5258 stripped):
#   [0] record type   [1] hardware revision   [2] firmware major.minor (BCD)
#   [3] firmware patch   [4:6] device number (u16, the tag type)
#   [6] battery %   [7] chip type << 4 | tx power
# The tag alternates this record with a 2-byte `ff 01` payload under the
# same company id; the record-type check rejects that one.
RECORD_TYPES = frozenset({0xFD, 0xFE, 0xFC, 0x04})
ADVERTISEMENT_MIN_LENGTH = 8


@dataclass(frozen=True)
class Advertisement:
    """Fields decoded from an XTE manufacturer-data record."""

    record_type: int
    hardware_revision: int
    firmware: str
    device_number: int
    battery_percent: int
    chip_type: int
    tx_power: int


def parse_advertisement(data: bytes | None) -> Advertisement | None:
    """Decode an XTE record, or None if `data` is not one."""
    if data is None or len(data) < ADVERTISEMENT_MIN_LENGTH or data[0] not in RECORD_TYPES:
        return None
    return Advertisement(
        record_type=data[0],
        hardware_revision=data[1],
        firmware=f"{data[2] >> 4}.{data[2] & 0x0F}.{data[3]}",
        device_number=int.from_bytes(data[4:6], "big"),
        battery_percent=min(100, data[6]),
        chip_type=data[7] >> 4,
        tx_power=data[7] & 0x0F,
    )


def row_bytes(width: int) -> int:
    """Packed bytes per buffer row: four pixels per byte, padded to a whole byte."""
    return (width + 3) // 4


def run_length(data: bytes) -> bytes:
    """(count, value) pairs, runs split at 255 bytes."""
    out = bytearray()
    pos, total = 0, len(data)
    while pos < total:
        value = data[pos]
        end = pos + 1
        while end < total and end - pos < 255 and data[end] == value:
            end += 1
        out += bytes((end - pos, value))
        pos = end
    return bytes(out)


# After the length field: image count 1, offset 17 of the one image record,
# the record's x 0 and y 0; width, height, compression (1 = RLE) and the
# compressed size follow.
OBJECT_HEADER = bytes.fromhex("01000000110000000000000000")
COMPRESSION_RLE = 1


def image_object(pixels: bytes, width: int, height: int) -> bytes:
    """The XTEK container: one full-screen record of run-length packed rows."""
    if len(pixels) != row_bytes(width) * height:
        raise ValueError(f"Expected {row_bytes(width) * height} bytes of packed XTE pixels")
    # The tag's encoder restarts its run halfway through the frame; keep that
    # boundary even when the bytes either side of it are equal.
    half = len(pixels) // 2
    data = run_length(pixels[:half]) + run_length(pixels[half:])
    body = OBJECT_HEADER + struct.pack(">IIBI", width, height, COMPRESSION_RLE, len(data)) + data
    return b"XTEK" + struct.pack(">II", sum(body) & 0xFFFFFFFF, 12 + len(body)) + body


def command(payload: bytes) -> bytes:
    """Control frame: `XTE 01`, total length (u8), payload checksum, payload."""
    if len(payload) > 249:
        raise ValueError("XTE command too long")
    return b"XTE\x01" + bytes((6 + len(payload), sum(payload) & 0xFF)) + payload


def blocks(obj: bytes) -> list[bytes]:
    """The object in numbered, checksummed blocks of up to 1211 data bytes."""
    count = (len(obj) + BLOCK_DATA_SIZE - 1) // BLOCK_DATA_SIZE
    if not 1 <= count <= 255:
        raise ValueError("Invalid XTE block count")
    out = []
    for number in range(count):
        payload = (
            bytes((count, number)) + obj[number * BLOCK_DATA_SIZE : (number + 1) * BLOCK_DATA_SIZE]
        )
        out.append(b"XTE\x02" + struct.pack(">HB", 7 + len(payload), sum(payload) & 0xFF) + payload)
    return out


def check_reply(frame: bytes, expected: bytes) -> bool:
    """True for the `XTE 04` reply carrying `expected`; other notifications are ignored.

    A malformed reply, or one with another body, raises: only the known
    positive replies count as success.
    """
    if not frame.startswith(b"XTE\x04"):
        return False
    if len(frame) < 6:
        raise ValueError("Truncated XTE response")
    length = frame[4]
    if length < 7 or length > len(frame):
        raise ValueError("Invalid XTE response length")
    body = frame[6:length]
    if sum(body) & 0xFF != frame[5]:
        raise ValueError("Invalid XTE response checksum")
    if body != expected:
        raise ValueError(f"Unexpected XTE response: {body.hex()}")
    return True
