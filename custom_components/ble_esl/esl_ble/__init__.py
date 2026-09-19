"""BLE plugin registry for BLE ESL ESL."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import (
    CONFIDENCE_COMMUNITY,
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
    AdvertisementInfo,
    BleBackend,
    BleParser,
    Capabilities,
    DevicePreset,
    ProtocolContractError,
    WriteResult,
)
from .easytag import EasyTagBleBackend
from .picksmart import PickSmartBleBackend
from .poshiji import PoshijiBleBackend
from .wolink import WolinkBleBackend

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

_BACKENDS: dict[str, BleBackend] = {}


def register(backend: BleBackend) -> None:
    """Register a BLE backend (the class-level contract is checked at definition time)."""
    if backend.id in _BACKENDS and _BACKENDS[backend.id] is not backend:
        raise ProtocolContractError(
            f"backend id {backend.id!r} is already registered by "
            f"{type(_BACKENDS[backend.id]).__name__}"
        )
    _BACKENDS[backend.id] = backend


def get(backend_id: str) -> BleBackend:
    """Retrieve a BLE backend by ID."""
    if backend_id not in _BACKENDS:
        raise KeyError(f"Unknown BLE backend: {backend_id!r}. Available: {list(_BACKENDS.keys())}")
    return _BACKENDS[backend_id]


def all_backends() -> list[BleBackend]:
    """Return all registered BLE backends."""
    return list(_BACKENDS.values())


def detect(
    service_info: BluetoothServiceInfoBleak,
) -> BleBackend | None:
    """Detect matching BLE backend from advertisement.

    Backends are checked in registration order; backends should define mutually
    exclusive supported() matchers to avoid ambiguous backend resolution.
    """
    for backend in _BACKENDS.values():
        if backend.supported(service_info):
            return backend
    return None


# Register standard backends
register(WolinkBleBackend())
register(EasyTagBleBackend())
register(PickSmartBleBackend())
register(PoshijiBleBackend())

__all__ = [
    "CONFIDENCE_COMMUNITY",
    "CONFIDENCE_ESTIMATED",
    "CONFIDENCE_HARDWARE",
    "CONFIDENCE_REPORTED",
    "AdvertisementInfo",
    "BleBackend",
    "BleParser",
    "Capabilities",
    "DevicePreset",
    "EasyTagBleBackend",
    "PickSmartBleBackend",
    "PoshijiBleBackend",
    "ProtocolContractError",
    "WolinkBleBackend",
    "WriteResult",
    "all_backends",
    "detect",
    "get",
    "register",
]
