"""Common base classes and data structures for protocol backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bluetooth_sensor_state_data import BluetoothData

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image

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


class BleParser(BluetoothData, ABC):
    """Base class for protocol-specific Bluetooth advertisement parsers."""

    @abstractmethod
    def set_preset(self, preset: DevicePreset) -> None:
        """Update active device preset on the parser."""


class BleBackend(ABC):
    """Abstract base class for ESL BLE backends."""

    id: str
    name: str
    #: Brand the tags are sold under (shown as HA device manufacturer).
    brand: str
    capabilities: Capabilities

    @abstractmethod
    def presets(self) -> Mapping[str, DevicePreset]:
        """Return device presets supported by this protocol."""

    @abstractmethod
    def supported(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Return True if this advertisement belongs to this protocol."""

    @abstractmethod
    def create_parser(
        self, preset: DevicePreset | None = None
    ) -> BleParser:
        """Return an advertisement parser bound to this preset."""

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

    @abstractmethod
    async def write_image(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        image: Image.Image,
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Encode and write an image to the device in one step."""

    def prepare_image(
        self, preset: DevicePreset, image: Image.Image, address: str
    ) -> Any:
        """Encode an image into whatever write_prepared() sends.

        CPU-bound and synchronous; the caller runs it in a worker thread,
        once per write, before taking the BLE lock. The default keeps the
        image as-is for backends that encode inside write_image().
        """
        return image

    async def write_prepared(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        prepared: Awaitable[Any],
        *,
        attempt: int = 1,
        write_delay_ms: int = 0,
    ) -> WriteResult:
        """Write the result of prepare_image() to the device.

        `prepared` is awaited only after the connection is up, so encoding
        overlaps connecting; awaiting it again on a retry reuses the result.
        """
        return await self.write_image(
            ble_device,
            preset,
            await prepared,
            attempt=attempt,
            write_delay_ms=write_delay_ms,
        )

    async def read_status(
        self, ble_device: BLEDevice, preset: DevicePreset
    ) -> WriteResult:
        """Optional status query without writing an image."""
        return WriteResult(success=False, error="not supported")


# Backwards compatibility aliases
ProtocolParser = BleParser
ProtocolBackend = BleBackend
