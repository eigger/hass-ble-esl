"""Tests for XTE BLE session writer, chunking, and pacing."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from blesession import SessionTrace
from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.xte.const import NOTIFY_UUID, SERVICE_UUID, WRITE_UUID
from custom_components.ble_esl.esl_ble.xte.devices import PRESETS
from custom_components.ble_esl.esl_ble.xte.protocol import blocks, command, image_object
from custom_components.ble_esl.esl_ble.xte.writer import XteError, XteSession, prepare

PSJ_420 = PRESETS["psj-420"]
MAC = "AA:BB:CC:DD:EE:FF"


def _client(client, pacing_s=0.0):
    session = XteSession(client, MAC, pacing_s=pacing_s)
    session.settle_s = 0  # Keep unit tests fast; the settle is asserted separately.
    return session


class FakeClient:
    def __init__(self, reply="ok", mtu_payload=244, fail_write=False):
        self.write_char = SimpleNamespace(
            properties=["write-without-response"], max_write_without_response_size=mtu_payload
        )
        self.notify_char = SimpleNamespace(properties=["notify"])
        self.service = SimpleNamespace(
            get_characteristic=lambda uuid: {
                WRITE_UUID: self.write_char,
                NOTIFY_UUID: self.notify_char,
            }.get(uuid)
        )
        self.services = SimpleNamespace(
            get_service=lambda uuid: self.service if uuid == SERVICE_UUID else None
        )
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
            reply[5] = sum(reply[6 : reply[4]]) & 255
        elif self.reply == "length":
            reply[4] = 17
        self.callback(None, reply)


@pytest.mark.parametrize("write_limit", [20, 182, 244, 514])
def test_transport_sequence(write_limit):
    client = FakeClient(mtu_payload=write_limit)
    image = Image.new("RGB", (400, 300), "white")
    trace = SessionTrace()
    asyncio.run(_client(client).send(prepare(PSJ_420, image, MAC), trace=trace))
    obj = image_object(b"\x55" * 30000, 400, 300)
    expected = [command(b"\x01" + len(obj).to_bytes(4, "big"))]
    chunk_size = min(244, write_limit)
    assert trace.facts["chunk_size"] == chunk_size
    assert trace.facts["bytes"] == len(obj)
    assert {"settle_s", "parts"} <= trace.facts.keys()
    assert list(trace.timings) == ["handshake", "transfer", "finish"]
    for block in blocks(obj):
        expected.extend(block[i : i + chunk_size] for i in range(0, len(block), chunk_size))
    expected.append(command(b"\x04\x00"))
    assert client.writes == expected
    assert b"".join(client.writes[1:-1]) == b"".join(blocks(obj))
    assert client.stopped


@pytest.mark.parametrize(
    "reply,error",
    [
        ("checksum", XteError),
        ("status", XteError),
        ("length", XteError),
        ("timeout", TimeoutError),
    ],
)
def test_bad_responses_fail_and_unsubscribe(reply, error):
    client = FakeClient(reply=reply)
    transport = _client(client)
    transport.reply_timeout_s = 0.01
    with pytest.raises(error):
        asyncio.run(transport.send(prepare(PSJ_420, Image.new("RGB", (400, 300)), MAC)))
    assert client.stopped
    assert len(client.writes) == 1  # No data sent after a failed preparation.


def test_invalid_write_size_and_missing_service():
    client = FakeClient(mtu_payload=0)
    with pytest.raises(XteError, match="write-without-response size"):
        asyncio.run(_client(client).send(prepare(PSJ_420, Image.new("RGB", (400, 300)), MAC)))
    assert client.writes == []
    client.services.get_service = lambda uuid: None
    with pytest.raises(XteError, match="service missing"):
        asyncio.run(_client(client).send(prepare(PSJ_420, Image.new("RGB", (400, 300)), MAC)))


def test_write_failure_unsubscribes():
    client = FakeClient(fail_write=True)
    with pytest.raises(OSError):
        asyncio.run(_client(client).send(prepare(PSJ_420, Image.new("RGB", (400, 300)), MAC)))
    assert client.stopped


def test_write_failure_after_disconnect_keeps_original_error():
    client = FakeClient(fail_write=True)
    original = client.write_gatt_char

    async def write_then_drop(characteristic, data, response):
        client.is_connected = False
        await original(characteristic, data, response)

    client.write_gatt_char = write_then_drop
    with pytest.raises(OSError, match="adapter write failed"):
        asyncio.run(_client(client).send(prepare(PSJ_420, Image.new("RGB", (400, 300)), MAC)))
    assert not client.stopped  # stop_notify skipped on a dropped link


def test_settle_then_pacing_per_frame_not_per_chunk(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    client = FakeClient(mtu_payload=20)
    asyncio.run(
        XteSession(client, MAC, pacing_s=0.05).send(
            prepare(PSJ_420, Image.new("RGB", (400, 300), "white"), MAC)
        )
    )
    frames = 2 + len(blocks(image_object(b"\x55" * 30000, 400, 300)))
    # One settle after start_notify, then the pacing once per XTE frame.
    assert sleeps == [pytest.approx(0.5)] + [pytest.approx(0.05)] * frames
