"""Bluetooth test helpers.

`inject_bluetooth_service_info` and the generators are a trimmed port of Home
Assistant's tests/components/bluetooth/__init__.py, which
pytest-homeassistant-custom-component does not ship. `service_info()` builds
the BluetoothServiceInfoBleak the integration's parsers and backends consume.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

from bleak.backends.scanner import AdvertisementData, BLEDevice
from homeassistant.components.bluetooth import (
    SOURCE_LOCAL,
    BaseHaRemoteScanner,
    BluetoothServiceInfoBleak,
    HaBluetoothConnector,
    async_get_advertisement_callback,
    async_register_scanner,
)
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback

ADVERTISEMENT_DATA_DEFAULTS: dict[str, Any] = {
    "local_name": "",
    "manufacturer_data": {},
    "service_data": {},
    "service_uuids": [],
    "rssi": -127,
    "platform_data": ((),),
    "tx_power": -127,
}


def generate_advertisement_data(**kwargs: Any) -> AdvertisementData:
    """Generate advertisement data with defaults."""
    return AdvertisementData(**{**ADVERTISEMENT_DATA_DEFAULTS, **kwargs})


def generate_ble_device(
    address: str, name: str | None = None, details: Any | None = None
) -> BLEDevice:
    """Generate a BLEDevice."""
    return BLEDevice(address=address, name=name, details=details)


def service_info(
    address: str,
    *,
    name: str = "",
    manufacturer_data: dict[int, bytes] | None = None,
    service_uuids: list[str] | None = None,
    service_data: dict[str, bytes] | None = None,
    rssi: int = -60,
    connectable: bool = True,
    source: str = SOURCE_LOCAL,
) -> BluetoothServiceInfoBleak:
    """A BluetoothServiceInfoBleak as the bluetooth integration would deliver it."""
    advertisement = generate_advertisement_data(
        local_name=name or None,
        manufacturer_data=manufacturer_data or {},
        service_uuids=service_uuids or [],
        service_data=service_data or {},
        rssi=rssi,
    )
    device = generate_ble_device(address, name or None, details={})
    return BluetoothServiceInfoBleak(
        name=name or address,
        address=address,
        rssi=rssi,
        manufacturer_data=advertisement.manufacturer_data,
        service_data=advertisement.service_data,
        service_uuids=advertisement.service_uuids,
        source=source,
        device=device,
        advertisement=advertisement,
        connectable=connectable,
        time=time.monotonic(),
        tx_power=advertisement.tx_power,
    )


def inject_bluetooth_service_info(hass: HomeAssistant, info: BluetoothServiceInfoBleak) -> None:
    """Deliver an advertisement to the bluetooth manager as if a scanner saw it."""
    async_get_advertisement_callback(hass)(info)


class FakeProxyScanner(BaseHaRemoteScanner):
    """A Bluetooth proxy (ESPHome-style remote scanner) as bluetooth sees one.

    Advertisements injected through it carry the proxy as their source, so
    the integration can report which radio a write went through.
    """

    def inject_advertisement(self, info: BluetoothServiceInfoBleak) -> None:
        self._async_on_advertisement(
            info.address,
            info.rssi,
            info.name,
            info.service_uuids,
            info.service_data,
            info.manufacturer_data,
            info.tx_power,
            {},
            time.monotonic(),
        )


def register_proxy(hass: HomeAssistant, name: str, mac: str) -> FakeProxyScanner:
    """Register a connectable proxy scanner named `name` with source `mac`.

    bluetooth names it "<name> (<mac>)". It is torn down with Home Assistant
    so its expiry timer does not linger past the test.
    """
    connector = HaBluetoothConnector(MagicMock, "fake", lambda: True)
    scanner = FakeProxyScanner(mac, name, connector, True)
    unsetup = scanner.async_setup()
    unregister = async_register_scanner(hass, scanner)

    @callback
    def _teardown(_event: Event) -> None:
        unregister()
        unsetup()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _teardown)
    return scanner


# ── Reading a parser's SensorUpdate ──────────────────────────────────────


def sensor_values(update: Any) -> dict[str, Any]:
    """{key: native_value} of the sensors in a SensorUpdate."""
    return {k.key: v.native_value for k, v in update.entity_values.items()}


def binary_values(update: Any) -> dict[str, bool | None]:
    """{key: native_value} of the binary sensors in a SensorUpdate."""
    return {k.key: v.native_value for k, v in update.binary_entity_values.items()}


def update_device(update: Any) -> Any:
    """The (single) SensorDeviceInfo in a SensorUpdate."""
    return update.devices[None]
