"""ETAG packet framing and reply checks, no hardware."""

import pytest

from custom_components.ble_esl.esl_ble.etag.wire import (
    HANDSHAKE,
    MAX_PACKET,
    REFRESH,
    EtagError,
    check_reply,
    frames,
    image_packet_count,
    image_packets,
)


def test_packet_counts_follow_the_panel_size():
    assert image_packet_count(250, 122) == 36
    planes = (bytes(4000), bytes(4000))
    assert len(list(image_packets(planes))) == 36
    assert len(list(frames(planes))) == len(HANDSHAKE) + 36 + len(REFRESH) == 40


def test_image_packet_layout():
    first = next(image_packets((bytes(range(10)), b"")))
    assert first == bytes.fromhex("ac01 00 0000 0001 000a") + bytes(range(10)) + b"\xca"
    assert max(len(p) for p in image_packets((bytes(4000),) * 2)) == MAX_PACKET == 240


def _ack(command, status=0):
    return bytes([0x91, command, status, 0x19])


@pytest.mark.parametrize("packet", HANDSHAKE + REFRESH)
def test_commands_accept_their_acknowledgement(packet):
    reply = {5: 6, 0x11: 0x12, 7: 8, 3: 4}[packet[1]]
    check_reply(packet, _ack(reply))


@pytest.mark.parametrize(
    ("reply", "match"),
    [
        (b"\x00\x06\x00\x19", "Unexpected response"),
        (b"\x91\x06\x00", "Unexpected response"),
        (_ack(9), "Expected response 06"),
        (_ack(6, 1), "Command rejected"),
    ],
)
def test_command_replies_are_checked(reply, match):
    with pytest.raises(EtagError, match=match):
        check_reply(HANDSHAKE[0], reply)


def test_version_reply_has_no_status_byte():
    check_reply(HANDSHAKE[2], _ack(8, 0x55))


def test_image_acknowledgement_names_the_packet_index_and_status():
    packet = next(image_packets((bytes(300), b"")))
    packet = packet[:3] + (1).to_bytes(2, "big") + packet[5:]
    check_reply(packet, b"\x91\x02\x01\x00\x00\x19")
    for reply in (b"\x91\x02\x02\x00\x00\x19", b"\x91\x02\x01\x00\x01\x19", b"\x91\x02\x19"):
        with pytest.raises(EtagError):
            check_reply(packet, reply)
