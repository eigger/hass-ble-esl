"""Tests for easyTag BLE writer, frame transmission, and notify handling."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from PIL import Image

from custom_components.ble_esl.esl_ble.easytag.const import (
    KEY_INDEX_NOTIFY,
    NOTIFY_UUID,
    WRITE_UUID,
)
from custom_components.ble_esl.esl_ble.easytag.devices import PRESETS
from custom_components.ble_esl.esl_ble.easytag.protocol import xor_key
from custom_components.ble_esl.esl_ble.easytag.writer import (
    EasyTagClient,
    update_image,
)

MAC = "3D:00:00:E5:7D:76"


def test_easytag_writer_notify_pre_subscription_and_flow():
    """Verify notify is subscribed before writing and responses are parsed."""

    async def _test():
        mock_client = MagicMock()
        written_frames: list[bytes] = []
        notify_active = False

        async def mock_start_notify(char, handler):
            nonlocal notify_active
            assert char == NOTIFY_UUID
            notify_active = True
            mock_client._handler = handler

        async def mock_stop_notify(char):
            nonlocal notify_active
            assert char == NOTIFY_UUID
            notify_active = False

        async def mock_write(char, data, response=False):
            assert char == WRITE_UUID
            assert notify_active is True  # Notify MUST be subscribed before any write
            written_frames.append(data)
            # On final data packet, simulate device emitting notify frame (3.0V = 30 decivolts, 22°C)
            plain = bytearray(20)
            plain[2] = 30
            plain[3] = 22
            kn = xor_key(MAC, KEY_INDEX_NOTIFY)
            mock_client._handler(None, bytearray(b ^ kn for b in plain))

        mock_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_client.stop_notify = AsyncMock(side_effect=mock_stop_notify)
        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        client = EasyTagClient(mock_client, PRESETS["3D"], MAC)
        img = Image.new("RGB", (296, 128), "white")
        result = await client.write_image(img)

        assert result.success is True
        assert result.battery_mv == 3000
        assert result.temperature_c == 22
        assert len(written_frames) >= 2  # Header + data packets

    asyncio.run(_test())


def test_easytag_update_image_entrypoint(monkeypatch):
    """Verify update_image establishes connection, transmits, and disconnects."""

    async def _test():
        mock_ble_device = MagicMock()
        mock_ble_device.address = MAC

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.start_notify = AsyncMock()
        mock_client.stop_notify = AsyncMock()
        mock_client.disconnect = AsyncMock()

        async def mock_write(char, data, response=False):
            plain = bytearray(20)
            plain[2] = 29
            plain[3] = 18
            kn = xor_key(MAC, KEY_INDEX_NOTIFY)
            mock_client.start_notify.call_args[0][1](
                None, bytearray(b ^ kn for b in plain)
            )

        mock_client.write_gatt_char = AsyncMock(side_effect=mock_write)

        async def mock_establish(*args, **kwargs):
            return mock_client

        monkeypatch.setattr(
            "custom_components.ble_esl.esl_ble.easytag.writer.establish_connection",
            mock_establish,
        )

        img = Image.new("RGB", (296, 128), "white")
        result = await update_image(mock_ble_device, PRESETS["3D"], img)

        assert result.success is True
        assert result.battery_mv == 2900
        assert result.temperature_c == 18
        assert mock_client.disconnect.called

    asyncio.run(_test())
