"""Test configuration: real Home Assistant via pytest-homeassistant-custom-component.

Protocol/codec/session tests need no fixtures from here. Integration-level
tests use `wolink_entry` (a loaded config entry for a WOLINK tag whose
advertisement the bluetooth integration has seen) and `tag_writer` (the
protocol's write path and the renderer stubbed out, steerable per test).
"""

# <!-- hass-standards:domain-fixtures:start -->
# Use pytest_homeassistant_custom_component.common.MockConfigEntry for
# mock_config_entry when the integration uses config entries.
# Define mock_client only when an external communication client is present.
# Mock external communication boundaries, never Home Assistant core modules.
# Keep integration-specific fixtures below this managed block.
# <!-- hass-standards:domain-fixtures:end -->

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import partial
import time
from typing import Any
from unittest.mock import AsyncMock, patch

from bleak.backends.device import BLEDevice
from blesession import Unreachable, attempts as attempts_mod
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ble_esl import services as svc
from custom_components.ble_esl.const import CONF_MODEL, CONF_PROTOCOL, DOMAIN
from custom_components.ble_esl.esl_ble.base import WriteResult
from custom_components.ble_esl.esl_ble.wolink import WolinkProtocol
from custom_components.ble_esl.esl_ble.wolink.const import MANUFACTURER_ID as WOLINK_MFR_ID
from tests.components.ble_esl.bt import inject_bluetooth_service_info, service_info
from tests.components.ble_esl.writes import Scripted, ok, play

ADDRESS = "66:66:54:20:00:55"
IDENT = "54200055"
# PID=0x1234, AppVer=0x0201 (513), HwVer=0x0403 (1027), DispVer=0x0605 (1541), battery 3000 mV
WOLINK_MFR_BYTES = bytes([0x12, 0x34, 0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x0B, 0xB8])


@pytest.fixture(autouse=True)
def enable_event_loop_debug() -> None:
    """Replace the plugin's fixture of the same name.

    Many codec/session tests drive coroutines with asyncio.run(), which leaves no
    current event loop behind. Older plugin releases (the minimum-HA CI job) call
    get_event_loop() unconditionally, so every following test errored in setup.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.set_debug(True)


def wolink_service_info(
    address: str = ADDRESS, mfr_bytes: bytes = WOLINK_MFR_BYTES, *, rssi: int = -60
):
    """A WOLINK tag's advertisement."""
    return service_info(
        address, name="WOLINK", manufacturer_data={WOLINK_MFR_ID: mfr_bytes}, rssi=rssi
    )


async def setup_entry(
    hass: HomeAssistant,
    *,
    address: str = ADDRESS,
    protocol: str = "wolink",
    model: str = "290",
    options: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    advertise: bool = True,
) -> MockConfigEntry:
    """Create and load a config entry for a tag (advertised first, like real discovery)."""
    if advertise:
        inject_bluetooth_service_info(hass, wolink_service_info(address))
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=address,
        title=f"Zhsunyco {address.replace(':', '')[-8:]}",
        data={CONF_PROTOCOL: protocol, CONF_MODEL: model, **(data or {})},
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def device_of(hass: HomeAssistant, address: str = ADDRESS) -> dr.DeviceEntry:
    """The HA device of a tag."""
    registry = dr.async_get(hass)
    connections = {(CONNECTION_BLUETOOTH, address)}
    if hasattr(registry, "async_get_devices"):
        devices = list(registry.async_get_devices(connections=connections))
    else:  # Home Assistant before the multi-entry device lookup (minimum support)
        devices = [d for d in [registry.async_get_device(connections=connections)] if d]
    assert len(devices) == 1, devices
    return devices[0]


def device_id_of(hass: HomeAssistant, address: str = ADDRESS) -> str:
    """The HA device id of a tag, as services are targeted."""
    return device_of(hass, address).id


@pytest.fixture
async def wolink_entry(hass: HomeAssistant, enable_bluetooth: None) -> MockConfigEntry:
    """A loaded WOLINK 2.9" entry whose advertisement bluetooth has seen."""
    return await setup_entry(hass)


