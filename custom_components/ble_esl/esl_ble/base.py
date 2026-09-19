"""Common base classes and data structures for protocol backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any

from bluetooth_sensor_state_data import BluetoothData
from sensor_state_data import BinarySensorDeviceClass, SensorLibrary

from .session import ble_session

if TYPE_CHECKING:
    from bleak import BleakClient
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image

_LOGGER = logging.getLogger(__name__)

CONFIDENCE_HARDWARE = "hardware"  # Verified on real hardware
CONFIDENCE_REPORTED = "reported"  # Third-party verified on real hardware
CONFIDENCE_COMMUNITY = "community"  # Community report, not re-tested
CONFIDENCE_ESTIMATED = "estimated"  # Resolution cross-checked, scan orientation estimated


@dataclass(frozen=True)
class DevicePreset:
    """Specification of an ESL device preset."""

    key: str
    display_name: str
    width: int
    height: int
    colors: str = "BWRY"
    confidence: str = CONFIDENCE_ESTIMATED
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def verified(self) -> bool:
        """True if the preset is confirmed working on physical hardware."""
        return self.confidence in (CONFIDENCE_HARDWARE, CONFIDENCE_REPORTED)

    @property
    def model_name(self) -> str:
        """Display name with the resolution appended unless it already contains it."""
        res = f"{self.width}x{self.height}"
        return self.display_name if res in self.display_name else f"{self.display_name} {res}"


@dataclass(frozen=True)
class Capabilities:
    """Protocol capabilities."""

    passive_battery: bool
    session_battery: bool
    session_temperature: bool
    model_detection: bool
    palettes: tuple[str, ...]


@dataclass
class AdvertisementInfo:
    """Information extracted from a Bluetooth advertisement."""

    battery_mv: int | None = None
    model_key: str | None = None
    sw_version: str | None = None
    hw_version: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class WriteResult:
    """Result of writing an image or querying status."""

    success: bool
    battery_mv: int | None = None
    temperature_c: int | None = None
    error: str | None = None


def battery_percent(volts: float, min_v: float, max_v: float) -> int:
    """Linear map of a cell voltage onto 0-100 %, clamped."""
    pct = (volts - min_v) * 100.0 / (max_v - min_v)
    return max(0, min(100, round(pct)))


class BleParser(BluetoothData, ABC):
    """Base class for protocol-specific Bluetooth advertisement parsers.

    Subclasses set `brand` and `fallback_name`, provide `is_advertisement`
    (the protocol's advertisement matcher) and override `_parse()` to update
    sensors from the advertisement. Device naming, preset tracking and the
    update skeleton live here.
    """

    #: Brand the tags are sold under (HA device manufacturer).
    brand: str
    #: Shown as the model name until a preset is known.
    fallback_name: str

    def __init__(self, preset: DevicePreset | None = None) -> None:
        super().__init__()
        self.preset = preset
        self.last_service_info: BluetoothServiceInfoBleak | None = None

    @staticmethod
    @abstractmethod
    def is_advertisement(service_info: BluetoothServiceInfoBleak) -> bool:
        """Return True if this advertisement belongs to the protocol."""

    def supported(self, data: BluetoothServiceInfoBleak) -> bool:
        """Return True if this advertisement is from a device of this protocol."""
        return self.is_advertisement(data)

    def set_preset(self, preset: DevicePreset) -> None:
        """Update active device preset and re-derive the device naming."""
        self.preset = preset
        if self.last_service_info is not None:
            self._update_device_info(self.last_service_info)

    def _update_device_info(self, service_info: BluetoothServiceInfoBleak) -> None:
        identifier = service_info.address.replace(":", "")[-8:]
        if self.preset is None:
            display_name, model = self.fallback_name, self.fallback_name
        else:
            display_name, model = self.preset.display_name, self.preset.model_name
        self.set_title(f"{identifier} ({display_name})")
        self.set_device_name(f"{self.brand} {identifier}")
        self.set_device_type(model)
        self.set_device_manufacturer(self.brand)

    def _start_update(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Update from BLE advertisement data."""
        if not self.is_advertisement(service_info):
            return
        self.last_service_info = service_info
        self._update_device_info(service_info)
        self._parse(service_info)

    def _parse(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Update sensors from the advertisement. Default: nothing to read."""

    def update_battery(self, volts: float, min_v: float, max_v: float) -> None:
        """Publish voltage, percentage and battery-low from a passive reading."""
        self.update_predefined_sensor(SensorLibrary.VOLTAGE__ELECTRIC_POTENTIAL_VOLT, volts)
        self.update_predefined_sensor(
            SensorLibrary.BATTERY__PERCENTAGE, battery_percent(volts, min_v, max_v)
        )
        self.update_predefined_binary_sensor(BinarySensorDeviceClass.BATTERY, volts <= min_v)


class BleBackend(ABC):
    """Abstract base class for ESL BLE backends.

    A backend is mostly declarative: `PRESETS` and `parser_cls` drive the
    preset/parser/advertisement methods, and the write path is implemented
    here on top of two protocol-specific hooks, `prepare_image()` (the
    CPU-bound encode) and `write_session()` (the transfer over an open
    link). `parse_advertisement()` and, where the advertisement identifies
    the model, `refine_preset()` are the remaining per-protocol pieces.
    """

    id: str
    name: str
    #: Brand the tags are sold under (shown as HA device manufacturer).
    brand: str
    capabilities: Capabilities
    PRESETS: Mapping[str, DevicePreset]
    parser_cls: type[BleParser]

    def presets(self) -> Mapping[str, DevicePreset]:
        """Return device presets supported by this protocol."""
        return self.PRESETS

    def supported(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Return True if this advertisement belongs to this protocol."""
        return self.parser_cls.is_advertisement(service_info)

    def create_parser(self, preset: DevicePreset | None = None) -> BleParser:
        """Return an advertisement parser bound to this preset."""
        return self.parser_cls(preset=preset)

    def refine_preset(
        self, preset: DevicePreset, info: AdvertisementInfo | None
    ) -> DevicePreset:
        """Refine preset using advertisement info (e.g. firmware quirks). Default is identity."""
        return preset

    @abstractmethod
    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Extract advertisement data from service info."""

    # ── Write path ───────────────────────────────────────────────────────

    def prepare_image(
        self, preset: DevicePreset, image: Image.Image, address: str
    ) -> Any:
        """Encode an image into whatever write_session() sends.

        CPU-bound and synchronous; callers run it in a worker thread, once
        per write, before taking the BLE lock. The default passes the image
        through, for a backend that overrides write_image() wholesale.
        """
        return image

    async def write_session(
        self,
        client: BleakClient,
        address: str,
        preset: DevicePreset,
        prepared: Awaitable[Any],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Transfer an image over an open link.

        `prepared` is the encode; await it only once any pre-transfer
        handshake that can be done without it is finished, so encoding
        overlaps connecting. Raise on protocol errors; write_prepared()
        converts exceptions to a failed WriteResult. A backend implements
        this or overrides write_image() itself.
        """
        raise NotImplementedError(f"{type(self).__name__} implements neither write_session nor write_image")

    async def write_prepared(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        prepared: Awaitable[Any],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Connect and write an already-scheduled encode.

        `prepared` is owned by the caller and may be awaited again on a
        retry. Every failure, including connecting, becomes a failed
        WriteResult so it counts toward retries and the failure sensors.
        """
        try:
            async with ble_session(ble_device) as client:
                return await self.write_session(
                    client,
                    ble_device.address,
                    preset,
                    prepared,
                    attempt=attempt,
                    write_delay_ms=write_delay_ms,
                )
        except Exception as exc:
            # The caller logs each failed attempt and raises after the last
            # one; keep the traceback at debug level without a second ERROR.
            _LOGGER.debug("Write to %s failed", ble_device.address, exc_info=exc)
            return WriteResult(success=False, error=str(exc) or type(exc).__name__)

    async def write_image(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        image: Image.Image,
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Encode and write an image in one step.

        The encode runs in a worker thread concurrently with connecting:
        the event loop stays free, the radio starts immediately (sleepy
        tags have short advertising windows), and the link is held only
        for whatever part of the encode outlasts the connect.
        """
        encode = asyncio.create_task(
            asyncio.to_thread(self.prepare_image, preset, image, ble_device.address)
        )
        try:
            return await self.write_prepared(
                ble_device, preset, encode, attempt=attempt, write_delay_ms=write_delay_ms
            )
        finally:
            encode.cancel()  # no-op once awaited; drops the result if connect failed

    async def read_status(
        self, ble_device: BLEDevice, preset: DevicePreset
    ) -> WriteResult:
        """Optional status query without writing an image."""
        return WriteResult(success=False, error="not supported")


# Backwards compatibility aliases
ProtocolParser = BleParser
ProtocolBackend = BleBackend
