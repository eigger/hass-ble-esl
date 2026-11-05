"""Generate Home Assistant brand images for BLE ESL.

The artwork is an original geometric brand mark on a dark navy rounded square:
a centered electronic shelf label (e-paper display tag) with an off-white / light-gray
plastic housing bezel, crisp white e-paper screen, bold Bluetooth rune, and clean
tri-color display blocks. Drawn from geometric primitives at 4x scale and
downsampled, so no source image, external font file, or network access is needed.
Run with Pillow 12.3.0 for reproducible PNGs.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BRAND = Path(__file__).resolve().parents[1] / "custom_components/ble_esl/brand"
SIZE = 512
SCALE = 4
NAVY = "#1b2a41"
BEZEL = "#e2e8f0"  # Realistic ESL off-white / light slate plastic casing
WHITE = "#ffffff"  # E-paper display screen
CORAL = "#ef4444"  # Tri-color E-paper red accent
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
    hw = h * 0.30
    top = (cx, cy - hh)
    bot = (cx, cy + hh)
    ur = (cx + hw, cy - hh * 0.5)
    lr = (cx + hw, cy + hh * 0.5)
    ul = (cx - hw * 0.92, cy - hh * 0.46)
    ll = (cx - hw * 0.92, cy + hh * 0.46)
    _draw_thick_line(d, top, bot, width, fill)
    _draw_thick_line(d, top, ur, width, fill)
    _draw_thick_line(d, ur, ll, width, fill)
    _draw_thick_line(d, bot, lr, width, fill)
    _draw_thick_line(d, lr, ul, width, fill)


def draw_icon() -> Image.Image:
    """Draw the 512px RGBA app icon."""
    s = SCALE
    image = Image.new("RGBA", (SIZE * s, SIZE * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)

    def box(x0: float, y0: float, x1: float, y1: float) -> list[float]:
        return [x0 * s, y0 * s, x1 * s, y1 * s]

    # 1. Dark navy rounded square background.
    d.rounded_rectangle(box(0, 0, SIZE - 1, SIZE - 1), radius=104 * s, fill=NAVY)

    # 2. Centered ESL tag bezel (realistic light gray/off-white plastic casing) + inner E-Ink screen (white).
    d.rounded_rectangle(box(52, 112, 460, 400), radius=42 * s, fill=BEZEL)
    d.rounded_rectangle(box(80, 140, 432, 372), radius=24 * s, fill=WHITE)

    # 3. Bold, simple elements inside the E-Ink screen:
    # Left side: large Bluetooth rune in dark navy.
    _draw_bt_rune(d, cx=168 * s, cy=256 * s, h=148 * s, width=16 * s, fill=NAVY)

    # Right side: bold red E-Ink price/promo block + two thick navy bars.
    d.rounded_rectangle(box(248, 176, 396, 236), radius=14 * s, fill=CORAL)
    d.rounded_rectangle(box(248, 260, 396, 290), radius=10 * s, fill=NAVY)
    d.rounded_rectangle(box(248, 308, 352, 338), radius=10 * s, fill=NAVY)

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
