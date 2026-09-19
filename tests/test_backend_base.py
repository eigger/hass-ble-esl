"""Tests for the shared BleParser / BleBackend behaviour in esl_ble/base.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ble_esl.esl_ble import session
from custom_components.ble_esl.esl_ble.base import (
    BleBackend,
    BleParser,
    Capabilities,
    DevicePreset,
    WriteResult,
    battery_percent,
)

PRESET = DevicePreset(key="p", display_name="Panel 2.9\"", width=296, height=128)
PRESET_WITH_RES = DevicePreset(key="q", display_name="Panel 296x128", width=296, height=128)


@pytest.mark.parametrize(
    ("volts", "expected"),
    [(3.0, 100), (2.6, 50), (2.2, 0), (3.4, 100), (1.9, 0), (2.61, 51)],
)
def test_battery_percent_linear_clamped(volts, expected):
    assert battery_percent(volts, 2.2, 3.0) == expected


class _Parser(BleParser):
    brand = "Acme"
    fallback_name = "Generic"
    is_advertisement = staticmethod(lambda info: info.name == "yes")


def _info(name="yes", address="66:66:54:20:00:55"):
    info = MagicMock()
    info.name = name
    info.address = address
    info.manufacturer_data = {}
    info.service_uuids = []
    return info


def test_parser_naming_with_and_without_preset():
    parser = _Parser()
    parser.update(_info())
    assert parser.title == "54200055 (Generic)"
    assert parser._device_name == "Acme 54200055"
    assert parser._device_type == "Generic"
    assert parser._device_manufacturer == "Acme"

    parser.set_preset(PRESET)  # re-derives naming from the last advertisement
    assert parser.title == "54200055 (Panel 2.9\")"
    assert parser._device_type == "Panel 2.9\" 296x128"

    parser.set_preset(PRESET_WITH_RES)  # resolution already in the name: not repeated
    assert parser._device_type == "Panel 296x128"


def test_parser_ignores_foreign_advertisements():
    parser = _Parser(PRESET)
    parser.update(_info(name="no"))
    assert parser.last_service_info is None
    assert parser.title is None


class _Backend(BleBackend):
    id = "t"
    name = "Test"
    brand = "Acme"
    capabilities = Capabilities(False, False, False, False, ("BW",))
    PRESETS = {PRESET.key: PRESET}
    parser_cls = _Parser

    def parse_advertisement(self, service_info):
        return None


def test_backend_declarative_defaults():
    backend = _Backend()
    assert backend.presets() is _Backend.PRESETS
    assert isinstance(backend.create_parser(PRESET), _Parser)
    assert backend.supported(_info()) and not backend.supported(_info(name="no"))
    assert backend.prepare_image(PRESET, "img", "aa") == "img"  # pass-through default


def test_backend_without_write_session_reports_not_implemented(monkeypatch):
    """A backend that implements neither hook fails cleanly, not with a traceback."""

    async def _test():
        client = MagicMock(is_connected=False)
        monkeypatch.setattr(session, "establish_connection", AsyncMock(return_value=client))
        device = MagicMock(address="AA:BB:CC:DD:EE:FF")
        result = await _Backend().write_image(device, PRESET, "img")
        assert result.success is False
        assert "neither write_session nor write_image" in result.error

    asyncio.run(_test())


def test_write_prepared_wraps_session_errors_and_disconnects(monkeypatch):
    """Errors raised inside write_session become a failed WriteResult; the
    link is closed either way; the caller-owned encode future is untouched."""

    class Backend(_Backend):
        async def write_session(self, client, address, preset, prepared, **kwargs):
            assert address == "AA:BB:CC:DD:EE:FF"
            await prepared
            raise TimeoutError()  # empty str(): falls back to the type name

    async def _test():
        client = MagicMock(is_connected=True, disconnect=AsyncMock())
        monkeypatch.setattr(session, "establish_connection", AsyncMock(return_value=client))
        prepared = asyncio.get_running_loop().create_future()
        prepared.set_result(b"x")
        device = MagicMock(address="AA:BB:CC:DD:EE:FF")

        result = await Backend().write_prepared(device, PRESET, prepared)

        assert result == WriteResult(success=False, error="TimeoutError")
        client.disconnect.assert_awaited_once()
        assert prepared.done() and not prepared.cancelled()

    asyncio.run(_test())
