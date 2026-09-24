"""Common base classes and data structures for protocol backends."""

from __future__ import annotations

from abc import ABC
import asyncio
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any

from bleak import BleakClient
from blesession import SessionTrace, ble_session, stages
from bluetooth_sensor_state_data import BluetoothData
from sensor_state_data import BinarySensorDeviceClass, SensorLibrary

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak
    from PIL import Image

_LOGGER = logging.getLogger(__name__)

ATTEMPT_TIMEOUT_S = 600.0
"""Upper bound on one write attempt, connecting included (applied by the
integration's run_attempts()).

Every protocol step has its own timeout, but a GATT write has none: a
proxy that dies mid-transfer can leave the attempt hanging, and since it
holds the BLE lock, every other tag's writes hang with it. The bound is
generous so it never cuts a legitimate write, even the slowest: connecting
retries for up to ~1.5 min, a 13.3" WOLINK image takes ~1 min to transfer
(more on a paced retry) and up to 2 min to refresh — about 5 min in all.
"""

# The stages a write goes through, as the writers time them on the
# SessionTrace. `connect`, `session` and `disconnect` come from
# blesession.ble_session(); the rest are the protocol's own. Every protocol
# has the same shape — a handshake before the data, the data transfer, and
# a wait for the tag to confirm — so tuning advice carries over between
# them:
#
#     handshake   START / authentication / size command
#     transfer    sending the image data
#     finish      from the last data frame to the tag's completion reply:
#                 the panel refresh on WOLINK and easyTag, the end-command
#                 reply on XTE
#
# `handshake` is the tag's name for blesession's `auth` stage; the report
# shows `failed_stage: auth, failed_detail: handshake`. Facts the writers
# note beside the stages: `settle_s` (pause after subscribing), `parts`,
# `bytes`, and protocol extras (PickSmart's probe/resend counters, ...).
STAGE_HANDSHAKE = "handshake"
STAGE_TRANSFER = stages.TRANSFER
STAGE_FINISH = stages.FINISH
STAGE_MAP = {STAGE_HANDSHAKE: stages.AUTH}

RETRY_BACKOFF_S = 0.05
"""Extra pause between packets, per earlier attempt that failed mid-transfer.

A marginal link shows up as a failure *during* the data transfer (a stalled
or unexpected reply, a dropped write); slowing the next attempt's packets
gives it slack. A failure to connect, to get through the handshake or to
see the panel finish is not helped by pacing, so those retries run at
full speed. The integration turns this into `pacing_s` for the writers.
"""

# Battery % is a linear map of the cell voltage over this range, and at or
# below the minimum the battery-low binary sensor turns on. Below 2.5 V
# e-paper refresh becomes unreliable even though BLE still works; the same
# range applies to every backend that reports a voltage (advertised: PickSmart,
# WOLINK; session-polled: easyTag) so the percentages are comparable across
# tags. A preset may override it via extra["min_voltage"] / extra["max_voltage"].
BATTERY_MIN_VOLTAGE = 2.5
BATTERY_MAX_VOLTAGE = 2.9

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
    """What a successful write (or a status query) reported.

    Where the time went and, on a failure, where it died is on the
    SessionTrace the caller passed in, not here: a failed write raises.
    """

    success: bool
    battery_mv: int | None = None
    temperature_c: int | None = None
    error: str | None = None
    """Only for read_status() on a protocol without one ("not supported")."""


class WriteRefused(Exception):
    """A backend declined the write before connecting (see XTE): a preset or
    tag it cannot encode for. Not a BLE failure, and not worth retrying."""


def battery_percent(volts: float, min_v: float, max_v: float) -> int:
    """Linear map of a cell voltage onto 0-100 %, clamped."""
    pct = (volts - min_v) * 100.0 / (max_v - min_v)
    return max(0, min(100, round(pct)))


class ProtocolContractError(TypeError):
    """A backend or parser class does not satisfy the protocol contract.

    Raised when the class is *defined* (import time), listing everything
    that is missing, so an incomplete protocol package can never load.
    """


def _missing_attrs(cls: type, names: tuple[str, ...]) -> list[str]:
    """Names not set on the class, or set to an empty string."""
    problems = []
    for name in names:
        if not hasattr(cls, name):
            problems.append(f"class attribute '{name}'")
        elif getattr(cls, name) == "":
            problems.append(f"class attribute '{name}' is empty")
    return problems


