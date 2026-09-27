"""PickSmart image payload: scan order and the four payload formats."""

from __future__ import annotations

import dataclasses
import struct

from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.picksmart.compression import decompress
from custom_components.ble_esl.esl_ble.picksmart.devices import PRESETS, _preset
from custom_components.ble_esl.esl_ble.picksmart.image import encode_image, scan_order

BLACK, WHITE, RED, YELLOW = (0, 0, 0), (255, 255, 255), (255, 0, 0), (255, 255, 0)


def preset(width, height, colors="BWR", **extra):
    base = {"rotation": 0, "mirror_x": False, "mirror_y": False, "encoding": "planes"}
    return dataclasses.replace(
        PRESETS["0x004B"], key="t", width=width, height=height, colors=colors, extra=base | extra
    )


def row(*colors):
    image = Image.new("RGB", (len(colors), 1))
    image.putdata(list(colors))
    return image


def test_planes_are_white_then_red():
    image = row(WHITE, BLACK, RED, WHITE, BLACK, BLACK, BLACK, RED)
    assert encode_image(image, preset(8, 1)) == bytes([0b10010000, 0b00100001])
    assert encode_image(image, preset(8, 1, "BW")) == bytes([0b10010000])


def test_black_plane_marks_black_pixels():
    image = row(WHITE, BLACK, RED, WHITE, BLACK, BLACK, BLACK, RED)
    assert encode_image(image, preset(8, 1, black_plane=True))[0] == 0b01001110


def test_2bpp_codes_and_priority():
    """00 black, 01 white, 10 yellow, 11 red; a light red or yellow still counts."""
    image = row(BLACK, WHITE, YELLOW, RED, (200, 40, 40), (200, 200, 60), WHITE, WHITE)
    assert encode_image(image, preset(8, 1, "BWRY", encoding="2bpp")) == bytes(
        [0b00011011, 0b11100101]
    )


def test_lines_prefix_every_line_with_a_header():
    p = preset(16, 8, encoding="lines")
    payload = encode_image(Image.new("RGB", (16, 8), "white"), p)
    # 16 lines of one byte per plane, two planes.
    assert struct.unpack_from("<I", payload)[0] == len(payload) == 4 + 2 * 16 * 8
    assert payload[4:12] == bytes([0x75, 8, 1, 0, 0, 0, 0, 0xFF])


def test_quicklz_decompresses_to_the_planes():
    p = PRESETS["0x008B"]
    image = Image.new("RGB", (p.width, p.height), "white")
    image.putpixel((0, 0), RED)
    planes = decompress(encode_image(image, p))
    frame = p.width * p.height // 8
    assert len(planes) == 2 * frame
    assert planes[0] == 0x7F and planes[frame] == 0x80


def test_scan_order():
    p = preset(4, 2, rotation=90, mirror_x=True)
    image = Image.new("RGB", (4, 2), "white")
    image.putpixel((3, 0), BLACK)
    scanned = scan_order(image, p)
    assert scanned.size == (2, 4)
    assert scanned.getpixel((1, 0)) == BLACK  # turned to (0, 0), then mirrored


def test_small_picture_sits_top_left_on_white():
    scanned = scan_order(Image.new("RGB", (2, 2), "black"), preset(4, 4))
    assert scanned.getpixel((1, 1)) == BLACK and scanned.getpixel((3, 3)) == WHITE


def test_resample_before_turning():
    """The 2.1" TFT is scaled to 125x264, then turned 90 degrees."""
    p = PRESETS["0x00A0"]
    assert p.extra["resample"] == (125, 264)
    scanned = scan_order(Image.new("RGB", (p.width, p.height), "white"), p)
    assert scanned.size == (264, 125)


def test_bwry_presets_use_2bpp():
    p = PRESETS["0x002E"]
    assert p.extra["encoding"] == "2bpp"
    white = encode_image(Image.new("RGB", (p.width, p.height), "white"), p)
    assert white == b"\x55" * (p.width * p.height // 4)


def test_unknown_encoding_is_rejected():
    with pytest.raises(ValueError, match="encoding"):
        _preset(0x1234, "x", 8, 8, "BWR", encoding="rle")