@dataclass
class TagWriter:
    """Stubbed write path of the WOLINK protocol, steerable per test.

    The real pipeline (services, lock, debounce, retries, the report, sensors)
    runs; only the encode and the BLE transfer are replaced. Like a real
    protocol, the stub awaits the encode future before "writing", times its
    stages on the trace it is handed and raises on failure — from
    `write_result` (a `writes.Scripted`, or a WriteResult) or `write_hook`
    (called with the trace; may return either or raise itself).
    """

    write_prepared: AsyncMock
    available: bool = True
    write_result: Scripted | WriteResult = field(default_factory=lambda: ok(transfer=0.1))
    write_hook: Callable[..., Awaitable[Scripted | WriteResult]] | None = None
    encoded: list[str] = field(default_factory=list)
    """Addresses whose image has been encoded (prepare_image ran), in order."""

    def sent_image(self, call_index: int = -1) -> Image.Image:
        """The image handed to the protocol on the n-th write."""
        return self.write_prepared.await_args_list[call_index].args[2].result()


@pytest.fixture
def tag_writer() -> TagWriter:
    """Stub the WOLINK protocol's encode/transfer and the renderer."""
    writer = TagWriter(write_prepared=AsyncMock())

    async def fake_write_prepared(ble_device, preset, prepared, **kwargs):
        image = await prepared
        if writer.write_hook is not None:
            outcome = await writer.write_hook(ble_device, preset, image, **kwargs)
        else:
            outcome = writer.write_result
        return play(outcome, kwargs["trace"])

    writer.write_prepared.side_effect = fake_write_prepared

    def identity_prepare(preset, image, address):
        # Keep the encode future *pending* when the write starts, as on a
        # loaded machine, so the await-after-connect path is exercised.
        time.sleep(0.02)
        writer.encoded.append(address)
        return image

    def fake_ble_device(hass, address, **kwargs):
        """blesession.hass.ble_device_or_raise, as the integration imported it."""
        if not writer.available:
            raise Unreachable(address)
        return BLEDevice(address, "WOLINK", {})

    def fake_render(hass, preset, payload, *, rotate=0, background="white"):
        img = Image.new("RGB", (preset.width, preset.height), "white")
        img.putpixel((0, 0), (len(str(payload)) % 256, 0, 0))
        return img

    with (
        patch.object(WolinkProtocol, "write_prepared", writer.write_prepared),
        patch.object(WolinkProtocol, "prepare_image", staticmethod(identity_prepare)),
        patch.object(svc, "render_image", fake_render),
        patch.object(svc, "ble_device_or_raise", fake_ble_device),
        patch.object(attempts_mod, "sleep", AsyncMock()),  # the retry pause
    ):
        yield writer


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A real HA config entry for the documented WOLINK 2.9-inch device."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        title=f"Zhsunyco {IDENT}",
        data={CONF_PROTOCOL: "wolink", CONF_MODEL: "290"},
    )


@pytest.fixture
async def payload_example_setup(hass, enable_bluetooth, mock_config_entry):
    """Load the actual integration and actions without sending a BLE command."""
    inject_bluetooth_service_info(hass, wolink_service_info())
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "write")
    assert hass.states.get(f"image.zhsunyco_{IDENT}_preview_content") is not None
    return mock_config_entry


@pytest.fixture
def payload_example_adapter(payload_example_setup):
    """Bind real schema-normalized payloads to the production renderer."""

    def adapter(hass, example_metadata, normalized_action, schema_data):
        # Ordinary regressions do not need the optional central collector installed.
        from hass_standards_payload import PreparedPayload

        from custom_components.ble_esl.renderer import PALETTES, _make_context, render_image
        from custom_components.ble_esl.yaml11 import repair_yaml11_keys

        preset = payload_example_setup.runtime_data.preset
        payload = repair_yaml11_keys(schema_data["payload"])
        rotate = schema_data.get("rotate", 0)
        background = schema_data.get("background", "white")
        return PreparedPayload(
            payload=payload,
            context=_make_context(
                hass, default_font="NotoSansKR-Regular.ttf", palette=PALETTES[preset.colors]
            ),
            render_options={
                "width": preset.width,
                "height": preset.height,
                "rotate": rotate,
                "rotate_mode": "canvas",
                "background": background,
                "dither": False,
            },
            prepare=partial(
                render_image, hass, preset, payload, rotate=rotate, background=background
            ),
        )

    return adapter
