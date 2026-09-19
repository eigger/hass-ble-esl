"""Shared BLE connection handling for the protocol writers."""

from __future__ import annotations

from collections.abc import AsyncIterator
import contextlib
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient
from bleak_retry_connector import establish_connection

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def ble_session(ble_device: BLEDevice) -> AsyncIterator[BleakClient]:
    """Connect to the tag for the duration of the block, then disconnect.

    Connecting happens inside the context so a connection failure raises
    out of the block like any other session error; the caller (see
    BleBackend.write_prepared) turns it into a failed WriteResult that
    counts toward retries. Disconnect failures on an already-dropped link
    are suppressed so they never mask the original error.
    """
    client: BleakClient | None = None
    try:
        client = await establish_connection(BleakClient, ble_device, ble_device.address)
        yield client
    finally:
        with contextlib.suppress(Exception):
            if client and client.is_connected:
                await client.disconnect()
