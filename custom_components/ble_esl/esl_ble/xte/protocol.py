"""XTE advertisement decoding, pixel packing and framing.

Framing and packing are capture-verified on the PSJ-420. The advertisement
layout (see docs/xte.md) is common to the XTE firmware family.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from .const import BLOCK_DATA_SIZE, PALETTES

if TYPE_CHECKING:
    from PIL import Image

    from ..base import DevicePreset

# Manufacturer data (company id 0x5258 stripped):
#   [0] record type   [1] hardware revision   [2] firmware major.minor (BCD)
#   [3] firmware patch   [4:6] device number (u16, identifies the tag type)
#   [6] battery %   [7] chip type << 4 | tx power   [8:] not read by the app
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


# XTEK container header after the length field: image count 1, offset of
# the (only) image record 17, then the record's x 0 and y 0; width and
# height follow. OBJECT_FLAG is the record's compression byte, 1 = RLE.
OBJECT_METADATA = bytes.fromhex("01000000110000000000000000")
OBJECT_FLAG = b"\x01"


def buffer_size(preset: DevicePreset) -> tuple[int, int]:
    """Native buffer dimensions: the as-viewed size, swapped when the panel scans the other way."""
    if preset.extra.get("rotation", 0) % 180:
        return preset.height, preset.width
    return preset.width, preset.height


def row_bytes(width: int) -> int:
    """Packed bytes per row: four pixels per byte, the row padded to a multiple of four."""
    return math.ceil(width / 4)


def pack_pixels(image: Image.Image, preset: DevicePreset) -> bytes:
    """Rotate into the native buffer, then pack four pixels per byte, first pixel in the high bits."""
    if image.size != (preset.width, preset.height):
        raise ValueError(f"XTE requires a {preset.width}x{preset.height} image")
    rotation = preset.extra.get("rotation", 0)
    if rotation:
        image = image.rotate(rotation, expand=True)
    width, height = image.size
    palette = PALETTES[preset.colors]
    # Quantize using a fixed palette without dithering, like the HA renderer.
    color_cache = {color: index for index, color in enumerate(palette)}

    def code(pixel: tuple[int, int, int]) -> int:
        value = color_cache.get(pixel)
        if value is None:
            value = min(
                range(4), key=lambda n: sum((pixel[c] - palette[n][c]) ** 2 for c in range(3))
            )
            color_cache[pixel] = value
        return value

    raw = image.convert("RGB").tobytes()
    stride = width * 3
    padding = (-width) % 4  # padded pixels pack as code 0 (black)
    result = bytearray()
    for y in range(height):
        row = raw[y * stride : (y + 1) * stride]
        codes = [code(p) for p in zip(row[0::3], row[1::3], row[2::3], strict=True)]
        codes.extend([0] * padding)
        for i in range(0, len(codes), 4):
            result.append(
                (codes[i] << 6) | (codes[i + 1] << 4) | (codes[i + 2] << 2) | codes[i + 3]
            )
    return bytes(result)


def encode_rle(data: bytes) -> bytes:
    """Encode (count, value) runs, splitting runs at 255 bytes."""
    output = bytearray()
    pos = 0
    while pos < len(data):
        end = pos + 1
        while end < len(data) and end - pos < 255 and data[end] == data[pos]:
            end += 1
        output.extend((end - pos, data[pos]))
        pos = end
    return bytes(output)


def make_image_object(pixels: bytes, width: int, height: int) -> bytes:
    """Build the XTEK container (one full-screen image record) around packed buffer rows."""
    expected = row_bytes(width) * height
    if len(pixels) != expected:
        raise ValueError(f"Expected {expected} bytes of packed XTE pixels")
    # The captured encoder resets its run at byte 15000, halfway through the
    # frame. Preserve that boundary even when both adjacent bytes are equal.
    midpoint = len(pixels) // 2
    compressed = encode_rle(pixels[:midpoint]) + encode_rle(pixels[midpoint:])
    body = (
        OBJECT_METADATA
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + OBJECT_FLAG
        + len(compressed).to_bytes(4, "big")
        + compressed
    )
    return (
        b"XTEK"
        + (sum(body) & 0xFFFFFFFF).to_bytes(4, "big")
        + (12 + len(body)).to_bytes(4, "big")
        + body
    )


def make_command(payload: bytes) -> bytes:
    """Control frames use a one-byte total length and payload checksum."""
    if len(payload) > 249:
        raise ValueError("XTE command too long")
    return b"XTE\x01" + bytes((6 + len(payload), sum(payload) & 0xFF)) + payload


def make_blocks(image_object: bytes) -> list[bytes]:
    """Frame the object into numbered, checksummed logical blocks."""
    count = math.ceil(len(image_object) / BLOCK_DATA_SIZE)
    if not 1 <= count <= 255:
        raise ValueError("Invalid XTE block count")
    blocks = []
    for number in range(count):
        payload = (
            bytes((count, number))
            + image_object[number * BLOCK_DATA_SIZE : (number + 1) * BLOCK_DATA_SIZE]
        )
        blocks.append(
            b"XTE\x02"
            + (7 + len(payload)).to_bytes(2, "big")
            + bytes((sum(payload) & 0xFF,))
            + payload
        )
    return blocks
