"""PickSmart image payload: the picture in scan order, packed in the preset's format.

Formats (`extra["format"]`):
  planes   a white bit plane, then a red one on BWR
  lines    the planes cut into lines, each behind a 7-byte `75` header
  quicklz  the planes, QuickLZ compressed
  2bpp     four pixels per byte (00 black, 01 white, 10 yellow, 11 red)
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageOps

from .compression import compress

if TYPE_CHECKING:
    from ..base import DevicePreset

FORMATS = ("planes", "lines", "quicklz", "2bpp")
LINE_HEADER = 0x75


def encode_image(image: Image.Image, preset: DevicePreset) -> bytes:
    """The payload for `preset`."""
    scanned = scan_order(image, preset)
    masks = ColorMasks(scanned, invert=preset.extra.get("invert_luminance", False))
    format_ = preset.extra.get("format", "planes")
    if format_ == "2bpp":
        return pack_2bpp(masks)
    if format_ == "quicklz":
        # This firmware counts a pixel as red without looking at blue.
        planes = pack_bits(masks.white) + pack_bits(masks.red_loose)
        try:
            return compress(planes)
        except Exception:
            return planes
    white = pack_bits(masks.white)
    red = pack_bits(masks.red) if "R" in preset.colors else None
    if format_ == "lines":
        return line_blocks(white, red, lines=scanned.width, line_bytes=scanned.height // 8)
    return white + red if red is not None else white


def scan_order(image: Image.Image, preset: DevicePreset) -> Image.Image:
    """The picture on a white preset-sized canvas, turned and mirrored into the scan.

    A TFT panel takes half the columns at twice the rows. `rotation` is
    counter-clockwise, as PIL's `Image.rotate`; the mirrors apply after it.
    """
    canvas = Image.new("RGB", (preset.width, preset.height), "white")
    picture = image.convert("RGB")
    if picture.width > preset.width or picture.height > preset.height:
        picture = picture.crop((0, 0, preset.width, preset.height))
    canvas.paste(picture, (0, 0))
    extra = preset.extra
    if extra.get("tft"):
        canvas = canvas.resize(
            (preset.width // 2, preset.height * 2), resample=Image.Resampling.BICUBIC
        )
    if rotation := extra.get("rotation", 0):
        canvas = canvas.rotate(rotation, expand=True)
    if extra.get("mirror_x"):
        canvas = ImageOps.mirror(canvas)
    if extra.get("mirror_y"):
        canvas = ImageOps.flip(canvas)
    return canvas


class ColorMasks:
    """Per-pixel color tests as 0/255 masks; a channel counts as lit above 128."""

    def __init__(self, image: Image.Image, *, invert: bool) -> None:
        red, green, blue = (
            channel.point(lambda v: 255 if v > 128 else 0) for channel in image.split()
        )
        dark = [ImageChops.invert(channel) for channel in (red, green, blue)]
        lit_all = _all(red, green, blue)
        # An inverted panel sets the white bit for dark pixels.
        self.white = _all(*dark) if invert else lit_all
        self.red = _all(red, dark[1], dark[2])
        self.red_loose = _all(red, dark[1])
        self.yellow = _all(green, ImageChops.invert(lit_all))
        self.red_not_white = _all(red, ImageChops.invert(self.white))


def _all(*masks: Image.Image) -> Image.Image:
    result = masks[0]
    for mask in masks[1:]:
        result = ImageChops.darker(result, mask)
    return result


def pack_bits(mask: Image.Image) -> bytes:
    """Eight pixels per byte, first in the high bit, straight across rows."""
    flat = Image.frombytes("L", (mask.width * mask.height, 1), mask.tobytes())
    return flat.convert("1", dither=Image.Dither.NONE).tobytes()


def pack_2bpp(masks: ColorMasks) -> bytes:
    """Four pixels per byte straight across rows; a trailing partial byte is dropped.

    Yellow wins over red, red over white, white over black.
    """
    codes = Image.new("L", masks.white.size, 0)
    codes.paste(1, mask=masks.white)
    codes.paste(3, mask=masks.red_not_white)
    codes.paste(2, mask=masks.yellow)
    data = codes.tobytes()
    return bytes(
        a << 6 | b << 4 | c << 2 | d
        for a, b, c, d in zip(data[0::4], data[1::4], data[2::4], data[3::4], strict=False)
    )


def line_blocks(white: bytes, red: bytes | None, *, lines: int, line_bytes: int) -> bytes:
    """Total length (u32 little endian), then `lines` headed lines per plane."""
    out = bytearray(4)
    header = bytes((LINE_HEADER, line_bytes + 7, line_bytes, 0, 0, 0, 0))
    for plane in (white, red):
        if plane is None:
            continue
        for line in range(lines):
            out += header + plane[line * line_bytes : (line + 1) * line_bytes]
    struct.pack_into("<I", out, 0, len(out))
    return bytes(out)
