"""ETAG discovery, image framing and acknowledged packet transfer."""

import asyncio
import gc
from types import SimpleNamespace
from unittest.mock import AsyncMock

from blesession import SessionTrace
from PIL import Image
import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble.base import STAGE_MAP, WriteRefused
from custom_components.ble_esl.esl_ble.etag import writer
from custom_components.ble_esl.esl_ble.etag.devices import PRESETS
from custom_components.ble_esl.esl_ble.etag.image import encode
from custom_components.ble_esl.esl_ble.etag.wire import packets
from custom_components.ble_esl.esl_ble.etag.writer import EtagConnection


def test_etag_discovery_and_padding():
    info = SimpleNamespace(name="ETAG-52500058B6", manufacturer_data={}, service_uuids=[])
    protocol = esl_ble.detect(info)
    assert protocol.id == "etag"
    assert protocol.preset_for(None).height == 122
    image = Image.new("RGB", (250, 122), "white")
    black, red = encode(image, "SE0213NP61-TNG-A0")
    assert len(black) == len(red) == 4000
    assert black[:16] == b"\x03" + b"\xff" * 15
    assert red == b"\x00" * 4000
    assert len(list(packets(image, "SE0213NP61-TNG-A0"))) == 40


@pytest.mark.parametrize("rejected", [False, True])
async def test_transfer_checks_acknowledgements(rejected):
    callback = None
    char = SimpleNamespace(max_write_without_response_size=244)
    service = SimpleNamespace(get_characteristic=lambda uuid: char)
    client = SimpleNamespace(services=SimpleNamespace(get_service=lambda uuid: service))

    async def start_notify(characteristic, fn):
        nonlocal callback
        callback = fn

    async def write_gatt_char(characteristic, packet, response):
        command = packet[1]
        reply_command = {5: 6, 0x11: 0x12, 7: 8, 1: 2, 3: 4}[command]
        if command == 1:
            index = int.from_bytes(packet[3:5], "big")
            reply = b"\x91\x02" + index.to_bytes(2, "little") + bytes([int(rejected)]) + b"\x19"
        else:
            reply = bytes([0x91, reply_command, 0, 0x19])
        callback(char, reply)

    client.start_notify = start_notify
    client.write_gatt_char = AsyncMock(side_effect=write_gatt_char)
    progress = []
    connection = EtagConnection(client, "SE0213NP61-TNG-A0")
    if rejected:
        with pytest.raises(RuntimeError, match="rejected"):
            await connection.write(
                Image.new("RGB", (250, 122), "white"),
                timeout=1,
                log=[],
                progress=lambda n, total: progress.append(n),
            )
    else:
        await connection.write(
            Image.new("RGB", (250, 122), "white"),
            timeout=1,
            log=[],
            progress=lambda n, total: progress.append(n),
        )
        assert progress == list(range(1, 41))


def fake_tag(firmware=b"SE0213NP61-TNG-A0\x00", mtu_payload=244, service=True):
    """A client that acknowledges every ETAG packet."""
    callback = None
    char = SimpleNamespace(max_write_without_response_size=mtu_payload)
    gatt = SimpleNamespace(get_characteristic=lambda uuid: char)
    client = SimpleNamespace(
        services=SimpleNamespace(get_service=lambda uuid: gatt if service else None)
    )

    async def start_notify(characteristic, fn):
        nonlocal callback
        callback = fn

    async def write_gatt_char(characteristic, packet, response):
        command = packet[1]
        if command == 1:
            reply = b"\x91\x02" + packet[3:5][::-1] + b"\x00\x19"
        else:
            reply = bytes([0x91, {5: 6, 0x11: 0x12, 7: 8, 3: 4}[command], 0, 0x19])
        callback(char, reply)

    client.start_notify = start_notify
    client.write_gatt_char = AsyncMock(side_effect=write_gatt_char)
    client.read_gatt_char = AsyncMock(return_value=firmware)
    return client


async def _prepared(image):
    return writer.prepare(PRESETS["etag213"], image, "AA:BB:CC:DD:EE:FF")


