"""easyTag image payload: quantization, planes, run-length and raw blocks."""

from __future__ import annotations

import random
import struct

from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.esl_ble.easytag.devices import PRESETS
from custom_components.ble_esl.esl_ble.easytag.image import (
    BLACK,
    PALETTES,
    RED,
    WHITE,
    align8,
    encode_image,
    pack_bits,
    plane,
    quantize,
    raw_block,
    run_length,
    run_length_block,
)


def decode_run_length(data: bytes, count: int) -> list[int]:
    out: list[int] = []
    i = 0
    while len(out) < count:
        byte = data[i]
        i += 1
        if byte & 0x80:
            out += [(byte >> (6 - k)) & 1 for k in range(7)]
            continue
        value, length = (byte >> 6) & 1, byte & 0x3F
        if length == 1:
            length, i = data[i], i + 1
        elif length == 0:
            length, i = int.from_bytes(data[i : i + 2], "little"), i + 2
        out += [value] * length
    return out[:count]


@pytest.mark.parametrize(
    "bits",
    [[0] * 5, [1] * 20, [0] * 300, [1] * 70000, [0, 1, 1, 0, 1, 0, 0, 0, 1] * 40],
)
def test_run_length_round_trips(bits):
    assert decode_run_length(run_length(bits), len(bits)) == bits


def test_run_length_forms():
    assert run_length([1] * 10) == bytes([0x40 | 10])  # short run
    assert run_length([0] * 100) == bytes([0x01, 100])  # medium run
    assert run_length([1] * 300) == bytes([0x40]) + struct.pack("<H", 300)  # long run
    assert run_length([1, 0, 1]) == bytes([0x80 | 0b1010000])  # literal, padded


def test_blocks():
    bits = [1] * 64
    black = run_length_block(bits, 8, 8, red=False)
    red = run_length_block(bits, 8, 8, red=True)
    assert black[:13] == b"\xfc" + struct.pack(">HHHHI", 0, 0, 7, 7, len(run_length(bits)))
    assert red[:13] == b"\xfc" + struct.pack(">HHHHI", 0x8000, 0, 0x8007, 7, len(run_length(bits)))
    assert (
        raw_block(bits, 8, 8, red=False) == b"\xfe" + struct.pack(">HHHH", 0, 0, 7, 7) + b"\xff" * 8
    )
    assert raw_block(bits, 8, 8, red=True)[0] == 0x03


def test_plane_pads_to_multiples_of_8():
    codes = [BLACK, RED, WHITE] * 3  # 3x3
    black = plane(codes, 3, 3, BLACK)
    assert len(black) == 64
    assert black[:8] == [1, 0, 0, 0, 0, 0, 0, 0]
    assert pack_bits(plane(codes, 3, 3, RED))[:3] == bytes([0x40, 0x40, 0x40])


def test_encode_picks_the_shorter_container():
    p = PRESETS["3D"]
    flat = encode_image(Image.new("RGB", (p.width, p.height), "white"), p)
    assert flat[0] == 0xFC  # long runs: run-length wins
    rng = random.Random(3)
    noise = Image.new("RGB", (p.width, p.height))
    noise.putdata(
        [rng.choice([(0, 0, 0), (250, 250, 250), (230, 0, 0)]) for _ in range(p.width * p.height)]
    )
    assert encode_image(noise, p)[0] == 0xFE  # no runs: raw wins


def test_encode_rejects_unknown_palette_and_size():
    p = DevicePreset(key="x", display_name="x", width=8, height=8, colors="BWRY")
    with pytest.raises(ValueError, match="palette"):
        encode_image(Image.new("RGB", (8, 8)), p)
    with pytest.raises(ValueError, match="296x128"):
        encode_image(Image.new("RGB", (8, 8)), PRESETS["3D"])


def test_quantize_matches_a_plain_reference():
    """Column-major Floyd-Steinberg, floored shares, clamp per update, no 3/16 onto row 0."""

    def reference(pixels, width, height, palette, dither):
        px = [[list(pixels[x][y]) for y in range(height)] for x in range(width)]
        codes = [0] * (width * height)
        for x in range(width):
            for y in range(height):
                c = px[x][y]
                best = min(
                    range(len(palette)),
                    key=lambda n: sum((c[k] - palette[n][k]) ** 2 for k in range(3)),
                )
                codes[y * width + x] = best
                if not dither:
                    continue
                for k in range(3):
                    err = c[k] - palette[best][k]
                    targets = []
                    if y + 1 < height:
                        targets.append((x, y + 1, 7))
                    if x + 1 < width:
                        if y - 1 > 0:
                            targets.append((x + 1, y - 1, 3))
                        targets.append((x + 1, y, 5))
                        if y + 1 < height:
                            targets.append((x + 1, y + 1, 1))
                    for nx, ny, share in targets:
                        px[nx][ny][k] = max(0, min(255, px[nx][ny][k] + (err * share >> 4)))
        return codes

    rng = random.Random(7)
    for width, height in ((37, 29), (64, 16), (25, 12)):
        pixels = [
            [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(height)]
            for _ in range(width)
        ]
        image = Image.new("RGB", (width, height))
        image.putdata([pixels[x][y] for y in range(height) for x in range(width)])
        for colors, palette in PALETTES.items():
            for dither in (True, False):
                assert quantize(image, colors, dither=dither) == reference(
                    pixels, width, height, palette, dither
                ), (width, height, colors, dither)


def test_align8():
    assert [align8(v) for v in (1, 8, 122, 128)] == [8, 8, 128, 128]
