"""Generate the BLE ESL brand images (icon / logo, light + dark).

Usage: python docs/brand/generate.py custom_components/ble_esl/brand
"""
from PIL import Image, ImageDraw, ImageFont
import sys
import os

OUT = sys.argv[1]
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "custom_components", "ble_esl", "fonts")
FONT_BOLD = os.path.join(FONT_DIR, "GmarketSansTTFBold.ttf")
FONT_MED = os.path.join(FONT_DIR, "GmarketSansTTFMedium.ttf")
SS = 4  # supersample

LIGHT = dict(body=(31, 41, 55), screen=(243, 244, 246), ink=(31, 41, 55),
             text=(17, 24, 39), sub=(107, 114, 128))
DARK = dict(body=(229, 231, 235), screen=(31, 41, 55), ink=(229, 231, 235),
            text=(243, 244, 246), sub=(156, 163, 175))
RED = (220, 38, 38)
YEL = (245, 158, 11)
BT = (0, 130, 252)
WHITE = (255, 255, 255)


def draw_tag(d, x, y, s, c):
    """Draw an ESL tag icon inside an s×s box at (x, y). Coordinates already supersampled."""
    # tag body: landscape rounded rect, centered
    # badge overhangs the body's top-right corner, so keep body + badge inside the box
    br = s * 0.17
    bw, bh = s * 0.86, s * 0.66
    bx = x + (s - bw) / 2 - br * 0.22
    by = y + (s - bh) / 2 + br * 0.15
    r = s * 0.10
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=r, fill=c["body"])
    # screen inset
    m = s * 0.075
    sx0, sy0, sx1, sy1 = bx + m, by + m, bx + bw - m, by + bh - m
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=r * 0.45, fill=c["screen"])
    # content: a bold "price" bar and two thin lines, plus BWRY color chips
    pad = s * 0.065
    lh = s * 0.075
    # thick bar
    d.rounded_rectangle([sx0 + pad, sy0 + pad, sx0 + pad + (sx1 - sx0) * 0.55, sy0 + pad + lh * 1.5],
                        radius=lh * 0.4, fill=c["ink"])
    # thin lines
    ly = sy0 + pad + lh * 1.5 + pad * 0.9
    d.rounded_rectangle([sx0 + pad, ly, sx0 + pad + (sx1 - sx0) * 0.70, ly + lh * 0.7],
                        radius=lh * 0.35, fill=c["ink"])
    ly2 = ly + lh * 0.7 + pad * 0.7
    d.rounded_rectangle([sx0 + pad, ly2, sx0 + pad + (sx1 - sx0) * 0.42, ly2 + lh * 0.7],
                        radius=lh * 0.35, fill=c["ink"])
    # color chips (red / yellow) bottom-right of screen
    chip = lh * 1.1
    cy = sy1 - pad - chip
    d.rounded_rectangle([sx1 - pad - chip * 2.3, cy, sx1 - pad - chip * 1.3, cy + chip], radius=chip * 0.25, fill=RED)
    d.rounded_rectangle([sx1 - pad - chip, cy, sx1 - pad, cy + chip], radius=chip * 0.25, fill=YEL)
    # bluetooth badge, top-right, overlapping corner
    bcx, bcy = bx + bw - br * 0.55, by + br * 0.55
    d.ellipse([bcx - br, bcy - br, bcx + br, bcy + br], fill=BT)
    draw_bt_rune(d, bcx, bcy, br * 0.95, WHITE, max(2, int(s * 0.024)))


def draw_bt_rune(d, cx, cy, h, color, w):
    """Bluetooth rune centered at (cx, cy) with total height h."""
    hh = h / 2
    hw = h * 0.30
    top, bot = (cx, cy - hh), (cx, cy + hh)
    ur, lr = (cx + hw, cy - hh / 2), (cx + hw, cy + hh / 2)
    ul, ll = (cx - hw, cy - hh / 2), (cx - hw, cy + hh / 2)
    d.line([top, bot], fill=color, width=w)
    d.line([top, ur, ll], fill=color, width=w, joint="curve")
    d.line([bot, lr, ul], fill=color, width=w, joint="curve")
    for p in (top, bot, ur, lr, ul, ll):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=color)


def icon(size, c, name):
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    draw_tag(d, 0, 0, S, c)
    im = im.resize((size, size), Image.LANCZOS)
    im.save(os.path.join(OUT, name))


def fit_font(d, path, text, max_w, start):
    size = start
    while size > 8:
        f = ImageFont.truetype(path, size)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= max_w:
            return f, bb
        size -= 2
    return f, bb


def logo(w, h, c, name):
    W, H = w * SS, h * SS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = H  # icon box = full height
    draw_tag(d, 0, 0, s, c)
    tx = s * 1.12
    max_w = W - tx - H * 0.05
    big, sub = "BLE ESL", "Electronic Shelf Label for Home Assistant"
    f_big, bb = fit_font(d, FONT_BOLD, big, max_w, int(H * 0.50))
    f_small, sb = fit_font(d, FONT_MED, sub, max_w, int(H * 0.15))
    bh, sh = bb[3] - bb[1], sb[3] - sb[1]
    gap = H * 0.08
    total = bh + gap + sh
    y0 = (H - total) / 2
    d.text((tx - bb[0], y0 - bb[1]), big, font=f_big, fill=c["text"])
    d.text((tx - sb[0], y0 + bh + gap - sb[1]), sub, font=f_small, fill=c["sub"])
    im = im.resize((w, h), Image.LANCZOS)
    im.save(os.path.join(OUT, name))


icon(256, LIGHT, "icon.png")
icon(512, LIGHT, "icon@2x.png")
icon(256, DARK, "dark_icon.png")
icon(512, DARK, "dark_icon@2x.png")
logo(712, 180, LIGHT, "logo.png")
logo(1424, 360, LIGHT, "logo@2x.png")
logo(712, 180, DARK, "dark_logo.png")
logo(1424, 360, DARK, "dark_logo@2x.png")
print("ok")
