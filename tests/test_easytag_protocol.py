"""easyTag frames: header, packets, CRC, obfuscation, reply."""

from __future__ import annotations

import pytest

from custom_components.ble_esl.esl_ble.easytag.const import KEY_INDEX_IMAGE, KEY_INDEX_REPLY
from custom_components.ble_esl.esl_ble.easytag.protocol import (
    Reply,
    crc16,
    image_frames,
    obfuscate,
    packet_count,
    parse_reply,
    session_key,
)

MAC = "E0:11:22:33:44:5A"


def test_crc16_cms():
    assert crc16(b"123456789") == 0xAEE7
    assert crc16(b"") == 0xFFFF


def test_session_key():
    """MAC bytes XORed together, then '1' (index 98) or 'b' (index 0)."""
    mac_xor = 0xE0 ^ 0x11 ^ 0x22 ^ 0x33 ^ 0x44 ^ 0x5A
    assert session_key(MAC, KEY_INDEX_IMAGE) == mac_xor ^ ord("1")
    assert session_key(MAC, KEY_INDEX_REPLY) == mac_xor ^ ord("b")


@pytest.mark.parametrize(("size", "count"), [(0, 1), (1, 1), (199, 2), (200, 2), (400, 3)])
def test_packet_count(size, count):
    assert packet_count(size) == count


def test_image_frames():
    payload = bytes(range(256)) * 2
    frames = image_frames(MAC, payload)
    key = session_key(MAC, KEY_INDEX_IMAGE)

    header = obfuscate(frames[0], key, keep=9)
    assert len(header) == 20
    assert header[:2] == b"\xff\xfc"
    assert header[2:9] == b"easyTag"
    assert header[9] == KEY_INDEX_IMAGE and frames[0][9] == KEY_INDEX_IMAGE  # sent in the clear
    assert int.from_bytes(header[10:14], "big") == len(payload)
    assert int.from_bytes(header[14:16], "big") == len(frames) - 1 == packet_count(len(payload))
    assert header[16:18] == b"BT"
    assert int.from_bytes(header[18:20], "big") == crc16(header[:18])

    recovered = b""
    for number, frame in enumerate(frames[1:], start=1):
        packet = obfuscate(frame, key)
        assert len(packet) == 204
        assert int.from_bytes(packet[:2], "big") == number
        assert int.from_bytes(packet[202:], "big") == crc16(packet[:202])
        recovered += packet[2:202]
    assert recovered[: len(payload)] == payload
    assert recovered[len(payload) :] == bytes(len(recovered) - len(payload))


def test_parse_reply():
    key = session_key(MAC, KEY_INDEX_REPLY)
    plain = bytes([0, 0, 30, 0xFB]) + bytes(16)  # 3.0 V, -5 °C
    assert parse_reply(MAC, obfuscate(plain, key)) == Reply(battery_mv=3000, temperature_c=-5)
    assert parse_reply(MAC, b"\x00\x01\x02") is None
