"""XTE image buffer tests: scan order and packing per palette."""

from __future__ import annotations

import dataclasses

from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.xte.devices import PRESETS
from custom_components.ble_esl.esl_ble.xte.image import (
    buffer_size,
    encode_image,
)
from custom_components.ble_esl.esl_ble.xte.wire import image_object

PSJ_420 = PRESETS["psj-420"]


def test_palette_and_bit_order():
    image = Image.new("RGB", (400, 300), "white")
    for x, color in enumerate(("black", "white", "yellow", "red")):
        image.putpixel((x, 0), Image.new("RGB", (1, 1), color).getpixel((0, 0)))
    assert encode_image(image, PSJ_420) == b"\x1b" + b"\x55" * 29999
    with pytest.raises(ValueError, match="400x300"):
        encode_image(Image.new("RGB", (300, 400)), PSJ_420)


def test_rows_pad_to_four_pixels_and_rotate_into_the_buffer():
    """A 250x122 as-viewed preset with a portrait buffer: 31-byte rows, 122x250."""
    portrait = dataclasses.replace(
        PSJ_420, key="t", width=250, height=122, extra={"device_number": 1, "rotation": 90}
    )
    assert buffer_size(portrait) == (122, 250)
    assert buffer_size(PSJ_420) == (400, 300)
    image = Image.new("RGB", (250, 122), "white")
    for x, color in enumerate(("white", "yellow", "red", "black", "black", "white")):
        image.putpixel((249, x), Image.new("RGB", (1, 1), color).getpixel((0, 0)))
    packed = encode_image(image, portrait)
    assert len(packed) == 31 * 250
    # Rotated 90 degrees counter-clockwise, the right-hand column becomes buffer row 0,
    # top pixel first; the two padded pixels pack as black.
    assert packed[:2] == bytes.fromhex("6c15")
    assert packed[2:30] == b"\x55" * 28
    assert packed[30] == 0x50  # 122 px: last byte holds 2 white pixels + 2 padded (black)
    assert packed[31:62] == b"\x55" * 30 + b"\x50"
    obj = image_object(packed, *buffer_size(portrait))
    assert obj[25:33] == (122).to_bytes(4, "big") + (250).to_bytes(4, "big")
    with pytest.raises(ValueError, match="250x122"):
        encode_image(Image.new("RGB", (122, 250)), portrait)
