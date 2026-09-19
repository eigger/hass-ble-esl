"""Tests for the shared BleParser / BleBackend behaviour in esl_ble/base.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble import base
from custom_components.ble_esl.esl_ble.base import (
    BleBackend,
    BleParser,
    Capabilities,
    DevicePreset,
    ProtocolContractError,
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
    label = "T"
    name = "Test"
    capabilities = Capabilities(False, False, False, False, ("BWRY",))
    PRESETS = {PRESET.key: PRESET}
    parser_cls = _Parser

    def parse_advertisement(self, service_info):
        return None

    def prepare_image(self, preset, image, address):
        return image

    async def write_session(self, client, address, preset, prepared, **kwargs):
        return WriteResult(success=True)


def test_backend_declarative_defaults():
    backend = _Backend()
    assert backend.presets() is _Backend.PRESETS
    assert backend.brand == "Acme"  # from the parser class
    assert isinstance(backend.create_parser(PRESET), _Parser)
    assert backend.supported(_info()) and not backend.supported(_info(name="no"))


def _define(**attrs):
    """Define a backend subclass with the given class body; returns the error message or None."""
    body = dict(
        id="x", label="X", name="X", capabilities=_Backend.capabilities,
        PRESETS=_Backend.PRESETS, parser_cls=_Parser,
        parse_advertisement=lambda self, i: None,
        prepare_image=lambda self, p, i, a: i,
        write_session=_Backend.write_session,
    )
    body.update(attrs)
    for key, value in list(body.items()):
        if value is _REMOVE:
            del body[key]
    try:
        type("Probe", (BleBackend,), body)
    except ProtocolContractError as err:
        return str(err)
    return None


_REMOVE = object()


def test_contract_complete_backend_defines_cleanly():
    assert _define() is None


def test_contract_reports_every_missing_piece_at_definition_time():
    message = _define(label=_REMOVE, PRESETS={}, parse_advertisement=_REMOVE)
    assert "class attribute 'label'" in message
    assert "PRESETS is empty" in message
    assert "parse_advertisement() not implemented" in message


def test_contract_write_path_requires_hooks_or_write_image():
    assert "write path" in _define(prepare_image=_REMOVE)
    assert "write path" in _define(write_session=_REMOVE)

    async def write_image(self, *args, **kwargs):
        return WriteResult(success=True)

    assert _define(prepare_image=_REMOVE, write_session=_REMOVE, write_image=write_image) is None


def test_contract_validates_presets_against_class_attributes():
    bad_key = {"other": PRESET}
    assert "PRESETS['other'].key is 'p'" in _define(PRESETS=bad_key)
    bw_only = Capabilities(False, False, False, False, ("BW",))
    assert "not in capabilities.palettes" in _define(capabilities=bw_only)
    assert "parser_cls must be a BleParser subclass" in _define(parser_cls=object)


def test_contract_parser_requires_brand_name_and_matcher():
    with pytest.raises(ProtocolContractError, match="fallback_name"):
        type("P", (BleParser,), {"brand": "b", "is_advertisement": staticmethod(lambda i: True)})
    with pytest.raises(ProtocolContractError, match="is_advertisement not provided"):
        type("P", (BleParser,), {"brand": "b", "fallback_name": "n"})


def test_contract_rejects_empty_identity_strings():
    message = _define(id="", label="")
    assert "class attribute 'id' is empty" in message
    assert "class attribute 'label' is empty" in message


def test_registry_rejects_duplicate_ids(monkeypatch):
    monkeypatch.setattr(esl_ble, "_BACKENDS", dict(esl_ble._BACKENDS))
    esl_ble.register(_Backend())
    with pytest.raises(ProtocolContractError, match="already registered"):
        esl_ble.register(type("Dup", (_Backend,), {})())


def test_write_prepared_wraps_session_errors_and_disconnects(monkeypatch):
    """Errors raised inside write_session become a failed WriteResult; the
    link is closed either way; the caller-owned encode future is untouched."""

    class Backend(_Backend):
        id = "t2"

        async def write_session(self, client, address, preset, prepared, **kwargs):
            assert address == "AA:BB:CC:DD:EE:FF"
            await prepared
            raise TimeoutError()  # empty str(): falls back to the type name

    async def _test():
        client = MagicMock(is_connected=True, disconnect=AsyncMock())
        monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=client))
        prepared = asyncio.get_running_loop().create_future()
        prepared.set_result(b"x")
        device = MagicMock(address="AA:BB:CC:DD:EE:FF")

        result = await Backend().write_prepared(device, PRESET, prepared)

        assert result == WriteResult(success=False, error="TimeoutError")
        client.disconnect.assert_awaited_once()
        assert prepared.done() and not prepared.cancelled()

    asyncio.run(_test())
