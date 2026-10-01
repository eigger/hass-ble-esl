"""ETAG palette conversion and padded black/red bitplanes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .const import PANELS

if TYPE_CHECKING:
    from ..base import DevicePreset

PALETTE = ((0, 0, 0), (255, 255, 255), (255, 0, 0))
BLACK, WHITE, RED = PALETTE


def encode_image(image: Image.Image, preset: DevicePreset) -> dict[str, tuple[bytes, bytes]]:
    """Both panels' (black, red) planes; the firmware read after connecting picks one."""
    colors = quantize(image, preset)
    return {panel: planes(colors, reverse) for panel, reverse in PANELS.items()}


def quantize(image: Image.Image, preset: DevicePreset) -> Image.Image:
    """The picture on its white background, every pixel one of the three panel colors."""
    size = (preset.width, preset.height)
    if image.size != size:
        raise ValueError(f"Expected {size[0]} x {size[1]} image, got {image.size}")
    flat = Image.new("RGBA", size, "white")
    flat.alpha_composite(image.convert("RGBA"))
    palette = Image.new("P", (1, 1))
    palette.putpalette(list(sum(PALETTE, ())) * 85 + [0, 0, 0])
    return flat.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB")


def planes(image: Image.Image, reverse: bool) -> tuple[bytes, bytes]:
    """APK a2.c.f/g/h: two MSB-first planes, one byte-aligned column after another.

    A black bit is 0 in the black plane, a red bit is 1 in the red plane. The
    standard scan pads the top of every column with black up to a whole byte;
    the reversed scan walks columns and rows backwards and pads the end.
    """
    width, height = image.size
    xs = range(width - 1, -1, -1) if reverse else range(width)
    ys = range(height - 1, -1, -1) if reverse else range(height)
    pad = [BLACK] * (-height % 8)
    black, red = bytearray(), bytearray()
    for x in xs:
        column = [image.getpixel((x, y)) for y in ys]
        if not reverse:
            column = pad + column
        for start in range(0, len(column), 8):
            bw, accent = 255, 0
            for bit, color in enumerate(column[start : start + 8]):
                if color == BLACK:
                    bw &= ~(128 >> bit)
                elif color == RED:
                    accent |= 128 >> bit
            black.append(bw)
            red.append(accent)
    return bytes(black), bytes(red)
