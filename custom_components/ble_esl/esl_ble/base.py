"""Common base classes and data structures for protocol backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
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
        """Write an image to the device."""

    async def read_status(
        self, ble_device: BLEDevice, preset: DevicePreset
    ) -> WriteResult:
        """Optional status query without writing an image."""
        return WriteResult(success=False, error="not supported")


# Backwards compatibility aliases
ProtocolParser = BleParser
ProtocolBackend = BleBackend
