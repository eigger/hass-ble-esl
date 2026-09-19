"""Codec and transport checks without a BLE adapter or Home Assistant."""

import asyncio
from types import SimpleNamespace

from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.poshiji.const import NOTIFY_UUID, SERVICE_UUID, WRITE_UUID
from custom_components.ble_esl.esl_ble.poshiji.devices import PSJ_420
from custom_components.ble_esl.esl_ble.poshiji.protocol import (
    encode_rle,
    is_psj420_advertisement,
    make_blocks,
    make_command,
    make_image_object,
    pack_pixels,
)
from custom_components.ble_esl.esl_ble.poshiji.writer import XteClient, prepare


@pytest.mark.parametrize("tail", [0x1E, 0x1B, 0x00, 0xFF])
def test_advertisement_variable_tail(tail):
    assert is_psj420_advertisement(bytes.fromhex("fd024002009964060102ffff") + bytes([tail]))


@pytest.mark.parametrize("data", [
    None, b"", bytes.fromhex("fd024002009964060102ffff"),
    bytes.fromhex("fd024002009964060102ffff1b00"),
    bytes.fromhex("fd024003009964060102ffff1b"),
])
def test_advertisement_rejects_other_signatures(data):
    assert not is_psj420_advertisement(data)


def test_rle_boundaries():
    assert encode_rle(b"") == b""
    assert encode_rle(b"\x55" * 256 + b"\xaa" * 2) == bytes.fromhex("ff55015502aa")
    raw = bytes(range(256)) * 120
    encoded = encode_rle(raw)
    assert b"".join(bytes([v]) * n for n, v in zip(encoded[::2], encoded[1::2], strict=True)) == raw


def test_palette_and_bit_order():
    image = Image.new("RGB", (400, 300), "white")
    for x, color in enumerate(("black", "white", "yellow", "red")):
        image.putpixel((x, 0), Image.new("RGB", (1, 1), color).getpixel((0, 0)))
    assert pack_pixels(image) == b"\x1b" + b"\x55" * 29999
    with pytest.raises(ValueError, match="400x300"):
        pack_pixels(Image.new("RGB", (300, 400)))


def test_image_header_and_half_frame_run_boundary():
    obj = make_image_object(b"\xaa" * 30000)
    # Each independently encoded 15000-byte half is 58*255 + 210 bytes.
    encoded_half = bytes.fromhex("ffaa") * 58 + bytes.fromhex("d2aa")
    assert obj[38:] == encoded_half * 2
    assert obj[:4] == b"XTEK"
    assert int.from_bytes(obj[4:8], "big") == sum(obj[12:])
    assert int.from_bytes(obj[8:12], "big") == len(obj)
    assert obj[12:25] == bytes.fromhex("01000000110000000000000000")
    assert obj[25:34] == bytes.fromhex("000001900000012c01")
    assert int.from_bytes(obj[34:38], "big") == 236
    with pytest.raises(ValueError):
        make_image_object(b"\x00")


def test_control_commands_from_capture():
    assert make_command(b"\x01" + (10244).to_bytes(4, "big")) == bytes.fromhex("585445010b2d0100002804")
    assert make_command(b"\x04\x00") == bytes.fromhex("5854450108040400")


def test_blocks_and_worst_case_size():
    obj = bytes(range(256)) * 40 + b"test"
    blocks = make_blocks(obj)
    assert len(blocks) == 9
    assert [len(b) for b in blocks] == [1220] * 8 + [565]
    assert b"".join(b[9:] for b in blocks) == obj
    for i, block in enumerate(blocks):
        assert block[:4] == b"XTE\x02"
        assert int.from_bytes(block[4:6], "big") == len(block)
        assert block[6] == sum(block[7:]) & 255
        assert block[7:9] == bytes((9, i))
    raw = (bytes(range(256)) * 118)[:30000]
    assert len(make_image_object(raw)) == 60038
    assert len(make_blocks(make_image_object(raw))) == 50


def _client(client, **kwargs):
    transport = XteClient(client, **kwargs)
    transport.settle = 0  # Keep unit tests fast; the settle is asserted separately.
    return transport


