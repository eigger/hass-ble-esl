"""Tests for PickSmart BLE writer, 4-step handshake, and stall detection."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from PIL import Image
import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble import base
from custom_components.ble_esl.esl_ble.base import NotificationTimeout
from custom_components.ble_esl.esl_ble.picksmart.devices import PRESETS
from custom_components.ble_esl.esl_ble.picksmart.writer import (
    PickSmartClient,
    PickSmartError,
    prepare,
)

CMD_UUID = "0000fef1-0000-1000-8000-00805f9b34fb"
IMG_UUID = "0000fef2-0000-1000-8000-00805f9b34fb"
MAC = "AA:BB:CC:DD:EE:FF"


def test_picksmart_handshake_flow():
    """Verify 4-step request-response handshake flow."""

    async def _test():
        mock_client = MagicMock()

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=False):
            if char == CMD_UUID:
                if data[0] == 0x01:
                    # Step 1 response: 01 F4 00
                    mock_client._handler(None, bytearray([0x01, 0xF4, 0x00]))
                elif data[0] == 0x02:
                    # Step 2 response: 02
                    mock_client._handler(None, bytearray([0x02]))
                elif data[0] == 0x03:
                    # Step 3 response: 05 00 + part 0 (4B LE)
                    mock_client._handler(None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif char == IMG_UUID:
                # Step 4 response: request next part or signal completion (large part)
                part = int.from_bytes(data[:4], "little")
                next_part = part + 1
                resp = bytearray([0x05, 0x00]) + next_part.to_bytes(4, "little")
                mock_client._handler(None, resp)

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = PickSmartClient(
            mock_client,
            CMD_UUID,
            IMG_UUID,
            PRESETS["0x0033"],
            MAC,
            attempt=1,
        )
        img = Image.new("RGB", (296, 128), "white")
        result = await client.write_payload(prepare(PRESETS["0x0033"], img, MAC))

        assert result.success is True

    asyncio.run(_test())


def test_picksmart_stall_detection():
    """Verify stall error is raised when device requests the same part 6 times."""

    async def _test():
        mock_client = MagicMock()

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=False):
            if char == CMD_UUID:
                if data[0] == 0x01:
                    mock_client._handler(None, bytearray([0x01, 0xF4, 0x00]))
                elif data[0] == 0x02:
                    mock_client._handler(None, bytearray([0x02]))
                elif data[0] == 0x03:
                    mock_client._handler(None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif char == IMG_UUID:
                # Repeat same part 0 repeatedly
                mock_client._handler(None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00]))

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = PickSmartClient(
            mock_client,
            CMD_UUID,
            IMG_UUID,
            PRESETS["0x0033"],
            MAC,
            attempt=1,
        )
        img = Image.new("RGB", (296, 128), "white")

        with pytest.raises(
            PickSmartError, match=r"Transfer stalled: part 0/\d+ requested 6 times"
        ) as caught:
            await client.write_payload(prepare(PRESETS["0x0033"], img, MAC))
        # One send per request: the initial one plus five resends.
        img_writes = [
            c for c in mock_client.write_gatt_char.await_args_list if c.args[0] == IMG_UUID
        ]
        assert len(img_writes) == 6
        # A stall is when the counters matter: they reach the failed
        # WriteResult through the exception even though the loop never ended.
        timing = caught.value.timing
        assert timing["sends"] == 6 and timing["resends"] == 5
        assert timing["completed_by_tag"] is False
        assert timing["parts"] == 40 and timing["round_trip_ms"] >= 0
        assert {"start_s", "transfer_s"} <= timing.keys()

    asyncio.run(_test())


def test_picksmart_recovers_from_resend_requests(monkeypatch):
    """A tag re-requesting a part a few times is served, not treated as a stall."""

    async def _test():
        monkeypatch.setattr(
            "custom_components.ble_esl.esl_ble.picksmart.writer.RESEND_BACKOFF_S", 0.0
        )
        mock_client = MagicMock()
        requests_for_part3 = 0

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=False):
            nonlocal requests_for_part3
            if char == CMD_UUID:
                if data[0] == 0x01:
                    mock_client._handler(None, bytearray([0x01, 0xF4, 0x00]))
                elif data[0] == 0x02:
                    mock_client._handler(None, bytearray([0x02]))
                elif data[0] == 0x03:
                    mock_client._handler(None, bytearray([0x05, 0x00]) + (0).to_bytes(4, "little"))
            elif char == IMG_UUID:
                part = int.from_bytes(data[0:4], "little")
                # Reject part 3 four times (5 requests in total), then accept it.
                if part == 3 and requests_for_part3 < 4:
                    requests_for_part3 += 1
                    nxt = 3
                else:
                    nxt = part + 1
                mock_client._handler(None, bytearray([0x05, 0x00]) + nxt.to_bytes(4, "little"))

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = PickSmartClient(mock_client, CMD_UUID, IMG_UUID, PRESETS["0x0033"], MAC)
        result = await client.write_payload(
            prepare(PRESETS["0x0033"], Image.new("RGB", (296, 128), "white"), MAC)
        )

        assert result.success is True
        sent_parts = [
            int.from_bytes(c.args[1][0:4], "little")
            for c in mock_client.write_gatt_char.await_args_list
            if c.args[0] == IMG_UUID
        ]
        assert sent_parts.count(3) == 5
        assert sorted(set(sent_parts)) == list(range(max(sent_parts) + 1))  # every part sent

    asyncio.run(_test())


WRITER = "custom_components.ble_esl.esl_ble.picksmart.writer"


def _fast_probe(monkeypatch, timeout=0.02, attempts=3, settle=0.0):
    monkeypatch.setattr(f"{WRITER}.START_PROBE_TIMEOUT_S", timeout)
    monkeypatch.setattr(f"{WRITER}.START_PROBE_ATTEMPTS", attempts)
    monkeypatch.setattr(f"{WRITER}.NOTIFY_SETTLE_S", settle)


def test_picksmart_start_is_probed_until_the_tag_answers(monkeypatch):
    """A START the tag drops (not ready after subscribing) is resent; the
    first answered one proves subscription and readiness end to end."""

    async def _test():
        _fast_probe(monkeypatch)
        mock_client = MagicMock()
        starts = 0

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=False):
            nonlocal starts
            if char == CMD_UUID and data[0] == 0x01:
                starts += 1
                if starts < 3:
                    return  # dropped: tag not ready yet
                mock_client._handler(None, bytearray([0x01, 0xF4, 0x00]))
            elif char == CMD_UUID and data[0] == 0x02:
                mock_client._handler(None, bytearray([0x02]))
            elif char == CMD_UUID and data[0] == 0x03:
                mock_client._handler(None, bytearray([0x05, 0x00]) + (0).to_bytes(4, "little"))
            elif char == IMG_UUID:
                part = int.from_bytes(data[0:4], "little")
                mock_client._handler(
                    None, bytearray([0x05, 0x00]) + (part + 1).to_bytes(4, "little")
                )

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = PickSmartClient(mock_client, CMD_UUID, IMG_UUID, PRESETS["0x0033"], MAC)
        result = await client.write_payload(
            prepare(PRESETS["0x0033"], Image.new("RGB", (296, 128), "white"), MAC)
        )

        assert result.success is True
        assert starts == 3
        assert result.timing["start_probes"] == 3
        assert result.timing["parts"] == 40 == result.timing["sends"]
        assert result.timing["resends"] == 0
        assert {"settle_s", "start_s", "transfer_s", "round_trip_ms"} <= result.timing.keys()

    asyncio.run(_test())


def test_picksmart_start_probes_exhausted_is_descriptive(monkeypatch):
    """A tag that never answers START fails after the probe budget with a
    message naming what was tried, not ''."""

    async def _test():
        _fast_probe(monkeypatch)
        mock_client = MagicMock()
        mock_client.start_notify = AsyncMock()
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock()  # never answers

        client = PickSmartClient(mock_client, CMD_UUID, IMG_UUID, PRESETS["0x0033"], MAC)
        with pytest.raises(
            NotificationTimeout, match=r"No response from tag to START after 3 probes"
        ):
            await client.write_payload(
                prepare(PRESETS["0x0033"], Image.new("RGB", (296, 128), "white"), MAC)
            )
        starts = [c for c in mock_client.write_gatt_char.await_args_list if c.args[1][0] == 0x01]
        assert len(starts) == 3

        # The failed attempt still reports how far it got, via the backend.
        from custom_components.ble_esl import esl_ble
        from custom_components.ble_esl.esl_ble import base

        monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=mock_client))
        mock_client.services = []
        result = await esl_ble.get("picksmart").write_prepared(
            MagicMock(address=MAC), PRESETS["0x0033"], _done(b"")
        )
        assert result.success is False
        assert "Insufficient characteristics" in result.error
        assert {"connect_s", "session_s"} <= result.timing.keys()

    asyncio.run(_test())


def test_picksmart_timeout_after_start_is_descriptive(monkeypatch):
    """Once START is answered, a later step that times out names that step."""

    async def _test():
        _fast_probe(monkeypatch)
        monkeypatch.setattr(f"{WRITER}.FEEDBACK_TIMEOUT", 0.05)
        mock_client = MagicMock()

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=False):
            if char == CMD_UUID and data[0] == 0x01:
                mock_client._handler(None, bytearray([0x01, 0xF4, 0x00]))
            # SIZE is never answered

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = PickSmartClient(mock_client, CMD_UUID, IMG_UUID, PRESETS["0x0033"], MAC)
        with pytest.raises(
            NotificationTimeout, match=r"No response from tag within 0\.05s after SIZE"
        ):
            await client.write_payload(
                prepare(PRESETS["0x0033"], Image.new("RGB", (296, 128), "white"), MAC)
            )

    asyncio.run(_test())


def test_picksmart_update_image_entrypoint(monkeypatch):
    """Verify update_image dynamically resolves UUIDs, writes image, and disconnects."""

    async def _test():
        mock_ble_device = MagicMock()
        mock_ble_device.address = MAC

        mock_svc = MagicMock()
        mock_svc.uuid = "0000fef0-0000-1000-8000-00805f9b34fb"

        char1 = MagicMock()
        char1.uuid = CMD_UUID
        char2 = MagicMock()
        char2.uuid = IMG_UUID
        mock_svc.characteristics = [char1, char2]

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.services = [mock_svc]
        mock_client.disconnect = AsyncMock()

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=False):
            if char == CMD_UUID:
                if data[0] == 0x01:
                    mock_client._handler(None, bytearray([0x01, 0xF4, 0x00]))
                elif data[0] == 0x02:
                    mock_client._handler(None, bytearray([0x02]))
                elif data[0] == 0x03:
                    mock_client._handler(None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00]))
            elif char == IMG_UUID:
                part = int.from_bytes(data[:4], "little")
                next_part = part + 1
                resp = bytearray([0x05, 0x00]) + next_part.to_bytes(4, "little")
                mock_client._handler(None, resp)

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        async def mock_establish(*args, **kwargs):
            return mock_client

        monkeypatch.setattr(
            "custom_components.ble_esl.esl_ble.base.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await esl_ble.get("picksmart").write_image(mock_ble_device, PRESETS["0x0033"], img)

        assert result.success is True
        assert mock_client.disconnect.called

    asyncio.run(_test())


def test_connection_failure_is_reported_not_raised(monkeypatch):
    """establish_connection errors become a failed WriteResult so retries/counters apply."""

    async def _test():
        mock_ble_device = MagicMock()
        mock_ble_device.address = "AA:BB:CC:DD:EE:FF"

        async def mock_establish(*args, **kwargs):
            raise OSError("unavailable")

        monkeypatch.setattr(
            "custom_components.ble_esl.esl_ble.base.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await esl_ble.get("picksmart").write_image(mock_ble_device, PRESETS["0x0028"], img)

        assert result.success is False
        assert result.error == "unavailable"

    asyncio.run(_test())


def test_connection_starts_before_encode_finishes(monkeypatch):
    """Encoding overlaps connecting instead of delaying it."""
    import time

    async def _test():
        encode_done_at = None

        def slow_prepare(*args, **kwargs):
            nonlocal encode_done_at
            time.sleep(0.15)
            encode_done_at = time.monotonic()
            return b""

        connect_started_at = None

        async def connect(*args, **kwargs):
            nonlocal connect_started_at
            connect_started_at = time.monotonic()
            await asyncio.sleep(0)  # a real connect yields to the loop
            raise OSError("stop here")

        monkeypatch.setattr(esl_ble.get("picksmart"), "prepare_image", slow_prepare)
        monkeypatch.setattr(base, "establish_connection", connect)

        mock_ble_device = MagicMock()
        mock_ble_device.address = "AA:BB:CC:DD:EE:FF"
        result = await esl_ble.get("picksmart").write_image(
            mock_ble_device, PRESETS["0x0028"], Image.new("RGB", (296, 128))
        )
        await asyncio.sleep(0.2)  # let the encode thread finish

        assert result.success is False
        assert connect_started_at < encode_done_at

    asyncio.run(_test())


@pytest.mark.parametrize(
    ("frame", "at", "expect"),
    [
        (bytes([0x05, 0x08, 0, 0, 0, 0]), "last", "completed"),
        (bytes([0x05, 0x08, 0, 0, 0, 0]), 1, r"Tag reported completion after part 1/\d+"),
        (
            bytes([0x05, 0x01, 0, 0, 0, 0]),
            "last",
            r"Unexpected reply after part \d+/\d+: 050100000000",
        ),
        (bytes([0x07]), 1, r"Unexpected reply after part 1/\d+: 07"),
    ],
    ids=["complete-after-last", "complete-too-early", "unknown-after-last", "unknown-early"],
)
def test_picksmart_transfer_end_frames(frame, at, expect):
    """05 08 is the tag's completion frame (seen after the last part on every
    tag tested); it is accepted only there. Any other non-'next part' reply
    fails the transfer wherever it arrives."""

    async def _test():
        mock_client = MagicMock()
        payload_parts = None

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=False):
            if char == CMD_UUID:
                if data[0] == 0x01:
                    mock_client._handler(None, bytearray([0x01, 0xF4, 0x00]))
                elif data[0] == 0x02:
                    mock_client._handler(None, bytearray([0x02]))
                elif data[0] == 0x03:
                    mock_client._handler(None, bytearray([0x05, 0x00]) + (0).to_bytes(4, "little"))
            elif char == IMG_UUID:
                part = int.from_bytes(data[0:4], "little")
                end_at = payload_parts - 1 if at == "last" else at
                if part == end_at:
                    mock_client._handler(None, bytearray(frame))
                else:
                    mock_client._handler(
                        None, bytearray([0x05, 0x00]) + (part + 1).to_bytes(4, "little")
                    )

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        from custom_components.ble_esl.esl_ble.picksmart.protocol import encode_image

        img = Image.new("RGB", (296, 128), "white")
        payload_parts = (len(encode_image(img, PRESETS["0x0033"])) + 239) // 240
        client = PickSmartClient(mock_client, CMD_UUID, IMG_UUID, PRESETS["0x0033"], MAC)

        if expect == "completed":
            result = await client.write_payload(prepare(PRESETS["0x0033"], img, MAC))
            assert result.success is True
            assert result.timing["completed_by_tag"] is True
        else:
            with pytest.raises(PickSmartError, match=expect):
                await client.write_payload(prepare(PRESETS["0x0033"], img, MAC))

    asyncio.run(_test())


def _done(value):
    fut = asyncio.get_event_loop().create_future()
    fut.set_result(value)
    return fut


def test_failed_start_probes_carry_timing(monkeypatch):
    """When every START goes unanswered, the failed WriteResult still says
    how many probes were sent, so the settle/probe budget can be tuned."""
    from custom_components.ble_esl.esl_ble import base

    async def _test():
        _fast_probe(monkeypatch)
        mock_client = MagicMock(is_connected=True, disconnect=AsyncMock())
        mock_client.start_notify = AsyncMock()
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock()  # never answers
        char = MagicMock(uuid="0000fef1-0000-1000-8000-00805f9b34fb")
        char2 = MagicMock(uuid="0000fef2-0000-1000-8000-00805f9b34fb")
        mock_client.services = [
            MagicMock(uuid="0000fef0-0000-1000-8000-00805f9b34fb", characteristics=[char, char2])
        ]
        monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=mock_client))

        prepared = asyncio.get_running_loop().create_future()
        prepared.set_result(b"\x00" * 480)
        result = await esl_ble.get("picksmart").write_prepared(
            MagicMock(address=MAC), PRESETS["0x0033"], prepared
        )

        assert result.success is False
        assert "after 3 probes" in result.error
        assert result.timing["start_probes"] == 3
        assert result.timing["settle_s"] == 0.0
        assert {"connect_s", "session_s"} <= result.timing.keys()

    asyncio.run(_test())
