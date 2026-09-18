"""Capture-verified PSJ-420 pixel packing and XTE framing."""

import math
from PIL import Image
from .const import ADVERTISEMENT, WIDTH, HEIGHT, PALETTE, BLOCK_DATA_SIZE

def is_psj420_advertisement(data: bytes | None) -> bool:
    """Recognize the observed PSJ-420 signature, ignoring its changing tail."""
    return data is not None and len(data) == 13 and data[:12] == ADVERTISEMENT[:12]


def pack_pixels(image: Image.Image) -> bytes:
    """Pack four pixels per byte, most significant pixel first."""
    if image.size != (WIDTH, HEIGHT):
        raise ValueError("XTE requires a 400x300 image")
    rgb = image.convert("RGB")
    # Quantize using a fixed palette without dithering, like the HA renderer.
    result = bytearray()
    packed = 0
    color_cache = {color: index for index, color in enumerate(PALETTE)}
    raw = rgb.tobytes()
    for i, pixel in enumerate(zip(raw[0::3], raw[1::3], raw[2::3])):
        value = color_cache.get(pixel)
        if value is None:
            value = min(range(4), key=lambda n: sum(
                (pixel[c] - PALETTE[n][c]) ** 2 for c in range(3)
            ))
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


def make_image_object(pixels: bytes) -> bytes:
    """Build XTEK metadata, RLE image and 32-bit additive checksum."""
    if len(pixels) != WIDTH * HEIGHT // 4:
        raise ValueError("Expected 30000 bytes of packed XTE pixels")
    # The captured encoder resets its run at byte 15000, halfway through the
    # frame. Preserve that boundary even when both adjacent bytes are equal.
    midpoint = len(pixels) // 2
    compressed = encode_rle(pixels[:midpoint]) + encode_rle(pixels[midpoint:])
    # Preserve observed opaque fields (offsets 12..24 and 33) for this profile.
    metadata = bytes.fromhex("01000000110000000000000000")
    body = (metadata + WIDTH.to_bytes(4, "big") + HEIGHT.to_bytes(4, "big")
            + b"\x01" + len(compressed).to_bytes(4, "big") + compressed)
    return (b"XTEK" + (sum(body) & 0xFFFFFFFF).to_bytes(4, "big")
            + (12 + len(body)).to_bytes(4, "big") + body)


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
        payload = bytes((count, number)) + image_object[
            number * BLOCK_DATA_SIZE:(number + 1) * BLOCK_DATA_SIZE
        ]
        blocks.append(b"XTE\x02" + (7 + len(payload)).to_bytes(2, "big")
                      + bytes((sum(payload) & 0xFF,)) + payload)
    return blocks