def _overrides(cls: type, base: type, name: str) -> bool:
    return getattr(cls, name) is not getattr(base, name)


class BleParser(BluetoothData, ABC):
    """Base class for protocol-specific Bluetooth advertisement parsers.

    Contract (checked when the subclass is defined):
      required  brand, fallback_name, is_advertisement
      optional  _parse()  — sensor readings from the advertisement

    Device naming, preset tracking and the update skeleton live here.
    """

    #: Brand the tags are sold under (HA device manufacturer).
    brand: str
    #: Shown as the model name until a preset is known.
    fallback_name: str

    REQUIRED = ("brand", "fallback_name")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        problems = _missing_attrs(cls, cls.REQUIRED)
        if not _overrides(cls, BleParser, "is_advertisement"):
            problems.append("is_advertisement not provided")
        if problems:
            raise ProtocolContractError(f"{cls.__name__} is missing: " + "; ".join(problems))

    def __init__(self, preset: DevicePreset | None = None) -> None:
        super().__init__()
        self.preset = preset
        self.last_service_info: BluetoothServiceInfoBleak | None = None

    @staticmethod
    def is_advertisement(service_info: BluetoothServiceInfoBleak) -> bool:
        """Return True if this advertisement belongs to the protocol."""
        raise NotImplementedError

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

    def update_battery(
        self, volts: float, min_v: float = BATTERY_MIN_VOLTAGE, max_v: float = BATTERY_MAX_VOLTAGE
    ) -> None:
        """Publish voltage, percentage and battery-low from a passive reading."""
        self.update_predefined_sensor(SensorLibrary.VOLTAGE__ELECTRIC_POTENTIAL_VOLT, volts)
        self.update_predefined_sensor(
            SensorLibrary.BATTERY__PERCENTAGE, battery_percent(volts, min_v, max_v)
        )
        self.update_predefined_binary_sensor(BinarySensorDeviceClass.BATTERY, volts <= min_v)