class FakeClient:
    def __init__(self, reply="ok", mtu_payload=244, fail_write=False):
        self.write_char = SimpleNamespace(properties=["write-without-response"], max_write_without_response_size=mtu_payload)
        self.notify_char = SimpleNamespace(properties=["notify"])
        self.service = SimpleNamespace(get_characteristic=lambda uuid: {
            WRITE_UUID: self.write_char, NOTIFY_UUID: self.notify_char
        }.get(uuid))
        self.services = SimpleNamespace(get_service=lambda uuid: self.service if uuid == SERVICE_UUID else None)
        self.reply = reply
        self.fail_write = fail_write
        self.writes = []
        self.stopped = False
        self.is_connected = True

    async def start_notify(self, characteristic, callback):
        assert characteristic is self.notify_char
        self.callback = callback

    async def stop_notify(self, characteristic):
        assert characteristic is self.notify_char
        if not self.is_connected:
            raise OSError("Not connected")
        self.stopped = True

    async def write_gatt_char(self, characteristic, data, response):
        assert characteristic is self.write_char and response is False
        assert len(data) <= min(244, self.write_char.max_write_without_response_size)
        self.writes.append(data)
        if self.fail_write:
            raise OSError("adapter write failed")
        if not data.startswith(b"XTE\x01") or self.reply == "timeout":
            return
        if data[6] == 1:
            reply = bytearray.fromhex("5854450409bd01ffbd00000000000000")
        else:
            reply = bytearray.fromhex("58544504080304ff0000000000000000")
        if self.reply == "checksum":
            reply[5] ^= 1
        elif self.reply == "status":
            reply[7] = 0
            reply[5] = sum(reply[6:reply[4]]) & 255
        elif self.reply == "length":
            reply[4] = 17
        self.callback(None, reply)


@pytest.mark.parametrize("write_limit", [20, 182, 244, 514])
def test_transport_sequence(write_limit):
    client = FakeClient(mtu_payload=write_limit)
    image = Image.new("RGB", (400, 300), "white")
    assert asyncio.run(_client(client).write_object(prepare(PSJ_420, image, "")))
    obj = make_image_object(b"\x55" * 30000)
    expected = [make_command(b"\x01" + len(obj).to_bytes(4, "big"))]
    chunk_size = min(244, write_limit)
    for block in make_blocks(obj):
        expected.extend(block[i:i + chunk_size] for i in range(0, len(block), chunk_size))
    expected.append(make_command(b"\x04\x00"))
    assert client.writes == expected
    assert b"".join(client.writes[1:-1]) == b"".join(make_blocks(obj))
    assert client.stopped


@pytest.mark.parametrize("reply,error", [
    ("checksum", ValueError), ("status", ValueError),
    ("length", ValueError), ("timeout", TimeoutError),
])
def test_bad_responses_fail_and_unsubscribe(reply, error):
    client = FakeClient(reply=reply)
    transport = _client(client)
    transport.timeout = 0.01
    with pytest.raises(error):
        asyncio.run(transport.write_object(prepare(PSJ_420, Image.new("RGB", (400, 300)), "")))
    assert client.stopped
    assert len(client.writes) == 1  # No data sent after a failed preparation.


def test_invalid_write_size_and_missing_service():
    client = FakeClient(mtu_payload=0)
    with pytest.raises(ValueError, match="write-without-response size"):
        asyncio.run(_client(client).write_object(prepare(PSJ_420, Image.new("RGB", (400, 300)), "")))
    assert client.writes == []
    client.services.get_service = lambda uuid: None
    with pytest.raises(ValueError, match="service missing"):
        asyncio.run(_client(client).write_object(prepare(PSJ_420, Image.new("RGB", (400, 300)), "")))


def test_write_failure_unsubscribes():
    client = FakeClient(fail_write=True)
    with pytest.raises(OSError):
        asyncio.run(_client(client).write_object(prepare(PSJ_420, Image.new("RGB", (400, 300)), "")))
    assert client.stopped


def test_write_failure_after_disconnect_keeps_original_error():
    client = FakeClient(fail_write=True)
    original = client.write_gatt_char

    async def write_then_drop(characteristic, data, response):
        client.is_connected = False
        await original(characteristic, data, response)

    client.write_gatt_char = write_then_drop
    with pytest.raises(OSError, match="adapter write failed"):
        asyncio.run(_client(client).write_object(prepare(PSJ_420, Image.new("RGB", (400, 300)), "")))
    assert not client.stopped  # stop_notify skipped on a dropped link


def test_settle_then_delay_per_frame_not_per_chunk(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    client = FakeClient(mtu_payload=20)
    assert asyncio.run(XteClient(client, attempt=2).write_object(prepare(PSJ_420, Image.new("RGB", (400, 300), "white"), "")))
    frames = 2 + len(make_blocks(make_image_object(b"\x55" * 30000)))
    # One settle after start_notify, then one retry delay per XTE frame.
    assert sleeps == [pytest.approx(0.5)] + [pytest.approx(0.05)] * frames

