"""PickSmart wire formats: commands, data parts, replies."""

from __future__ import annotations

import struct

from custom_components.ble_esl.esl_ble.picksmart.wire import (
    data_packet,
    image_command,
    is_done_reply,
    is_size_reply,
    is_start_reply,
    part_count,
    requested_part,
    size_command,
    start_command,
)


def test_commands():
    assert start_command() == b"\x01"
    assert image_command() == b"\x03"
    assert size_command(1000, quicklz=False) == b"\x02" + struct.pack("<I", 1000) + bytes(3)
    assert size_command(1000, quicklz=True) == b"\x02" + struct.pack("<I", 1000) + b"\x01"


def test_data_packets():
    payload = bytes(range(256)) * 2  # 512 bytes: parts of 240, 240, 32
    assert part_count(len(payload)) == 3
    assert data_packet(0, payload) == struct.pack("<I", 0) + payload[:240]
    assert data_packet(2, payload) == struct.pack("<I", 2) + payload[480:]
    assert data_packet(3, payload) == struct.pack("<I", 3)


def test_replies():
    assert is_start_reply(bytes.fromhex("01f400"))
    assert not is_start_reply(bytes.fromhex("01f4"))
    assert is_size_reply(b"\x02")
    assert not is_size_reply(b"")
    assert requested_part(bytes.fromhex("0500") + struct.pack("<I", 7)) == 7
    assert requested_part(bytes.fromhex("0500")) is None
    assert requested_part(bytes.fromhex("0508") + bytes(4)) is None
    assert is_done_reply(bytes.fromhex("0508"))
    assert not is_done_reply(bytes.fromhex("0500"))
