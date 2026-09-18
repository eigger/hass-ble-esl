"""Tests for easyTag protocol codec, framing, CRC-16/CMS, RLE, and image quantization."""

from __future__ import annotations

from PIL import Image

from custom_components.ble_esl.esl_ble.easytag.const import (
    KEY_INDEX_CONFIG,
    KEY_INDEX_IMAGE,
    KEY_INDEX_NOTIFY,
    PACKET_LEN,
)
from custom_components.ble_esl.esl_ble.easytag.protocol import (
    build_image_frames,
    build_status_frames,
    compress_rle,
    crc16,
    decompress_rle,
    encode_image,
    mac_xor,
    packet_count,
    parse_notify,
    quantize_image,
    xor_key,
)

MAC = "3D:00:00:E5:7D:76"


def test_crc16_cms():
    """Verify CRC-16/CMS standard check value."""
    assert crc16(b"123456789") == 0xAEE7
    assert crc16(b"") == 0xFFFF


def test_xor_key_derivation():
    """Verify XOR key calculation from MAC and table index."""
    assert mac_xor(MAC) == 0xD3
    assert xor_key(MAC, KEY_INDEX_IMAGE) == 0xE2
    assert xor_key(MAC, KEY_INDEX_NOTIFY) == 0xB1


def test_packet_count_calculation():
    """Verify packet count formula ((len + 201) // 200)."""
    assert packet_count(0) == 1
    assert packet_count(1) == 1
    assert packet_count(199) == 2  # (199 + 201) // 200 = 2
    assert packet_count(200) == 2
    assert packet_count(400) == 3


def test_rle_compression_roundtrip():
    """Verify RLE compression and decompression roundtrip."""
    w, h = 296, 128
    plane = [1 if (x // 37 + y // 16) % 3 == 0 else 0 for y in range(h) for x in range(w)]
    compressed = compress_rle(plane)
    decompressed = decompress_rle(compressed, len(plane))
    assert decompressed[: len(plane)] == plane


def test_image_frames_and_obfuscation_roundtrip():
    """Verify building and unpacking image frames."""
    w, h = 296, 128
    plane = [0] * (w * h)
    payload = encode_image(plane, [0] * (w * h), w, h)
    assert payload[0] in (0xFC, 0xFE)

    frames = build_image_frames(MAC, payload)
    k = xor_key(MAC, KEY_INDEX_IMAGE)

    # Validate header frame (frame 0)
    hdr = bytearray(b ^ k for b in frames[0])
    hdr[9] ^= k  # byte 9 was clear
    assert hdr[0] == 0xFF
    assert hdr[1] == 0xFC
    assert bytes(hdr[2:9]) == b"easyTag"
    assert hdr[9] == KEY_INDEX_IMAGE
    assert bytes(hdr[16:18]) == b"BT"
    assert int.from_bytes(hdr[10:14], "big") == len(payload)
    assert int.from_bytes(hdr[14:16], "big") == len(frames) - 1
    assert crc16(bytes(hdr), 18) == int.from_bytes(hdr[18:20], "big")

    # Validate data packets
    recovered = bytearray()
    for seq, f in enumerate(frames[1:], 1):
        assert len(f) == PACKET_LEN
        p = bytes(b ^ k for b in f)
        assert int.from_bytes(p[0:2], "big") == seq
        assert crc16(p, 202) == int.from_bytes(p[202:204], "big")
        recovered += p[2:202]

    assert bytes(recovered[: len(payload)]) == payload


def test_status_frames():
    """Verify status query (0xF0) frame building."""
    sf = build_status_frames(MAC)
    k = xor_key(MAC, KEY_INDEX_CONFIG)
    hs = bytearray(b ^ k for b in sf[0])
    hs[9] ^= k
    assert hs[1] == 0xF0
    assert hs[9] == KEY_INDEX_CONFIG
    assert int.from_bytes(hs[10:14], "big") == 1
    assert int.from_bytes(hs[14:16], "big") == 1
    assert crc16(bytes(hs), 18) == int.from_bytes(hs[18:20], "big")
    assert bytes(b ^ k for b in sf[1])[2] == 0x00


def test_parse_notify():
    """Verify parsing notify response frame for battery and signed temperature."""
    plain = bytearray(20)
    plain[2] = 30  # 30 decivolts = 3.0 V = 3000 mV
    plain[3] = 256 - 5  # -5 °C
    kn = xor_key(MAC, KEY_INDEX_NOTIFY)
    frame = bytes(b ^ kn for b in plain)

    parsed = parse_notify(MAC, frame)
    assert parsed["battery_v"] == 3.0
    assert parsed["battery_mv"] == 3000
    assert parsed["temperature_c"] == -5


def test_quantize_image():
    """Verify quantizing PIL image to 8-aligned bitplanes."""
    img = Image.new("RGB", (10, 10), "white")
    pixels = img.load()
    pixels[0, 0] = (0, 0, 0)
    pixels[1, 0] = (255, 0, 0)

    bw, red = quantize_image(img, 10, 10, colors="BWR", dither=False)
    assert len(bw) == 16 * 16  # 10 aligned to 8 -> 16
    assert red is not None
    assert bw[0] == 1  # Black pixel
    assert red[1] == 1  # Red pixel
