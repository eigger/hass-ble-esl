"""WOLINK image buffers: the picture in the panel's scan order, packed by palette."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import ImageOps

if TYPE_CHECKING:
    from PIL import Image

    from ..base import DevicePreset

ROTATIONS = (0, 90, 180, 270)

# Color codes; on BWRY panels they are the 2-bit pixel values.
BLACK, WHITE, YELLOW, RED = 0, 1, 2, 3
RGB = {BLACK: (0, 0, 0), WHITE: (255, 255, 255), YELLOW: (255, 255, 0), RED: (255, 0, 0)}
PALETTES = {"BWRY": (BLACK, WHITE, YELLOW, RED), "BWR": (BLACK, WHITE, RED)}


def encode_image(image: Image.Image, preset: DevicePreset) -> bytes:
    """The uncompressed buffer for `preset`: 2 bits per pixel on BWRY, two frames on BWR."""
    scanned = scan_order(image, preset)
    codes = color_codes(scanned, preset.colors)
    if preset.colors == "BWRY":
        return pack_2bpp(codes, scanned.width)
    return pack_black_and_red(codes, scanned.width)


def scan_order(image: Image.Image, preset: DevicePreset) -> Image.Image:
    """Turn `rotation` degrees counter-clockwise, then mirror, so rows follow the scan."""
    if image.size != (preset.width, preset.height):
        raise ValueError(f"expected a {preset.width}x{preset.height} image, got {image.size}")
    if preset.colors not in PALETTES:
        raise ValueError(f"no WOLINK pixel format for {preset.colors} ({preset.key})")
    rotation = preset.extra.get("rotation", 0)
    if rotation:
        image = image.rotate(rotation, expand=True)
    if preset.extra.get("mirror_x"):
        image = ImageOps.mirror(image)
    if preset.extra.get("mirror_y"):
        image = ImageOps.flip(image)
    return image


def color_codes(image: Image.Image, colors: str) -> list[int]:
    """Nearest palette color of every pixel, row by row."""
    palette = [(code, RGB[code]) for code in PALETTES[colors]]
    nearest: dict[tuple[int, int, int], int] = {}

    def code_of(pixel: tuple[int, int, int]) -> int:
        code = nearest.get(pixel)
        if code is None:
            code = min(
                palette,
                key=lambda entry: sum((a - b) ** 2 for a, b in zip(pixel, entry[1], strict=True)),
            )[0]
            nearest[pixel] = code
        return code

    raw = image.convert("RGB").tobytes()
    return [code_of(pixel) for pixel in zip(raw[0::3], raw[1::3], raw[2::3], strict=True)]


def pack_2bpp(codes: list[int], width: int) -> bytes:
    """Four pixels per byte, first in the high bits; rows padded with white."""
    padding = [WHITE] * ((-width) % 4)
    out = bytearray()
    for start in range(0, len(codes), width):
        row = codes[start : start + width] + padding
        for i in range(0, len(row), 4):
            out.append(row[i] << 6 | row[i + 1] << 4 | row[i + 2] << 2 | row[i + 3])
    return bytes(out)


def pack_black_and_red(codes: list[int], width: int) -> bytes:
    """A black/white frame (1 = not black), then a red frame (1 = red)."""
    return pack_bits([code != BLACK for code in codes], width) + pack_bits(
        [code == RED for code in codes], width
    )


def pack_bits(bits: list[bool], width: int) -> bytes:
    """Eight pixels per byte, first in the high bit; rows padded with zeros."""
    padding = [False] * ((-width) % 8)
    out = bytearray()
    for start in range(0, len(bits), width):
        row = bits[start : start + width] + padding
        for i in range(0, len(row), 8):
            byte = 0
            for bit in row[i : i + 8]:
                byte = byte << 1 | bit
            out.append(byte)
    return bytes(out)
