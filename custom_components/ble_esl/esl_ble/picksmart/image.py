"""PickSmart image payload: the picture in scan order, packed in the preset's encoding.

Encodings (`extra["encoding"]`):
  planes   a white bit plane (a black one with `black_plane`), then a red one on BWR
  lines    the planes cut into lines, each behind a 7-byte `75` header
  quicklz  the planes, QuickLZ compressed
  2bpp     four pixels per byte (00 black, 01 white, 10 yellow, 11 red)
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageOps

from . import quicklz

if TYPE_CHECKING:
    from ..base import DevicePreset

ENCODINGS = ("planes", "lines", "quicklz", "2bpp")
LINE_HEADER = 0x75


def encode_image(image: Image.Image, preset: DevicePreset) -> bytes:
    """The payload for `preset`."""
    scanned = scan_order(image, preset)
    masks = ColorMasks(scanned)
    encoding = preset.extra.get("encoding", "planes")
    if encoding == "2bpp":
        return pack_2bpp(masks)
    first = pack_bits(masks.black if preset.extra.get("black_plane") else masks.white)
    if encoding == "quicklz":
        # This firmware counts a pixel as red without looking at blue.
        planes = first + pack_bits(masks.red_loose)
        try:
            return quicklz.compress(planes)
        except Exception:
            return planes
    red = pack_bits(masks.red) if "R" in preset.colors else None
    if encoding == "lines":
        return line_blocks(first, red, lines=scanned.width, line_bytes=scanned.height // 8)
    return first + red if red is not None else first


def scan_order(image: Image.Image, preset: DevicePreset) -> Image.Image:
    """The picture on a white preset-sized canvas, resampled, turned and mirrored into the scan.

    `resample` is the (width, height) the canvas is scaled to first (the 2.1"
    TFT takes half the columns at twice the rows). `rotation` is counter-
    clockwise, as PIL's `Image.rotate`; the mirrors apply after it.
    """
    canvas = Image.new("RGB", (preset.width, preset.height), "white")
    picture = image.convert("RGB")
    if picture.width > preset.width or picture.height > preset.height:
        picture = picture.crop((0, 0, preset.width, preset.height))
    canvas.paste(picture, (0, 0))
    extra = preset.extra
    if size := extra.get("resample"):
        canvas = canvas.resize(tuple(size), resample=Image.Resampling.BICUBIC)
    if rotation := extra.get("rotation", 0):
        canvas = canvas.rotate(rotation, expand=True)
    if extra.get("mirror_x"):
        canvas = ImageOps.mirror(canvas)
    if extra.get("mirror_y"):
        canvas = ImageOps.flip(canvas)
    return canvas


class ColorMasks:
    """Per-pixel color tests as 0/255 masks; a channel counts as lit above 128."""

    def __init__(self, image: Image.Image) -> None:
        red, green, blue = (
            channel.point(lambda v: 255 if v > 128 else 0) for channel in image.split()
        )
        dark = [ImageChops.invert(channel) for channel in (red, green, blue)]
        self.white = _all(red, green, blue)
        self.black = _all(*dark)
        self.red = _all(red, dark[1], dark[2])
        self.red_loose = _all(red, dark[1])
        self.yellow = _all(green, ImageChops.invert(self.white))
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


def line_blocks(first: bytes, red: bytes | None, *, lines: int, line_bytes: int) -> bytes:
    """Total length (u32 little endian), then `lines` headed lines per plane."""
    out = bytearray(4)
    header = bytes((LINE_HEADER, line_bytes + 7, line_bytes, 0, 0, 0, 0))
    for plane in (first, red):
        if plane is None:
            continue
        for line in range(lines):
            out += header + plane[line * line_bytes : (line + 1) * line_bytes]
    struct.pack_into("<I", out, 0, len(out))
    return bytes(out)
