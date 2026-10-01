"""ETAG bitplanes: palette, column padding and the two panel orientations."""

from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.esl_ble.etag.const import PANELS
from custom_components.ble_esl.esl_ble.etag.devices import PRESETS
from custom_components.ble_esl.esl_ble.etag.image import encode_image, quantize

PRESET = PRESETS["etag213"]
NP61, MN50 = "SE0213NP61-TNG-A0", "SE0213MN50-TNG-A0"


def test_white_image_pads_the_top_of_every_column():
    black, red = encode_image(Image.new("RGB", (250, 122), "white"), PRESET)[NP61]
    assert len(black) == len(red) == 4000
    assert black[:16] == b"\x03" + b"\xff" * 15  # six black padding rows, then white
    assert red == b"\x00" * 4000


def test_reversed_panel_starts_from_the_opposite_corner():
    image = Image.new("RGB", (250, 122), "white")
    image.putpixel((249, 121), (0, 0, 0))
    image.putpixel((0, 0), (255, 0, 0))
    planes = encode_image(image, PRESET)
    assert planes[MN50][0][0] == 0x7F  # first byte holds (249, 121), the black pixel
    assert planes[MN50][1][-1] == 0x40  # last byte holds (0, 0) as bit 6 of the two-row tail
    assert planes[NP61][0][-1] == 0xFE  # (249, 121) is the last bit of the last byte
    assert len(planes[MN50][0]) == len(planes[MN50][1]) == 4000


def test_quantize_snaps_to_the_panel_palette_and_flattens_alpha():
    image = Image.new("RGBA", (250, 122), (0, 0, 0, 0))
    image.putpixel((0, 0), (230, 20, 20, 255))
    out = quantize(image, PRESET)
    assert out.getpixel((0, 0)) == (255, 0, 0)
    assert out.getpixel((1, 0)) == (255, 255, 255)


def test_size_follows_the_preset():
    preset = DevicePreset("t", "T", 296, 128, "BWR")
    planes = encode_image(Image.new("RGB", (296, 128), "white"), preset)
    assert {len(p) for pair in planes.values() for p in pair} == {296 * 16}
    assert set(planes) == set(PANELS)


def test_wrong_size_is_rejected():
    with pytest.raises(ValueError, match="250 x 122"):
        encode_image(Image.new("RGB", (122, 250)), PRESET)
