"""Capture-verified XTE pixel packing and framing (PSJ-420)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .const import BLOCK_DATA_SIZE, PALETTES

if TYPE_CHECKING:
    from PIL import Image

    from ..base import DevicePreset

# Opaque XTEK header fields (object offsets 12..24 and 33) preserved from the
# single PSJ-420 capture; not a general specification for all XTE devices.
OBJECT_METADATA = bytes.fromhex("01000000110000000000000000")
OBJECT_FLAG = b"\x01"


def pack_pixels(image: Image.Image, preset: DevicePreset) -> bytes:
    """Pack four pixels per byte, most significant pixel first."""
    if image.size != (preset.width, preset.height):
        raise ValueError(f"XTE requires a {preset.width}x{preset.height} image")
    palette = PALETTES[preset.colors]
    rgb = image.convert("RGB")
    # Quantize using a fixed palette without dithering, like the HA renderer.
    result = bytearray()
    packed = 0
    color_cache = {color: index for index, color in enumerate(palette)}
    raw = rgb.tobytes()
    for i, pixel in enumerate(zip(raw[0::3], raw[1::3], raw[2::3], strict=True)):
        value = color_cache.get(pixel)
        if value is None:
            value = min(
                range(4), key=lambda n: sum((pixel[c] - palette[n][c]) ** 2 for c in range(3))
            )
            color_cache[pixel] = value
        packed = (packed << 2) | value
        if i % 4 == 3:
            result.append(packed)
            packed = 0
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


def make_image_object(pixels: bytes, preset: DevicePreset) -> bytes:
    """Build XTEK metadata, RLE image and 32-bit additive checksum."""
    expected = preset.width * preset.height // 4
    if len(pixels) != expected:
        raise ValueError(f"Expected {expected} bytes of packed XTE pixels")
    # The captured encoder resets its run at byte 15000, halfway through the
    # frame. Preserve that boundary even when both adjacent bytes are equal.
    midpoint = len(pixels) // 2
    compressed = encode_rle(pixels[:midpoint]) + encode_rle(pixels[midpoint:])
    body = (
        OBJECT_METADATA
        + preset.width.to_bytes(4, "big")
        + preset.height.to_bytes(4, "big")
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
