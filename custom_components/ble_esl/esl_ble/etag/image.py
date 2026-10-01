"""ETAG palette conversion and padded black/red bitplanes."""

from PIL import Image

from .const import PALETTE, PANELS, SIZE


def quantize(image):
    if image.size != SIZE:
        raise ValueError(f"Expected {SIZE[0]} x {SIZE[1]} image, got {image.size}")
    rgba = image.convert("RGBA")
    rgb = Image.new("RGBA", SIZE, "white")
    rgb.alpha_composite(rgba)
    palette = Image.new("P", (1, 1))
    palette.putpalette(list(sum(PALETTE, ())) * 85 + [0, 0, 0])
    return rgb.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).convert("RGB")


def encode(image, firmware):
    """APK a2.c.f/g/h: two MSB-first planes, padded per column."""
    image = quantize(image)
    black, red = bytearray(), bytearray()
    reverse = "SE0213MN50-TNG-A0" in firmware
    xs = range(249, -1, -1) if reverse else range(250)
    for x in xs:
        colors = [image.getpixel((x, y)) for y in (range(121, -1, -1) if reverse else range(122))]
        if not reverse:
            colors = [PALETTE[0]] * 6 + colors
        for start in range(0, len(colors), 8):
            bw, accent = 255, 0
            for bit, color in enumerate(colors[start : start + 8]):
                if color == PALETTE[0]:
                    bw &= ~(128 >> bit)
                elif color == PALETTE[2]:
                    accent |= 128 >> bit
            black.append(bw)
            red.append(accent)
    return bytes(black), bytes(red)


def encode_image(image, preset):
    """Both panels' planes; the firmware read after connecting picks one."""
    image = quantize(image)
    return {panel: encode(image, panel) for panel in PANELS}
