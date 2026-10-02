"""WOLINK image buffers: scan order and packing per palette."""

from __future__ import annotations

from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.esl_ble.wolink.devices import PRESETS, _preset
from custom_components.ble_esl.esl_ble.wolink.image import (
    BLACK,
    RED,
    RGB,
    WHITE,
    YELLOW,
    color_codes,
    encode_image,
    pack_2bpp,
    pack_bits,
    scan_order,
)


def preset(width, height, colors="BWRY", **extra):
    return DevicePreset(
        key="t", display_name="t", width=width, height=height, colors=colors, extra=extra
    )


def solid(p, color):
    return Image.new("RGB", (p.width, p.height), color)


def test_2bpp_codes():
    """00 black, 01 white, 10 yellow, 11 red, first pixel in the high bits."""
    p = preset(4, 1)
    image = Image.new("RGB", (4, 1))
    image.putdata([RGB[BLACK], RGB[WHITE], RGB[YELLOW], RGB[RED]])
    assert encode_image(image, p) == bytes([0b00011011])


def test_2bpp_rows_pad_with_white():
    assert pack_2bpp([BLACK] * 6, 6) == bytes([0x00, 0b00000101])


def test_bwr_is_black_frame_then_red_frame():
    """Black/white frame: 1 = not black (red counts as white). Red frame: 1 = red."""
    p = preset(8, 1, "BWR")
    image = Image.new("RGB", (8, 1), "white")
    image.putpixel((0, 0), RGB[BLACK])
    image.putpixel((7, 0), RGB[RED])
    assert encode_image(image, p) == bytes([0b01111111, 0b00000001])


def test_bits_rows_pad_with_zero():
    assert pack_bits([True] * 10, 10) == bytes([0xFF, 0b11000000])


def test_nearest_palette_color():
    image = Image.new("RGB", (3, 1))
    image.putdata([(20, 10, 10), (250, 240, 30), (200, 30, 20)])
    assert color_codes(image, "BWRY") == [BLACK, YELLOW, RED]
    assert color_codes(image, "BWR") == [BLACK, WHITE, RED]


def test_pixel_format_follows_colors():
    white_bwr = encode_image(solid(PRESETS["290-bwr"], "white"), PRESETS["290-bwr"])
    frame = 296 * 128 // 8
    assert white_bwr == b"\xff" * frame + bytes(frame)
    white_bwry = encode_image(solid(PRESETS["290"], "white"), PRESETS["290"])
    assert white_bwry == b"\x55" * (296 * 128 // 4)
    with pytest.raises(ValueError, match="pixel format"):
        encode_image(Image.new("RGB", (8, 1)), preset(8, 1, "BW"))


def test_image_must_match_the_preset():
    with pytest.raises(ValueError, match="296x128"):
        encode_image(Image.new("RGB", (10, 10)), PRESETS["290"])


def test_213_rows_are_padded():
    """250x122 turned 270 degrees: 250 rows of 122 pixels, 31 bytes each."""
    assert len(encode_image(solid(PRESETS["213"], "white"), PRESETS["213"])) == 250 * 31


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_rotation_is_counter_clockwise_like_pil(rotation):
    image = Image.new("RGB", (5, 3))
    image.putdata([(i, i, i) for i in range(15)])
    scanned = scan_order(image, preset(5, 3, rotation=rotation))
    assert scanned.tobytes() == image.rotate(rotation, expand=True).tobytes()


@pytest.mark.parametrize(
    ("extra", "first"),
    [
        ({"rotation": 0}, (0, 0)),
        ({"rotation": 0, "mirror_x": True}, (3, 0)),
        ({"rotation": 0, "mirror_y": True}, (0, 1)),
        ({"rotation": 90}, (3, 0)),
        ({"rotation": 180}, (3, 1)),
        ({"rotation": 270}, (0, 1)),
        ({"rotation": 270, "mirror_x": True}, (0, 0)),
    ],
)
def test_first_buffer_pixel(extra, first):
    """Which source pixel of a 4x2 picture lands in byte 0, bit 7."""
    image = Image.new("RGB", (4, 2), "black")
    image.putpixel(first, RGB[WHITE])
    packed = encode_image(image, preset(4, 2, "BWR", **extra))
    assert packed[0] & 0x80
    assert sum(bin(byte).count("1") for byte in packed[: len(packed) // 2]) == 1


@pytest.mark.parametrize(
    ("key", "corner"),
    [("290-bwr", (0, 127)), ("370", (415, 239))],
)
def test_first_buffer_pixel_with_led_top_left(key, corner):
    p = PRESETS[key]
    image = Image.new("RGB", (p.width, p.height), "black")
    image.putpixel(corner, RGB[RED])
    packed = encode_image(image, p)
    if p.colors == "BWR":
        packed = packed[len(packed) // 2 :]  # the red frame
        assert packed[0] == 0x80
    else:
        assert packed[0] >> 6 == RED


def test_preset_rejects_unknown_rotation():
    with pytest.raises(ValueError, match="rotation"):
        _preset("x", "x", 8, 8, rotation=45)
