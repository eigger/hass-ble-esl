"""Generate Home Assistant brand images for BLE ESL.

The artwork is an original geometric brand mark on a dark navy rounded square:
a cyan and white electronic shelf label (e-paper display tag) with a tri-color
accent block, barcode bars, DataMatrix grid, and a golden Bluetooth badge with
wireless signal arcs. Drawn from geometric primitives at 4x scale and
downsampled, so no source image, external font file, or network access is
needed. Run with Pillow 12.3.0 for reproducible PNGs.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BRAND = Path(__file__).resolve().parents[1] / "custom_components/ble_esl/brand"
SIZE = 512
SCALE = 4
NAVY = "#1b2a41"
CYAN = "#38bdf8"
WHITE = "#ffffff"
YELLOW = "#ffd23f"
GOLD = "#f2a900"
CORAL = "#ef4444"
WORDMARK = "#0ea5e9"


def _draw_thick_line(
    d: ImageDraw.ImageDraw,
    p0: tuple[float, float],
    p1: tuple[float, float],
    width: float,
    fill: str,
) -> None:
    """Draw a line segment with round caps."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    r = width / 2.0
    if length > 0:
        nx, ny = -dy / length * r, dx / length * r
        d.polygon(
            [
                (x0 + nx, y0 + ny),
                (x1 + nx, y1 + ny),
                (x1 - nx, y1 - ny),
                (x0 - nx, y0 - ny),
            ],
            fill=fill,
        )
    d.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=fill)
    d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=fill)


def _draw_bt_rune(
    d: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    h: float,
    width: float,
    fill: str,
) -> None:
    """Draw a crisp geometric Bluetooth rune centered at (cx, cy)."""
    hh = h / 2.0
    hw = h * 0.29
    top = (cx, cy - hh)
    bot = (cx, cy + hh)
    ur = (cx + hw, cy - hh * 0.5)
    lr = (cx + hw, cy + hh * 0.5)
    ul = (cx - hw * 0.95, cy - hh * 0.48)
    ll = (cx - hw * 0.95, cy + hh * 0.48)
    _draw_thick_line(d, top, bot, width, fill)
    _draw_thick_line(d, top, ur, width, fill)
    _draw_thick_line(d, ur, ll, width, fill)
    _draw_thick_line(d, bot, lr, width, fill)
    _draw_thick_line(d, lr, ul, width, fill)


def _draw_arc_ring(
    d: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r_in: float,
    r_out: float,
    deg_start: float,
    deg_end: float,
    fill: str,
) -> None:
    """Draw a smooth annular sector."""
    steps = 48
    a0 = math.radians(deg_start)
    a1 = math.radians(deg_end)
    pts_out = [
        (
            cx + r_out * math.cos(a0 + (a1 - a0) * i / steps),
            cy + r_out * math.sin(a0 + (a1 - a0) * i / steps),
        )
        for i in range(steps + 1)
    ]
    pts_in = [
        (
            cx + r_in * math.cos(a0 + (a1 - a0) * i / steps),
            cy + r_in * math.sin(a0 + (a1 - a0) * i / steps),
        )
        for i in range(steps + 1)
    ]
    d.polygon(pts_out + list(reversed(pts_in)), fill=fill)