async def test_write_session_times_stages_and_picks_firmware_orientation(monkeypatch):
    monkeypatch.setattr(writer.asyncio, "sleep", AsyncMock())
    client = fake_tag(b"SE0213MN50-TNG-A0")
    image = Image.new("RGB", (250, 122), "white")
    trace = SessionTrace(STAGE_MAP)
    result = await writer.write_session(
        client, "AA", PRESETS["etag213"], _prepared(image), pacing_s=0.05, trace=trace
    )
    assert result.success
    assert set(trace.timings) >= {"handshake", "transfer", "finish"}
    sent = [call.args[1] for call in client.write_gatt_char.await_args_list]
    assert sent == list(packets(image, "SE0213MN50-TNG-A0"))
    # Only the 36 image packets are paced; the final settle is 1 s.
    paced = [c.args[0] for c in writer.asyncio.sleep.await_args_list]
    assert paced.count(0.05) == 36


async def test_unsupported_firmware_is_refused_without_retry():
    client = fake_tag(b"SE0290XX00-TNG-A0")
    prepared = _prepared(None)
    with pytest.raises(WriteRefused):
        await writer.write_session(
            client, "AA", PRESETS["etag213"], prepared, trace=SessionTrace(STAGE_MAP)
        )
    prepared.close()  # refused before the encode was needed
    client.write_gatt_char.assert_not_awaited()


@pytest.mark.parametrize(
    ("kwargs", "match"), [({"service": False}, "missing"), ({"mtu_payload": 20}, "too small")]
)
async def test_link_problems_are_reported_clearly(kwargs, match):
    connection = EtagConnection(fake_tag(**kwargs), "SE0213NP61-TNG-A0")
    with pytest.raises(RuntimeError, match=match):
        await connection.write(
            Image.new("RGB", (250, 122), "white"), timeout=1, log=[], progress=lambda *_: None
        )


async def test_retry_reuses_the_prepared_encode_and_awaits_it_after_the_handshake(monkeypatch):
    """The integration awaits the same future on every attempt."""
    yield_once = asyncio.sleep  # writer.asyncio is this module; keep a real one
    monkeypatch.setattr(writer.asyncio, "sleep", AsyncMock())
    image = Image.new("RGB", (250, 122), "white")
    prepared = asyncio.get_running_loop().create_future()
    expected = list(packets(image, "SE0213NP61-TNG-A0"))
    for _ in range(2):
        client = fake_tag()
        if not prepared.done():
            # Not encoded yet: the handshake must still go out.
            task = asyncio.create_task(
                writer.write_session(
                    client, "AA", PRESETS["etag213"], prepared, trace=SessionTrace(STAGE_MAP)
                )
            )

            async def handshake_sent(client=client):
                while client.write_gatt_char.await_count < 3:
                    await yield_once(0)

            # Fails (rather than hangs) if the encode is awaited first again.
            await asyncio.wait_for(handshake_sent(), 1)
            prepared.set_result(writer.prepare(PRESETS["etag213"], image, "AA"))
            await task
        else:
            await writer.write_session(
                client, "AA", PRESETS["etag213"], prepared, trace=SessionTrace(STAGE_MAP)
            )
        assert [c.args[1] for c in client.write_gatt_char.await_args_list] == expected


@pytest.mark.parametrize(
    ("kwargs", "match"), [({"service": False}, "missing"), ({"mtu_payload": 20}, "too small")]
)
async def test_early_link_failure_closes_the_unused_encode(kwargs, match):
    """Run with -W error::RuntimeWarning: an unawaited coroutine would fail it."""
    client = fake_tag(**kwargs)
    prepared = asyncio.get_running_loop().create_future()
    with pytest.raises(RuntimeError, match=match):
        await writer.write_session(
            client, "AA", PRESETS["etag213"], prepared, trace=SessionTrace(STAGE_MAP)
        )
    prepared.cancel()
    gc.collect()


async def test_progress_total_is_known_during_the_handshake(monkeypatch):
    monkeypatch.setattr(writer.asyncio, "sleep", AsyncMock())
    seen = []
    image = Image.new("RGB", (250, 122), "white")

    async def prepared():
        return writer.prepare(PRESETS["etag213"], image, "AA")["SE0213NP61-TNG-A0"]

    await EtagConnection(fake_tag(), "SE0213NP61-TNG-A0").send(
        prepared(), progress=lambda n, total: seen.append(total)
    )
    assert seen == [40] * 40
