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
    """Verify stall error is raised when device requests the same part 3 times."""

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

        with pytest.raises(PickSmartError, match="Transfer stalled: part 0 requested 3 times"):
            await client.write_image(img)

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
