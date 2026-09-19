"""Tests for WOLINK BLE session writer, authentication, and status notifications."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from PIL import Image
import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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
    update_image,
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
        result = await client.write_image(img, write_delay_ms=0, attempt=1)

        assert result.success is True
        assert len(written_data) >= 2  # Chunks + refresh
        assert notification_active is False  # Stopped after session

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
            await client.write_image(img, write_delay_ms=0, attempt=1)

    asyncio.run(_test())


def test_update_image_entrypoint(monkeypatch):
    """Verify update_image handles connection, authentication, write, and disconnect (no GATT battery read)."""

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
            "custom_components.ble_esl.esl_ble.wolink.writer.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await update_image(mock_ble_device, PRESETS["290"], img, attempt=2, write_delay_ms=50)

        assert result.success is True
        assert result.battery_mv is None  # No redundant GATT battery read
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
            "custom_components.ble_esl.esl_ble.wolink.writer.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await update_image(mock_ble_device, PRESETS["290"], img)

        assert result.success is False
        assert result.error == "unavailable"

    asyncio.run(_test())
