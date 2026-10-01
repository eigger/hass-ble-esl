"""ETAG session against a scripted tag: handshake, acknowledged packets, refresh."""

import asyncio
import gc
from types import SimpleNamespace
from unittest.mock import AsyncMock

from blesession import NotificationTimeout, SessionDropped, SessionTrace, session as session_mod
from blesession.testing import FakeClient
from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.base import STAGE_MAP, WriteRefused
from custom_components.ble_esl.esl_ble.etag import writer
from custom_components.ble_esl.esl_ble.etag.devices import PRESETS
from custom_components.ble_esl.esl_ble.etag.image import encode_image
from custom_components.ble_esl.esl_ble.etag.wire import (
    EtagError,
    frames,
)

REAL_SLEEP = asyncio.sleep
PRESET = PRESETS["etag213"]
NP61 = "SE0213NP61-TNG-A0"
REPLY = {5: 6, 0x11: 0x12, 7: 8, 3: 4}


class Char:
    def __init__(self, mtu):
        self.max_write_without_response_size = mtu


class FakeTag(FakeClient):
    """Acknowledges every packet, as the verified NP61 tag does."""

    def __init__(
        self,
        firmware=b"SE0213NP61-TNG-A0\x00",
        mtu=244,
        service=True,
        silent_after=None,
        image_status=0,
    ):
        super().__init__()
        char = Char(mtu)
        gatt = SimpleNamespace(get_characteristic=lambda uuid: char)
        self.services = SimpleNamespace(get_service=lambda uuid: gatt if service else None)
        self.firmware = firmware
        self.silent_after = silent_after
        self.image_status = image_status
        self.written = []

    async def read_gatt_char(self, uuid):
        return self.firmware

    async def write_gatt_char(self, characteristic, data, response=False):
        await super().write_gatt_char(characteristic, data, response)
        self.written.append(bytes(data))
        if self.silent_after is not None and len(self.written) > self.silent_after:
            return
        command = data[1]
        if command == 1:
            self.reply(b"\x91\x02" + data[3:5][::-1] + bytes([self.image_status]) + b"\x19")
        else:
            self.reply(bytes([0x91, REPLY[command], 0, 0x19]))


def _trace():
    return SessionTrace(STAGE_MAP)


async def _prepared(image=None):
    image = image or Image.new("RGB", (250, 122), "white")
    return writer.prepare(PRESET, image, "AA")


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(writer.asyncio, "sleep", sleep)
    return sleep


async def test_session_times_stages_and_sends_the_panel_packets(fast):
    client = FakeTag(b"SE0213MN50-TNG-A0")
    image = Image.new("RGB", (250, 122), "white")
    image.putpixel((3, 4), (0, 0, 0))
    trace = _trace()
    result = await writer.write_session(
        client, "AA", PRESET, _prepared(image), pacing_s=0.05, trace=trace
    )
    assert result.success
    assert list(trace.timings) == ["handshake", "transfer", "finish"]
    assert trace.facts["firmware"] == "SE0213MN50-TNG-A0"
    assert trace.facts["parts"] == 40
    assert client.written == list(frames(encode_image(image, PRESET)["SE0213MN50-TNG-A0"]))
    assert client.subscribed == {}  # unsubscribed again
    # Only the 36 image packets are paced; the refresh then settles for a second.
    sleeps = [call.args[0] for call in fast.await_args_list]
    assert sleeps.count(0.05) == 36
    assert sleeps[-1] == 1.0


async def test_unsupported_firmware_is_refused_without_retry():
    client = FakeTag(b"SE0290XX00-TNG-A0")
    prepared = _prepared()
    with pytest.raises(WriteRefused, match="SE0290XX00"):
        await writer.write_session(client, "AA", PRESET, prepared, trace=_trace())
    assert client.written == []


@pytest.mark.parametrize(
    ("kwargs", "match"), [({"service": False}, "missing"), ({"mtu": 20}, "too small")]
)
@pytest.mark.filterwarnings(
    "error::RuntimeWarning", "error::pytest.PytestUnraisableExceptionWarning"
)
async def test_link_problems_are_reported_and_close_the_unused_encode(kwargs, match):
    prepared = asyncio.get_running_loop().create_future()
    with pytest.raises(EtagError, match=match):
        await writer.write_session(FakeTag(**kwargs), "AA", PRESET, prepared, trace=_trace())
    prepared.cancel()
    gc.collect()  # the unawaited wrapper coroutine would warn here


async def test_rejected_packet_aborts_the_transfer():
    client = FakeTag(image_status=1)
    with pytest.raises(EtagError, match="rejected"):
        await writer.write_session(client, "AA", PRESET, _prepared(), trace=_trace())
    assert len(client.written) == 4  # handshake, then the first image packet


async def test_a_silent_tag_times_out_naming_the_step():
    client = FakeTag(silent_after=1)
    session = writer.EtagSession(client, "AA")
    session.reply_timeout_s = 0.01
    with pytest.raises(NotificationTimeout, match="command 0x11"):
        await session.send(_prepared_list(), total=36, trace=_trace())


async def test_a_dropped_link_ends_the_wait_at_once():
    client = FakeTag(silent_after=0)
    dropped = asyncio.Event()
    session_mod._DROPPED[client] = dropped  # what ble_session() registers
    client.disconnected_callback = lambda _client: dropped.set()
    task = asyncio.create_task(
        writer.EtagSession(client, "AA").send(_prepared_list(), total=36, trace=_trace())
    )
    for _ in range(5):  # let the first write go out unanswered
        await REAL_SLEEP(0)
    client.drop()
    with pytest.raises(SessionDropped):
        await asyncio.wait_for(task, 1)


async def _prepared_list():
    return (await _prepared())[NP61]


async def test_wrong_packet_count_is_an_error():
    async def short():
        return [b"\xac\x01\x00\x00\x00\x00\x01\x00\x01\x00\xca"]

    with pytest.raises(EtagError, match="Expected 36"):
        await writer.EtagSession(FakeTag(), "AA").send(short(), total=36, trace=_trace())


async def test_retry_reuses_the_prepared_encode_and_awaits_it_after_the_handshake():
    """The integration awaits the same future on every attempt."""
    image = Image.new("RGB", (250, 122), "white")
    prepared = asyncio.get_running_loop().create_future()
    expected = list(frames(encode_image(image, PRESET)[NP61]))
    for attempt in range(2):
        client = FakeTag()
        task = asyncio.create_task(
            writer.write_session(client, "AA", PRESET, prepared, trace=_trace())
        )
        if attempt == 0:

            async def handshake_sent(client=client):
                while len(client.written) < 3:
                    await REAL_SLEEP(0)

            # Fails (rather than hangs) if the encode is awaited first.
            await asyncio.wait_for(handshake_sent(), 1)
            assert not task.done()
            prepared.set_result(writer.prepare(PRESET, image, "AA"))
        await task
        assert client.written == expected
