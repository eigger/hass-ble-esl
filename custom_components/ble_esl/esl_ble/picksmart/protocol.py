"""PickSmart wire formats: advertisement, commands, data parts and replies."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .const import (
    CMD_IMAGE,
    CMD_SIZE,
    CMD_START,
    PART_DONE,
    PART_NEXT,
    PART_SIZE,
    REPLY_PART,
    REPLY_SIZE,
    REPLY_START,
)

ADVERTISEMENT_LENGTH = 5


@dataclass(frozen=True)
class Advertisement:
    """The five bytes after company id 0x5053."""

    device_id: int
    battery_mv: int
    firmware: int
    hardware: int

    @property
    def model_key(self) -> str:
        return f"0x{self.device_id:04X}"


def parse_advertisement(data: bytes | None) -> Advertisement | None:
    """Hardware is bytes 4 and 0 (its low 14 bits the device id), battery byte 1 in 0.1 V,
    firmware bytes 2-3."""
    if data is None or len(data) != ADVERTISEMENT_LENGTH:
        return None
    hardware = data[4] << 8 | data[0]
    return Advertisement(
        device_id=hardware & 0x3FFF,
        battery_mv=data[1] * 100,
        firmware=data[2] << 8 | data[3],
        hardware=hardware,
    )


def start_command() -> bytes:
    return bytes((CMD_START,))


def size_command(size: int, *, quicklz: bool) -> bytes:
    """Payload size (u32 little endian); a QuickLZ payload is flagged in a sixth byte."""
    if quicklz:
        return struct.pack("<BIB", CMD_SIZE, size, 0x01)
    return struct.pack("<BI3x", CMD_SIZE, size)


def image_command() -> bytes:
    return bytes((CMD_IMAGE,))


def part_count(size: int) -> int:
    return (size + PART_SIZE - 1) // PART_SIZE


def data_packet(part: int, payload: bytes) -> bytes:
    """Part number (u32 little endian), then that part's 240 bytes of the payload."""
    return struct.pack("<I", part) + payload[part * PART_SIZE : (part + 1) * PART_SIZE]


def is_start_reply(frame: bytes) -> bool:
    return frame[:3] == REPLY_START


def is_size_reply(frame: bytes) -> bool:
    return frame[:1] == bytes((REPLY_SIZE,))


def is_done_reply(frame: bytes) -> bool:
    return frame[:2] == bytes((REPLY_PART, PART_DONE))


def requested_part(frame: bytes) -> int | None:
    """The part the tag asks for next, or None if `frame` is not such a request."""
    if len(frame) < 6 or frame[:2] != bytes((REPLY_PART, PART_NEXT)):
        return None
    return int.from_bytes(frame[2:6], "little")
