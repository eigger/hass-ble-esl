"""XTE image buffer: the picture in the panel's scan order, 2 bits per pixel."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

    from ..base import DevicePreset

# 2-bit pixel values.
BLACK, WHITE, YELLOW, RED = 0, 1, 2, 3
RGB = {BLACK: (0, 0, 0), WHITE: (255, 255, 255), YELLOW: (255, 255, 0), RED: (255, 0, 0)}
PALETTES = {"BWRY": (BLACK, WHITE, YELLOW, RED)}


def encode_image(image: Image.Image, preset: DevicePreset) -> bytes:
    """Packed buffer rows for `preset`, each padded to a multiple of 4 pixels."""
    if preset.colors not in PALETTES:
        raise ValueError(f"no XTE palette for {preset.colors} ({preset.key})")
    scanned = scan_order(image, preset)
    return pack_2bpp(color_codes(scanned, preset.colors), scanned.width)


def buffer_size(preset: DevicePreset) -> tuple[int, int]:
    """Buffer width and height: the preset's, swapped when the panel is turned 90 or 270."""
    if preset.extra.get("rotation", 0) % 180:
        return preset.height, preset.width
    return preset.width, preset.height


def scan_order(image: Image.Image, preset: DevicePreset) -> Image.Image:
    """Turn `rotation` degrees counter-clockwise so rows follow the panel's scan."""
    if image.size != (preset.width, preset.height):
        raise ValueError(f"XTE requires a {preset.width}x{preset.height} image")
    rotation = preset.extra.get("rotation", 0)
    return image.rotate(rotation, expand=True) if rotation else image


def color_codes(image: Image.Image, colors: str) -> list[int]:
    """Nearest palette color of every pixel, row by row; ties go to the lower code."""
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
    """Four pixels per byte, first in the high bits; rows padded with black."""
    padding = [BLACK] * ((-width) % 4)
    out = bytearray()
    for start in range(0, len(codes), width):
        row = codes[start : start + width] + padding
        for i in range(0, len(row), 4):
            out.append(row[i] << 6 | row[i + 1] << 4 | row[i + 2] << 2 | row[i + 3])
    return bytes(out)
