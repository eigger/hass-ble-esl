"""Minew MTag15 palette conversion for previews."""

from PIL import Image

from .const import PALETTE, SIZE


def encode_image(image, preset):
    if image.size != SIZE:
        raise ValueError(f"Expected {SIZE[0]} x {SIZE[1]} image, got {image.size}")
    rgba = Image.new("RGBA", SIZE, "white")
    rgba.alpha_composite(image.convert("RGBA"))
    palette = Image.new("P", (1, 1))
    palette.putpalette(list(sum(PALETTE, ())) * 64)
    return rgba.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB")
