"""WOLINK wire formats: advertisement, unlock, commands, status, compression."""

from __future__ import annotations

import zlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import pytest

from custom_components.ble_esl.esl_ble.wolink.const import AES_KEY
from custom_components.ble_esl.esl_ble.wolink.protocol import (
    Advertisement,
    battery_plausible,
    compress,
    parse_advertisement,
    refresh_command,
    status_error,
    status_idle,
    unlock_response,
    write_data_command,
)


def decompress(payload: bytes) -> bytes:
    """Read a block-compressed picture back, checking every header field."""
    assert payload[:2] == b"\xa5\xa6"
    assert payload[3] == 0x02
    count, pos, out = payload[2], 4, b""
    for index in range(1, count + 1):
        assert payload[pos] == index
        size = int.from_bytes(payload[pos + 1 : pos + 3], "little")
        pos += 3
        inflate = zlib.decompressobj(-zlib.MAX_WBITS)
        out += inflate.decompress(payload[pos : pos + size]) + inflate.flush()
        pos += size
    assert pos == len(payload)
    return out


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # 2.9" BWR from discussion 55
        (
            "3000000e033003030b9d",
            Advertisement(0x3000, 0x000E, 0x0330, 0x0303, 2973),
        ),
        # 3.5" BWRY
        (
            "3000000e033002010b8b",
            Advertisement(0x3000, 0x000E, 0x0330, 0x0201, 2955),
        ),
    ],
)
def test_parse_advertisement(data, expected):
    assert parse_advertisement(bytes.fromhex(data)) == expected


def test_parse_advertisement_rejects_short_data():
    assert parse_advertisement(None) is None
    assert parse_advertisement(bytes(9)) is None


def test_battery_plausible():
    assert battery_plausible(3000)
    assert not battery_plausible(1400)
    assert not battery_plausible(4300)


def test_unlock_response_is_the_encrypted_nonce():
    nonce = bytes(range(16))
    decryptor = Cipher(algorithms.AES(AES_KEY), modes.ECB()).decryptor()
    assert decryptor.update(unlock_response(nonce)) + decryptor.finalize() == nonce


def test_commands_are_little_endian():
    assert write_data_command(0x01020304, b"\xaa") == bytes.fromhex("00a504030201aa")
    assert refresh_command(0x1234) == bytes.fromhex("02a534120000")


def test_status_frames():
    assert status_error(bytes([0x01, 0x02])) == 2
    assert status_error(bytes([0x01])) == 0
    assert status_idle(bytes([0x00, 0x00]))
    assert status_idle(bytes([0xFF, 0x00]))
    assert not status_idle(bytes([0x01, 0x00]))
    assert not status_idle(b"")


@pytest.mark.parametrize("size", [1, 8192, 8193, 17664, 96000])
def test_compress_round_trips(size):
    data = bytes((i * 7) % 256 for i in range(size))
    payload = compress(data)
    assert payload[2] == -(-size // 8192)  # one block per started 8 KiB
    assert decompress(payload) == data


def test_compress_rejects_empty_and_oversized_input():
    with pytest.raises(ValueError):
        compress(b"")
    with pytest.raises(ValueError):
        compress(bytes(8192 * 255 + 1))
