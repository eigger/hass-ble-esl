"""easyTag image payload: palette planes, run-length or raw, whichever is shorter."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from ..base import DevicePreset

BLACK, WHITE, RED = 0, 1, 2
PALETTES = {
    "BW": ((0, 0, 0), (250, 250, 250)),
    "BWR": ((0, 0, 0), (250, 250, 250), (230, 0, 0)),
}
RED_FLAG = 0x8000


def encode_image(image: Image.Image, preset: DevicePreset) -> bytes:
    """The image payload for `preset`: a black plane, plus a red plane on BWR."""
    if preset.colors not in PALETTES:
        raise ValueError(f"no easyTag palette for {preset.colors} ({preset.key})")
    if image.size != (preset.width, preset.height):
        raise ValueError(f"expected a {preset.width}x{preset.height} image, got {image.size}")
    codes = quantize(image, preset.colors, dither=preset.extra.get("dither", True))
    width, height = align8(preset.width), align8(preset.height)
    black = plane(codes, preset.width, preset.height, BLACK)
    red = plane(codes, preset.width, preset.height, RED) if preset.colors == "BWR" else None
    runs = run_length_block(black, width, height, red=False)
    raw = raw_block(black, width, height, red=False)
    if red is not None:
        runs += run_length_block(red, width, height, red=True)
        raw += raw_block(red, width, height, red=True)
    return runs if len(runs) <= len(raw) else raw


def align8(value: int) -> int:
    return (value + 7) & ~7


def quantize(image: Image.Image, colors: str, *, dither: bool) -> list[int]:
    """Nearest palette color per pixel (row by row), with Floyd-Steinberg error diffusion.

    The diffusion walks columns (x outer, y inner) and so pushes 7/16 down,
    3/16 up-right, 5/16 right and 1/16 down-right. Shares are floored
    (`>> 4`) and each neighbour is clamped to 0..255 as it is updated; the
    up-right share never lands on row 0. Ties go to the earlier palette entry.
    """
    palette = PALETTES[colors]
    width, height = image.size
    columns = image.convert("RGB").transpose(Image.Transpose.TRANSPOSE).tobytes()
    reds, greens, blues = (list(columns[c::3]) for c in range(3))
    codes = [0] * (width * height)

    def spread(values: list[int], i: int, error: int, right: bool, below: bool, up: bool) -> None:
        if below:
            v = values[i + 1] + (error * 7 >> 4)
            values[i + 1] = 0 if v < 0 else 255 if v > 255 else v
        if right:
            j = i + height
            if up:
                v = values[j - 1] + (error * 3 >> 4)
                values[j - 1] = 0 if v < 0 else 255 if v > 255 else v
            v = values[j] + (error * 5 >> 4)
            values[j] = 0 if v < 0 else 255 if v > 255 else v
            if below:
                v = values[j + 1] + (error >> 4)
                values[j + 1] = 0 if v < 0 else 255 if v > 255 else v

    nearest: dict[tuple[int, int, int], int] = {}
    for x in range(width):
        right = x + 1 < width
        for y in range(height):
            i = x * height + y
            pixel = (reds[i], greens[i], blues[i])
            code = nearest.get(pixel)
            if code is None:
                code = min(range(len(palette)), key=lambda n: _distance(pixel, palette[n]))
                nearest[pixel] = code
            codes[y * width + x] = code
            if not dither:
                continue
            below, up = y + 1 < height, y - 1 > 0
            level = palette[code]
            if error := pixel[0] - level[0]:
                spread(reds, i, error, right, below, up)
            if error := pixel[1] - level[1]:
                spread(greens, i, error, right, below, up)
            if error := pixel[2] - level[2]:
                spread(blues, i, error, right, below, up)
    return codes


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def plane(codes: list[int], width: int, height: int, color: int) -> list[int]:
    """1 where the pixel is `color`, on a canvas padded to multiples of 8 (padding 0)."""
    row_padding = [0] * (align8(width) - width)
    bits: list[int] = []
    for start in range(0, width * height, width):
        bits += [1 if code == color else 0 for code in codes[start : start + width]]
        bits += row_padding
    return bits + [0] * (align8(width) * (align8(height) - height))


def run_length_block(bits: list[int], width: int, height: int, *, red: bool) -> bytes:
    """`FC`, origin, bottom-right corner (red flagged in bit 15), length, run-length data."""
    data = run_length(bits)
    flag = RED_FLAG if red else 0
    return (
        b"\xfc" + struct.pack(">HHHHI", flag, 0, flag | (height - 1), width - 1, len(data)) + data
    )


def raw_block(bits: list[int], width: int, height: int, *, red: bool) -> bytes:
    """`FE` (black) or `03` (red), origin, bottom-right corner, eight pixels per byte."""
    command = b"\x03" if red else b"\xfe"
    return command + struct.pack(">HHHH", 0, 0, height - 1, width - 1) + pack_bits(bits)


def pack_bits(bits: list[int]) -> bytes:
    """Eight pixels per byte, first pixel in the high bit."""
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = byte << 1 | bit
        out.append(byte)
    return bytes(out)


def run_length(bits: list[int]) -> bytes:
    """Runs of one bit value, or seven literal pixels when a run is shorter than 7.

    Literal: `1 p0..p6`. Run of 7-31: `0 v nnnnnn`. Run of 32-255: `0 v 000001`
    and a length byte. Longer (up to 65535): `0 v 000000` and a u16 little
    endian length.
    """
    out = bytearray()
    total, i = len(bits), 0
    while i < total:
        value = bits[i]
        run = 1
        while i + run < total and bits[i + run] == value and run < 0xFFFF:
            run += 1
        if run < 7:
            literal = bits[i : i + 7] + [0] * max(0, i + 7 - total)
            byte = 0x80
            for position, bit in enumerate(literal):
                byte |= bit << (6 - position)
            out.append(byte)
            i += 7
        elif run <= 31:
            out.append(value << 6 | run)
            i += run
        elif run <= 255:
            out += bytes((value << 6 | 1, run))
            i += run
        else:
            out.append(value << 6)
            out += struct.pack("<H", run)
            i += run
    return bytes(out)