def draw_icon() -> Image.Image:
    """Draw the 512px RGBA app icon."""
    s = SCALE
    image = Image.new("RGBA", (SIZE * s, SIZE * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)

    def box(x0: float, y0: float, x1: float, y1: float) -> list[float]:
        return [x0 * s, y0 * s, x1 * s, y1 * s]

    # 1. Dark navy rounded square background.
    d.rounded_rectangle(box(0, 0, SIZE - 1, SIZE - 1), radius=104 * s, fill=NAVY)

    # 2. Outer ESL tag bezel (cyan) + inner E-Ink screen (white).
    d.rounded_rectangle(box(52, 136, 404, 420), radius=38 * s, fill=CYAN)
    d.rounded_rectangle(box(76, 160, 380, 396), radius=20 * s, fill=WHITE)

    # 3. E-Ink tri-color accent header & data layout on the screen.
    # Red/coral promo pill (classic BWR/BWY e-paper accent) + dark navy title bars.
    d.rounded_rectangle(box(98, 182, 172, 230), radius=10 * s, fill=CORAL)
    d.rounded_rectangle(box(188, 184, 272, 202), radius=6 * s, fill=NAVY)
    d.rounded_rectangle(box(188, 212, 252, 230), radius=6 * s, fill=NAVY)

    # Large price / metric block in navy.
    d.rounded_rectangle(box(98, 250, 260, 294), radius=8 * s, fill=NAVY)

    # Crisp vertical barcode bars along the bottom-left of the e-paper screen.
    barcode_x = [
        (98, 108),
        (116, 122),
        (130, 144),
        (152, 158),
        (166, 176),
        (184, 198),
        (206, 212),
        (220, 230),
        (238, 246),
        (254, 260),
    ]
    for x0, x1 in barcode_x:
        d.rounded_rectangle(box(x0, 316, x1, 372), radius=2 * s, fill=NAVY)

    # 2D QR / DataMatrix finder & cells on the bottom-right of the screen.
    d.rounded_rectangle(box(286, 268, 358, 372), radius=8 * s, fill=CYAN)
    d.rounded_rectangle(box(298, 280, 346, 328), radius=4 * s, fill=WHITE)
    d.rounded_rectangle(box(310, 292, 334, 316), radius=2 * s, fill=NAVY)
    d.rounded_rectangle(box(298, 340, 318, 360), radius=3 * s, fill=NAVY)
    d.rounded_rectangle(box(326, 340, 346, 360), radius=3 * s, fill=NAVY)

    # 4. Circular Bluetooth badge overlapping the top-right corner of the ESL tag
    #    with a dark-navy negative-space knockout ring.
    bcx, bcy = 356 * s, 168 * s
    d.ellipse([bcx - 72 * s, bcy - 72 * s, bcx + 72 * s, bcy + 72 * s], fill=NAVY)
    d.ellipse([bcx - 54 * s, bcy - 54 * s, bcx + 54 * s, bcy + 54 * s], fill=GOLD)
    _draw_bt_rune(d, bcx, bcy, h=64 * s, width=9 * s, fill=NAVY)

    # 5. Golden wireless signal arcs radiating from the top-right badge.
    for r_in, r_out, col in (
        (82 * s, 96 * s, YELLOW),
        (108 * s, 122 * s, GOLD),
    ):
        _draw_arc_ring(d, bcx, bcy, r_in, r_out, -68, 16, fill=col)

    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> None:
    """Write icon.png, icon@2x.png, logo.png and logo@2x.png."""
    BRAND.mkdir(parents=True, exist_ok=True)
    icon = draw_icon()
    icon.save(BRAND / "icon@2x.png", optimize=True)
    icon.resize((256, 256), Image.Resampling.LANCZOS).save(BRAND / "icon.png", optimize=True)

    # Pillow bundles Aileron Regular, so regeneration needs no system fonts.
    font = ImageFont.load_default(size=336)
    bounds = font.getbbox("BLE ESL")
    wordmark = Image.new("RGBA", (bounds[2] - bounds[0], bounds[3] - bounds[1]))
    ImageDraw.Draw(wordmark).text((-bounds[0], -bounds[1]), "BLE ESL", font=font, fill=WORDMARK)
    wordmark = wordmark.crop(wordmark.getbbox())
    gap = 96 + ((SIZE + 96 + wordmark.width) % 2)
    logo = Image.new("RGBA", (SIZE + gap + wordmark.width, SIZE))
    logo.alpha_composite(icon, (0, 0))
    logo.alpha_composite(wordmark, (SIZE + gap, (SIZE - wordmark.height) // 2))
    logo = logo.crop(logo.getbbox())
    logo.save(BRAND / "logo@2x.png", optimize=True)
    logo.resize((logo.width // 2, logo.height // 2), Image.Resampling.LANCZOS).save(
        BRAND / "logo.png", optimize=True
    )


if __name__ == "__main__":
    main()
