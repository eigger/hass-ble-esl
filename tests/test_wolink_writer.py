"""Tests for WOLINK BLE session writer, authentication, and status notifications."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from PIL import Image
import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble import base
from custom_components.ble_esl.esl_ble.base import NotificationTimeout
from custom_components.ble_esl.esl_ble.wolink.const import (
    AES_KEY,
    AUTH_CHAR,
    DATA_CHAR,
    STATUS_CHAR,
)
from custom_components.ble_esl.esl_ble.wolink.devices import PRESETS
from custom_components.ble_esl.esl_ble.wolink.writer import (
    WolinkClient,
    WolinkError,
    prepare,
)

MAC = "66:66:54:20:00:55"


def test_wolink_authentication():
    """Verify AES-128 ECB challenge-response authentication writes directly to AUTH_CHAR without pre-subscribing."""

    async def _test():
        mock_client = MagicMock()
        mock_client.is_connected = True
        nonce = bytes(range(16))
        mock_client.read_gatt_char = AsyncMock(return_value=nonce)
        mock_client.start_notify = AsyncMock()
        written = {}

        async def mock_write(char, data, response=True):
            written[char] = data

        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = WolinkClient(mock_client, PRESETS["290"], MAC)
        await client.authenticate()

        # Must not call start_notify during authenticate to avoid triggering unauthorized service disconnect
        assert not mock_client.start_notify.called
        assert AUTH_CHAR in written
        cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(written[AUTH_CHAR]) + decryptor.finalize()
        assert decrypted == nonce

    asyncio.run(_test())


def test_wolink_authentication_failure_disconnect():
    """Verify authenticate immediately raises WolinkError if device disconnects."""

    async def _test():
        mock_client = MagicMock()
        mock_client.is_connected = True
        nonce = bytes(range(16))
        mock_client.read_gatt_char = AsyncMock(return_value=nonce)

        async def mock_write(char, data, response=True):
            if char == AUTH_CHAR:
                # Device closes connection on bad auth
                mock_client.is_connected = False

        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = WolinkClient(mock_client, PRESETS["290"], MAC)
        with pytest.raises(WolinkError, match="device error 5"):
            await client.authenticate()

    asyncio.run(_test())


def test_wolink_write_image_flow_with_status_notification():
    """Verify write_image subscribes to status BEFORE writing, handles chunks and completion."""

    async def _test():
        mock_client = MagicMock()
        written_data: list[bytes] = []
        notification_active = False

        async def mock_start_notify(char, handler):
            nonlocal notification_active
            assert char == STATUS_CHAR
            notification_active = True
            mock_client._handler = handler

        async def mock_stop_notify(char):
            nonlocal notification_active
            assert char == STATUS_CHAR
            notification_active = False

        async def mock_write(char, data, response=True):
            assert char == DATA_CHAR
            # Status notify MUST be subscribed before any write commands
            assert notification_active is True
            written_data.append(data)
            # If refresh command (OP 0xA502 = 0x02 0xA5), simulate device sending completion notification
            if data[:2] == b"\x02\xa5":
                # Send 0xFF completion marker
                mock_client._handler(None, bytearray([0xFF, 0x00]))

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock(side_effect=mock_stop_notify)
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = WolinkClient(mock_client, PRESETS["290"], MAC)
        img = Image.new("RGB", (296, 128), "white")
        prepared = prepare(PRESETS["290"], img, MAC)
        result = await client.write_prepared(prepared)

        assert result.success is True
        assert len(written_data) >= 2  # Chunks + refresh
        assert notification_active is False  # Stopped after session
        # The breakdown: every chunk is a part (all sent), the refresh wait is finish_s.
        assert result.timing["parts"] == len(written_data) - 1 == result.timing["sends"]
        assert result.timing["bytes"] == len(prepared[0])
        assert {"transfer_s", "finish_s"} <= result.timing.keys()

    asyncio.run(_test())


def test_wolink_error_during_upload_fails_before_refresh():
    """An ERR status frame received while chunks are still being sent fails the
    write without sending the refresh command."""

    async def _test():
        mock_client = MagicMock()
        sent = []

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=True):
            sent.append(bytes(data[:2]))
            if data[:2] == b"\x00\xa5" and len(sent) == 1:  # first image chunk
                mock_client._handler(None, bytearray([0x01, 0x01]))  # ERR=1 during upload

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = WolinkClient(mock_client, PRESETS["290"], MAC)
        img = Image.new("RGB", (296, 128), "white")
        with pytest.raises(WolinkError, match="device error 1: epd initialization error"):
            await client.write_prepared(prepare(PRESETS["290"], img, MAC))

        assert b"\x02\xa5" not in sent  # refresh (0xA502) never sent
        mock_client.stop_notify.assert_awaited_once()

    asyncio.run(_test())


def test_wolink_write_image_error_notification():
    """Verify write_image handles device ERR status frame."""

    async def _test():
        mock_client = MagicMock()

        async def mock_start_notify(char, handler):
            mock_client._handler = handler

        async def mock_write(char, data, response=True):
            if data[:2] == b"\x02\xa5":
                # Send ERR=2 (epd write error)
                mock_client._handler(None, bytearray([0x01, 0x02]))

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = WolinkClient(mock_client, PRESETS["290"], MAC)
        img = Image.new("RGB", (296, 128), "white")

        with pytest.raises(WolinkError, match="device error 2: epd write error"):
            await client.write_prepared(prepare(PRESETS["290"], img, MAC))

    asyncio.run(_test())


def test_write_image_entrypoint(monkeypatch):
    """Verify write_image handles connection, authentication, write, and disconnect (no GATT battery read)."""

    async def _test():
        mock_ble_device = MagicMock()
        mock_ble_device.address = MAC

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.read_gatt_char = AsyncMock(return_value=bytes(16))
        mock_client.start_notify = AsyncMock()
        mock_client.stop_notify = AsyncMock()
        mock_client.disconnect = AsyncMock()

        async def mock_write(char, data, response=True):
            if char == DATA_CHAR and data[:2] == b"\x02\xa5":
                # Trigger 0x00 idle / not busy completion
                mock_client.start_notify.call_args[0][1](None, bytearray([0x00, 0x00]))

        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        async def mock_establish(*args, **kwargs):
            return mock_client

        monkeypatch.setattr(
            "custom_components.ble_esl.esl_ble.base.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await esl_ble.get("wolink").write_image(
            mock_ble_device, PRESETS["290"], img, pacing_s=0.05
        )

        assert result.success is True
        assert result.battery_mv is None  # No redundant GATT battery read
        assert mock_client.disconnect.called
        # Authentication is the handshake stage; the common connect/session
        # split wraps the protocol's own stages.
        assert list(result.timing) == [
            "connect_s",
            "start_s",
            "bytes",
            "parts",
            "sends",
            "transfer_s",
            "finish_s",
            "session_s",
        ]

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
        result = await esl_ble.get("wolink").write_image(mock_ble_device, PRESETS["290"], img)

        assert result.success is False
        assert result.error == "unavailable"

    asyncio.run(_test())


def test_encoding_overlaps_connection_off_the_event_loop(monkeypatch):
    """Encoding runs in a worker thread concurrently with connecting: the loop
    keeps ticking, and the connection starts before the encode finishes."""
    import time

    async def _test():
        ticks = 0
        encode_done_at = None

        async def ticker():
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0.01)

        def slow_prepare(preset, image, address):
            nonlocal encode_done_at
            time.sleep(0.3)  # blocking CPU stand-in
            encode_done_at = time.monotonic()
            return b"", 0

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.disconnect = AsyncMock()
        mock_client.read_gatt_char = AsyncMock(side_effect=OSError("stop at auth"))
        connect_started_at = None

        async def connect(*args, **kwargs):
            nonlocal connect_started_at
            connect_started_at = time.monotonic()
            return mock_client

        monkeypatch.setattr(esl_ble.get("wolink"), "prepare_image", slow_prepare)
        monkeypatch.setattr(base, "establish_connection", connect)

        mock_ble_device = MagicMock()
        mock_ble_device.address = MAC
        task = asyncio.create_task(ticker())
        result = await esl_ble.get("wolink").write_image(
            mock_ble_device, PRESETS["290"], Image.new("RGB", (296, 128))
        )
        task.cancel()

        assert result.success is False and result.error == "stop at auth"
        assert connect_started_at < encode_done_at  # radio not delayed by the encode
        assert ticks >= 10  # loop was not blocked during the 300 ms encode
        assert mock_client.disconnect.await_count == 1

    asyncio.run(_test())


def test_connect_failure_does_not_leak_encode_task(monkeypatch):
    """If connecting fails while the encode is still running, the result is
    dropped cleanly (no pending-task or unretrieved-exception warnings)."""
    from custom_components.ble_esl.esl_ble.wolink import writer

    async def _test():
        started = asyncio.Event()

        async def slow_encode(*args):
            started.set()
            await asyncio.sleep(0.2)
            return b"", 0

        async def failing_connect(*args, **kwargs):
            await asyncio.sleep(0)  # a real connect yields to the loop
            raise OSError("no link")

        monkeypatch.setattr(writer.asyncio, "to_thread", slow_encode)
        monkeypatch.setattr(base, "establish_connection", failing_connect)

        mock_ble_device = MagicMock()
        mock_ble_device.address = MAC
        result = await esl_ble.get("wolink").write_image(
            mock_ble_device, PRESETS["290"], Image.new("RGB", (296, 128))
        )
        assert result.success is False and result.error == "no link"
        assert started.is_set()
        await asyncio.sleep(0)
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert pending == []

    asyncio.run(_test())


def test_wolink_completion_timeout_has_message(monkeypatch):
    """A tag that never confirms the refresh raises a descriptive timeout (the
    backend turns it into the WriteResult error)."""

    async def _test():
        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.start_notify = AsyncMock()
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock()  # never notifies

        client = WolinkClient(mock_client, PRESETS["290"], MAC)
        monkeypatch.setattr(WolinkClient, "_completion_timeout", staticmethod(lambda raw_len: 0.05))
        with pytest.raises(
            NotificationTimeout, match=r"No response from tag within 0\.05s after refresh"
        ):
            await client.write_prepared(
                prepare(PRESETS["290"], Image.new("RGB", (296, 128), "white"), MAC)
            )

    asyncio.run(_test())


def test_write_prepared_awaits_encode_after_connect_and_leaves_it_to_caller(monkeypatch):
    """The caller-owned future is awaited once the link is up and not cancelled here."""
    from custom_components.ble_esl.esl_ble.wolink import writer

    async def _test():
        order = []
        prepared = asyncio.get_running_loop().create_future()

        async def connect(*args, **kwargs):
            order.append("connect")
            prepared.set_result((b"", 0))
            return MagicMock(is_connected=False)

        monkeypatch.setattr(base, "establish_connection", connect)
        monkeypatch.setattr(
            writer.WolinkClient, "authenticate", AsyncMock(side_effect=OSError("stop"))
        )
        mock_ble_device = MagicMock()
        mock_ble_device.address = MAC
        result = await esl_ble.get("wolink").write_prepared(
            mock_ble_device, PRESETS["290"], prepared
        )

        assert result.success is False and result.error == "stop"
        assert order == ["connect"]
        assert prepared.done() and not prepared.cancelled()
        assert prepared.result() == (b"", 0)  # still usable for a retry

    asyncio.run(_test())
