"""Tests for PickSmart BLE writer, 4-step handshake, and stall detection."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.picksmart.devices import PRESETS
from custom_components.ble_esl.esl_ble.picksmart.writer import (
    PickSmartClient,
    PickSmartError,
    update_image,
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
                    mock_client._handler(
                        None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00])
                    )
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
            write_delay_ms=0,
        )
        img = Image.new("RGB", (296, 128), "white")
        result = await client.write_image(img)

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
                    mock_client._handler(
                        None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00])
                    )
            elif char == IMG_UUID:
                # Repeat same part 0 repeatedly
                mock_client._handler(
                    None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00])
                )

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
            write_delay_ms=0,
        )
        img = Image.new("RGB", (296, 128), "white")

        with pytest.raises(PickSmartError, match="Transfer stalled: part 0/.* requested 6 times"):
            await client.write_image(img)
        # One send per request: the initial one plus five resends.
        img_writes = [c for c in mock_client.write_gatt_char.await_args_list if c.args[0] == IMG_UUID]
        assert len(img_writes) == 6

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
        result = await client.write_image(Image.new("RGB", (296, 128), "white"))

        assert result.success is True
        sent_parts = [
            int.from_bytes(c.args[1][0:4], "little")
            for c in mock_client.write_gatt_char.await_args_list
            if c.args[0] == IMG_UUID
        ]
        assert sent_parts.count(3) == 5
        assert sorted(set(sent_parts)) == list(range(max(sent_parts) + 1))  # every part sent

    asyncio.run(_test())


def test_picksmart_timeout_error_is_descriptive(monkeypatch):
    """A tag that stops answering yields a message naming the step, not ''."""

    async def _test():
        monkeypatch.setattr(
            "custom_components.ble_esl.esl_ble.picksmart.writer.FEEDBACK_TIMEOUT", 0.05
        )
        mock_client = MagicMock()
        mock_client.start_notify = AsyncMock()
        mock_client.stop_notify = AsyncMock()
        mock_client.write_gatt_char = AsyncMock()  # never answers

        client = PickSmartClient(mock_client, CMD_UUID, IMG_UUID, PRESETS["0x0033"], MAC)
        with pytest.raises(PickSmartError, match="No response from tag within 0.05s after START"):
            await client.write_image(Image.new("RGB", (296, 128), "white"))

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
                    mock_client._handler(
                        None, bytearray([0x05, 0x00, 0x00, 0x00, 0x00, 0x00])
                    )
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
            "custom_components.ble_esl.esl_ble.picksmart.writer.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await update_image(mock_ble_device, PRESETS["0x0033"], img)

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
            "custom_components.ble_esl.esl_ble.picksmart.writer.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await update_image(mock_ble_device, PRESETS["0x0028"], img)

        assert result.success is False
        assert result.error == "unavailable"

    asyncio.run(_test())


def test_connection_starts_before_encode_finishes(monkeypatch):
    """Encoding overlaps connecting instead of delaying it."""
    import time

    from custom_components.ble_esl.esl_ble.picksmart import writer

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

        monkeypatch.setattr(writer, "encode_image", slow_prepare)
        monkeypatch.setattr(writer, "establish_connection", connect)

        mock_ble_device = MagicMock()
        mock_ble_device.address = "AA:BB:CC:DD:EE:FF"
        result = await update_image(mock_ble_device, PRESETS["0x0028"], Image.new("RGB", (296, 128)))
        await asyncio.sleep(0.2)  # let the encode thread finish

        assert result.success is False
        assert connect_started_at < encode_done_at

    asyncio.run(_test())


@pytest.mark.parametrize("ends_after_last", [True, False])
def test_picksmart_unexpected_frame_only_ok_after_last_part(ends_after_last):
    """A non-'send me part N' frame is success only once every part was sent."""

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
                end_at = payload_parts - 1 if ends_after_last else 1
                if part == end_at:
                    mock_client._handler(None, bytearray([0x05, 0x08]))  # unknown frame
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

        if ends_after_last:
            assert (await client.write_image(img)).success is True
        else:
            with pytest.raises(PickSmartError, match=r"ended transfer after part 1/\d+ with 0508"):
                await client.write_image(img)

    asyncio.run(_test())
