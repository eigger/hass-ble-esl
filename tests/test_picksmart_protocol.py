"""Tests for PickSmart command framing, packet sizing, and image encoding."""

from __future__ import annotations

import struct

from PIL import Image

from custom_components.ble_esl.esl_ble.picksmart.devices import PRESETS
from custom_components.ble_esl.esl_ble.picksmart.protocol import (
    encode_image,
    make_cmd_packet,
    make_size_packet,
)


def test_make_cmd_packets():
    """Verify wire framing of PickSmart command packets."""
    assert make_cmd_packet(0x01, 1000) == b"\x01"
    assert make_cmd_packet(0x03, 1000) == b"\x03"

    # 0x02 standard
    cmd_size = make_cmd_packet(0x02, 1000, compression2=False)
    assert len(cmd_size) == 8
    assert cmd_size[0] == 0x02
    assert struct.unpack_from("<I", cmd_size, 1)[0] == 1000

    # 0x02 compression2
    cmd_size_c2 = make_cmd_packet(0x02, 1000, compression2=True)
    assert len(cmd_size_c2) == 6
    assert cmd_size_c2[0] == 0x02
    assert struct.unpack_from("<I", cmd_size_c2, 1)[0] == 1000
    assert cmd_size_c2[5] == 0x01


def test_make_size_packet():
    """Verify 240-byte chunk packaging with part sequence header."""
    payload = bytes(range(256)) * 2  # 512 bytes -> 3 parts (240, 240, 32)
    p0 = make_size_packet(0, payload)
    assert len(p0) == 4 + 240
    assert struct.unpack_from("<I", p0, 0)[0] == 0
    assert p0[4:] == payload[:240]

    p2 = make_size_packet(2, payload)
    assert len(p2) == 4 + 32
    assert struct.unpack_from("<I", p2, 0)[0] == 2
    assert p2[4:] == payload[480:512]


def test_encode_image_presets():
    """Verify encoding images on BWR, BWRY, and compression2 presets."""
    img = Image.new("RGB", (296, 128), "white")

    # 0x0033: 2.9" BWR
    encoded_bwr = encode_image(img, PRESETS["0x0033"])
    assert len(encoded_bwr) > 0

    # 0x002E: 2.9" BWRY (4-color)
    encoded_bwry = encode_image(img, PRESETS["0x002E"])
    assert len(encoded_bwry) == (296 * 128) // 4

    # 0x008B: 10.2" BWR (compression2)
    img_102 = Image.new("RGB", (960, 640), "white")
    encoded_c2 = encode_image(img_102, PRESETS["0x008B"])
    assert len(encoded_c2) > 4
    # First 4 bytes are LE part2 length header
    part2_len = struct.unpack_from("<I", encoded_c2, 0)[0]
    assert part2_len > 0
