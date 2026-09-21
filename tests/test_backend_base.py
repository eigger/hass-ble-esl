"""Tests for the shared BleParser / BleBackend behaviour in esl_ble/base.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from bt import service_info, update_device
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
    WriteTiming,
    battery_percent,
)

PRESET = DevicePreset(key="p", display_name='Panel 2.9"', width=296, height=128)
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
    return service_info(address, name=name)


def test_parser_naming_with_and_without_preset():
    parser = _Parser()
    update = parser.update(_info())
    assert update.title == "54200055 (Generic)"
    device = update_device(update)
    assert device.name == "Acme 54200055"
    assert device.model == "Generic"
    assert device.manufacturer == "Acme"

    parser.set_preset(PRESET)  # re-derives naming from the last advertisement
    update = parser.update(_info())
    assert update.title == '54200055 (Panel 2.9")'
    assert update_device(update).model == 'Panel 2.9" 296x128'

    parser.set_preset(PRESET_WITH_RES)  # resolution already in the name: not repeated
    assert update_device(parser.update(_info())).model == "Panel 296x128"


def test_parser_ignores_foreign_advertisements():
    parser = _Parser(PRESET)
    update = parser.update(_info(name="no"))
    assert parser.last_service_info is None
    assert update.title is None and update.devices == {}


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
        id="x",
        label="X",
        name="X",
        capabilities=_Backend.capabilities,
        PRESETS=_Backend.PRESETS,
        parser_cls=_Parser,
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

        assert (result.success, result.error) == (False, "TimeoutError")
        assert set(result.timing) == {"connect_s", "session_s"}  # failures are timed too
        client.disconnect.assert_awaited_once()
        assert prepared.done() and not prepared.cancelled()

    asyncio.run(_test())


# ── Notifications ────────────────────────────────────────────────────────


def _notifying_client(*, connected=True, stop_fails=False):
    client = MagicMock(is_connected=connected)
    client.handler = None

    async def start_notify(char, handler):
        client.handler = handler

    client.start_notify = AsyncMock(side_effect=start_notify)
    client.stop_notify = AsyncMock(side_effect=OSError("gone") if stop_fails else None)
    return client


def test_notifications_next_and_clear():
    from custom_components.ble_esl.esl_ble.base import Notifications

    async def _test():
        client = _notifying_client()
        async with Notifications(client, "char") as replies:
            client.handler(None, bytearray(b"a"))
            client.handler(None, bytearray(b"b"))
            assert replies.clear() == [b"a", b"b"]
            client.handler(None, bytearray(b"c"))
            assert await replies.next(0.1, step="cmd") == b"c"
        client.stop_notify.assert_awaited_once_with("char")

    asyncio.run(_test())


def test_notifications_timeout_names_the_step():
    from custom_components.ble_esl.esl_ble.base import Notifications, NotificationTimeout

    async def _test():
        async with Notifications(_notifying_client(), "char") as replies:
            with pytest.raises(
                NotificationTimeout, match=r"No response from tag within 0\.05s after START"
            ):
                await replies.next(0.05, step="START")
            with pytest.raises(NotificationTimeout, match="after DONE"):
                await replies.wait_for(lambda d: False, 0.05, step="DONE")

    asyncio.run(_test())


def test_notifications_wait_for_skips_and_can_raise():
    from custom_components.ble_esl.esl_ble.base import Notifications

    def accept(data):
        if data == b"err":
            raise ValueError("device error")
        return data == b"ok"

    async def _test():
        client = _notifying_client()
        async with Notifications(client, "char") as replies:
            client.handler(None, bytearray(b"busy"))
            client.handler(None, bytearray(b"ok"))
            assert await replies.wait_for(accept, 0.1, step="x") == b"ok"
            client.handler(None, bytearray(b"err"))
            with pytest.raises(ValueError, match="device error"):
                await replies.wait_for(accept, 0.1, step="x")

    asyncio.run(_test())


@pytest.mark.parametrize("connected,stop_fails", [(True, True), (False, False)])
def test_notifications_unsubscribe_never_masks_the_session_error(connected, stop_fails):
    from custom_components.ble_esl.esl_ble.base import Notifications

    async def _test():
        client = _notifying_client(connected=connected, stop_fails=stop_fails)
        with pytest.raises(RuntimeError, match="transfer failed"):
            async with Notifications(client, "char"):
                raise RuntimeError("transfer failed")
        assert client.stop_notify.await_count == (1 if connected else 0)

    asyncio.run(_test())


def test_notifications_settle_after_subscribe(monkeypatch):
    from custom_components.ble_esl.esl_ble import base

    async def _test():
        order = []
        client = _notifying_client()
        client.start_notify = AsyncMock(side_effect=lambda *a: order.append("subscribe"))
        monkeypatch.setattr(
            base.asyncio, "sleep", AsyncMock(side_effect=lambda s: order.append(f"sleep {s}"))
        )
        async with base.Notifications(client, "char", settle=0.5):
            order.append("body")
        assert order == ["subscribe", "sleep 0.5", "body"]

    asyncio.run(_test())


def test_preset_for_falls_back_to_first_preset():
    backend = _Backend()
    assert backend.preset_for("p") is PRESET
    assert backend.preset_for("290") is PRESET  # foreign/stale key
    assert backend.preset_for(None) is PRESET


def test_write_prepared_records_connect_and_session_timing(monkeypatch):
    class Backend(_Backend):
        id = "t3"

        async def write_session(self, client, address, preset, prepared, **kwargs):
            await prepared
            return WriteResult(success=True, timing={"transfer_s": 0.5})

    async def _test():
        client = MagicMock(is_connected=True, disconnect=AsyncMock())
        monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=client))
        prepared = asyncio.get_running_loop().create_future()
        prepared.set_result(b"x")
        result = await Backend().write_prepared(
            MagicMock(address="AA:BB:CC:DD:EE:FF"), PRESET, prepared
        )
        assert result.success
        assert list(result.timing) == ["connect_s", "transfer_s", "session_s"]
        assert all(v >= 0 for v in result.timing.values())

    asyncio.run(_test())


def test_write_timing_stages_record_success_and_failure():
    """A stage records its elapsed time whether it returns or raises, and
    reported() hangs the whole dict on the exception for write_prepared()."""
    timing = WriteTiming(settle_s=0.5)
    with timing.stage("start_s"):
        pass
    with pytest.raises(ValueError) as caught, timing.reported(), timing.stage("transfer_s"):
        raise ValueError("boom")
    assert caught.value.timing is timing
    assert list(timing) == ["settle_s", "start_s", "transfer_s"]
    assert timing["start_s"] >= 0 and timing["transfer_s"] >= 0


def test_write_prepared_passes_on_the_connected_scanner(monkeypatch):
    """The scanner the client wrapper connected through is handed to the
    integration on success and failure; a client without one yields None."""

    class Backend(_Backend):
        id = "t4"

        async def write_session(self, client, address, preset, prepared, **kwargs):
            await prepared
            if client.fail:
                raise OSError("gone")
            return WriteResult(success=True)

    async def _test(fail):
        scanner = object()
        client = MagicMock(is_connected=True, disconnect=AsyncMock(), fail=fail)
        client._connected_scanner = scanner
        monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=client))
        prepared = asyncio.get_running_loop().create_future()
        prepared.set_result(b"x")
        result = await Backend().write_prepared(
            MagicMock(address="AA:BB:CC:DD:EE:FF"), PRESET, prepared
        )
        assert result.success is (not fail)
        assert result.scanner is scanner

    asyncio.run(_test(False))
    asyncio.run(_test(True))

    async def _no_handle():
        client = MagicMock(
            is_connected=True, disconnect=AsyncMock(), spec=["is_connected", "disconnect"]
        )
        monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=client))
        prepared = asyncio.get_running_loop().create_future()
        prepared.set_result(b"x")
        backend = Backend()

        async def ok(client, address, preset, prepared, **kwargs):
            return WriteResult(success=True)

        backend.write_session = ok
        result = await backend.write_prepared(
            MagicMock(address="AA:BB:CC:DD:EE:FF"), PRESET, prepared
        )
        assert result.scanner is None

    asyncio.run(_no_handle())
