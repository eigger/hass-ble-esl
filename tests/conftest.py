"""Test configuration: real Home Assistant via pytest-homeassistant-custom-component.

Protocol/codec/session tests need no fixtures from here. Integration-level
tests use `wolink_entry` (a loaded config entry for a WOLINK tag whose
advertisement the bluetooth integration has seen) and `tag_writer` (the
backend's write path and the renderer stubbed out, steerable per test).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import time
from typing import Any
from unittest.mock import AsyncMock, patch

from bleak.backends.device import BLEDevice
from bt import inject_bluetooth_service_info, service_info
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ble_esl import services as svc
from custom_components.ble_esl.const import CONF_MODEL, CONF_PROTOCOL, DOMAIN
from custom_components.ble_esl.esl_ble.base import WriteResult
from custom_components.ble_esl.esl_ble.wolink import WolinkBleBackend
from custom_components.ble_esl.esl_ble.wolink.const import MANUFACTURER_ID as WOLINK_MFR_ID

ADDRESS = "66:66:54:20:00:55"
IDENT = "54200055"
# PID=0x1234, AppVer=258, HwVer=772, DispVer=0x0506, battery 3000 mV
WOLINK_MFR_BYTES = bytes([0x12, 0x34, 0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x0B, 0xB8])


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> None:
    """Let Home Assistant load custom_components/ble_esl — only for tests that
    use `hass`, so codec/session tests do not start a Home Assistant at all."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")


def wolink_service_info(address: str = ADDRESS, mfr_bytes: bytes = WOLINK_MFR_BYTES):
    """A WOLINK tag's advertisement."""
    return service_info(address, name="WOLINK", manufacturer_data={WOLINK_MFR_ID: mfr_bytes})


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
    devices = dr.async_get(hass).async_get_devices(connections={(CONNECTION_BLUETOOTH, address)})
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
    """Stubbed write path of the WOLINK backend, steerable per test.

    The real pipeline (services, lock, debounce, retries, sensors) runs; only
    the encode and the BLE transfer are replaced. Like a real backend, the
    stub awaits the encode future before "writing".
    """

    write_prepared: AsyncMock
    available: bool = True
    write_result: WriteResult = field(default_factory=lambda: WriteResult(success=True))
    write_hook: Callable[..., Awaitable[WriteResult]] | None = None
    encoded: list[str] = field(default_factory=list)
    """Addresses whose image has been encoded (prepare_image ran), in order."""

    def sent_image(self, call_index: int = -1) -> Image.Image:
        """The image handed to the backend on the n-th write."""
        return self.write_prepared.await_args_list[call_index].args[2].result()


@pytest.fixture
def tag_writer() -> TagWriter:
    """Stub the WOLINK backend's encode/transfer and the renderer."""
    writer = TagWriter(write_prepared=AsyncMock())

    async def fake_write_prepared(ble_device, preset, prepared, **kwargs):
        image = await prepared
        if writer.write_hook is not None:
            return await writer.write_hook(ble_device, preset, image, **kwargs)
        return writer.write_result

    writer.write_prepared.side_effect = fake_write_prepared

    def identity_prepare(preset, image, address):
        # Keep the encode future *pending* when the write starts, as on a
        # loaded machine, so the await-after-connect path is exercised.
        time.sleep(0.02)
        writer.encoded.append(address)
        return image

    def fake_render(hass, preset, payload, *, rotate=0, background="white"):
        img = Image.new("RGB", (preset.width, preset.height), "white")
        img.putpixel((0, 0), (len(str(payload)) % 256, 0, 0))
        return img

    with (
        patch.object(WolinkBleBackend, "write_prepared", writer.write_prepared),
        patch.object(WolinkBleBackend, "prepare_image", staticmethod(identity_prepare)),
        patch.object(svc, "render_image", fake_render),
        patch.object(
            svc,
            "async_ble_device_from_address",
            lambda hass, address: BLEDevice(address, "WOLINK", {}) if writer.available else None,
        ),
        patch.object(svc, "sleep", AsyncMock()),  # retry backoff
    ):
        yield writer