class BleBackend(ABC):
    """A protocol backend: declarative class attributes plus a few hooks.

    Contract (checked when the subclass is defined, see __init_subclass__):

      required class attributes
        id            registry / options key, lowercase, unique
        label         short protocol name shown as the HA model_id ("WOLINK")
        name          protocol name shown in the config UI
        capabilities  Capabilities
        PRESETS       non-empty mapping key -> DevicePreset, key == preset.key
        parser_cls    BleParser subclass (also supplies `brand`)
      required hooks
        parse_advertisement(service_info) -> AdvertisementInfo | None
        write path: prepare_image() *and* write_session(), or override
                    write_image() wholesale
      optional (defaults provided)
        refine_preset()   when the advertisement identifies the model
        write_prepared()  to refuse before connecting (raise WriteRefused; see XTE)
        read_status()     status query without a write

    presets() / preset_for() / supported() / create_parser() / brand are
    derived from the class attributes and should not be overridden.
    """

    id: str
    label: str
    name: str
    capabilities: Capabilities
    PRESETS: Mapping[str, DevicePreset]
    parser_cls: type[BleParser]

    REQUIRED = ("id", "label", "name", "capabilities", "PRESETS", "parser_cls")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Every check is independent so one message lists everything to fix.
        problems = _missing_attrs(cls, cls.REQUIRED)
        parser_cls = getattr(cls, "parser_cls", None)
        if parser_cls is not None and not (
            isinstance(parser_cls, type) and issubclass(parser_cls, BleParser)
        ):
            problems.append("parser_cls must be a BleParser subclass")
        presets = getattr(cls, "PRESETS", None)
        if presets is not None:
            if not presets:
                problems.append("PRESETS is empty")
            else:
                problems += [
                    f"PRESETS[{k!r}].key is {v.key!r}" for k, v in presets.items() if k != v.key
                ]
                if (caps := getattr(cls, "capabilities", None)) is not None:
                    problems += [
                        f"PRESETS[{k!r}].colors {v.colors!r} not in capabilities.palettes"
                        for k, v in presets.items()
                        if v.colors not in caps.palettes
                    ]
        if not _overrides(cls, BleBackend, "parse_advertisement"):
            problems.append("parse_advertisement() not implemented")
        has_hooks = _overrides(cls, BleBackend, "prepare_image") and _overrides(
            cls, BleBackend, "write_session"
        )
        if not has_hooks and not _overrides(cls, BleBackend, "write_image"):
            problems.append(
                "write path: implement prepare_image() and write_session(), "
                "or override write_image()"
            )
        if problems:
            raise ProtocolContractError(f"{cls.__name__} is missing: " + "; ".join(problems))

    # ── Derived from the class attributes ────────────────────────────────

    @property
    def brand(self) -> str:
        """Brand the tags are sold under (shown as HA device manufacturer)."""
        return self.parser_cls.brand

    def presets(self) -> Mapping[str, DevicePreset]:
        """Return device presets supported by this protocol."""
        return self.PRESETS

    def preset_for(self, model_key: str | None) -> DevicePreset:
        """The preset for a configured model key, or the first preset if unknown.

        A stale or foreign key (e.g. the WOLINK-centric DEFAULT_MODEL on
        another protocol) degrades to the protocol's first preset rather
        than failing setup.
        """
        preset = self.PRESETS.get(model_key) if model_key else None
        return preset if preset is not None else next(iter(self.PRESETS.values()))

    def supported(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Return True if this advertisement belongs to this protocol."""
        return self.parser_cls.is_advertisement(service_info)

    def create_parser(self, preset: DevicePreset | None = None) -> BleParser:
        """Return an advertisement parser bound to this preset."""
        return self.parser_cls(preset=preset)

    # ── Hooks ────────────────────────────────────────────────────────────

    def refine_preset(self, preset: DevicePreset, info: AdvertisementInfo | None) -> DevicePreset:
        """Refine preset using advertisement info (e.g. firmware quirks). Default is identity."""
        return preset

    def parse_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> AdvertisementInfo | None:
        """Extract advertisement data from service info."""
        raise NotImplementedError

    def prepare_image(self, preset: DevicePreset, image: Image.Image, address: str) -> Any:
        """Encode an image into whatever write_session() sends.

        CPU-bound and synchronous; callers run it in a worker thread, once
        per write, before taking the BLE lock. Usually
        `prepare_image = staticmethod(writer.prepare)`.
        """
        raise NotImplementedError

    async def write_session(
        self,
        client: BleakClient,
        address: str,
        preset: DevicePreset,
        prepared: Awaitable[Any],
        *,
        pacing_s: float = 0.0,
        trace: SessionTrace,
    ) -> WriteResult:
        """Transfer an image over an open link.

        `prepared` is the encode; await it only once any pre-transfer
        handshake that can be done without it is finished, so encoding
        overlaps connecting. Time the protocol's stages on `trace`
        (STAGE_HANDSHAKE / STAGE_TRANSFER / STAGE_FINISH) and note its
        facts there; raise on protocol errors. Usually
        `write_session = staticmethod(writer.write_session)`.
        """
        raise NotImplementedError

    # ── Write path (shared) ──────────────────────────────────────────────

    def new_trace(self) -> SessionTrace:
        """A trace that knows this protocol's stage names."""
        return SessionTrace(STAGE_MAP)

    async def write_prepared(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        prepared: Awaitable[Any],
        *,
        pacing_s: float = 0.0,
        trace: SessionTrace | None = None,
    ) -> WriteResult:
        """Connect and write an already-scheduled encode.

        `prepared` is owned by the caller and may be awaited again on a
        retry. Every failure raises — connecting included — with the stage
        it happened in recorded on `trace`; the integration's attempt loop
        turns that into the failure sensors and decides about a retry.
        """
        trace = trace if trace is not None else self.new_trace()
        async with ble_session(ble_device, trace=trace) as client:
            return await self.write_session(
                client,
                ble_device.address,
                preset,
                prepared,
                pacing_s=pacing_s,
                trace=trace,
            )

    async def write_image(
        self,
        ble_device: BLEDevice,
        preset: DevicePreset,
        image: Image.Image,
        *,
        pacing_s: float = 0.0,
        trace: SessionTrace | None = None,
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
                ble_device, preset, encode, pacing_s=pacing_s, trace=trace
            )
        finally:
            encode.cancel()  # no-op once awaited; drops the result if connect failed

    async def read_status(self, ble_device: BLEDevice, preset: DevicePreset) -> WriteResult:
        """Optional status query without writing an image."""
        return WriteResult(success=False, error="not supported")
