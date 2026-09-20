"""Poshiji discovery, model catalog, config persistence and session integration tests."""

import asyncio
import dataclasses
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from bt import sensor_values, service_info, update_device
from PIL import Image
import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble import base
from custom_components.ble_esl.esl_ble.base import CONFIDENCE_REPORTED
from custom_components.ble_esl.esl_ble.poshiji import devices, writer
from custom_components.ble_esl.esl_ble.poshiji.const import PALETTES
from custom_components.ble_esl.esl_ble.poshiji.devices import PSJ_420, preset_for_advertisement


def advertisement(tail=0x1B, payload=None):
    return service_info(
        "AA:BB:CC:DD:EE:FF",
        name="FFEEDDCCBBAA",
        manufacturer_data={
            0x5258: payload
            if payload is not None
            else bytes.fromhex("fd024002009964060102ffff") + bytes([tail])
        },
    )


def test_discovery_profile_and_no_invented_sensors():
    backend = esl_ble.get("poshiji")
    assert backend.brand == "Poshiji"
    assert PSJ_420.confidence == CONFIDENCE_REPORTED
    assert PSJ_420.verified
    for tail in (0x1E, 0x1B):
        info = advertisement(tail)
        assert [b.id for b in esl_ble.all_backends() if b.supported(info)] == ["poshiji"]
        assert esl_ble.detect(info) is backend
        adv = backend.parse_advertisement(info)
        assert adv.model_key == "psj-420" and adv.battery_mv is None
        parser = backend.create_parser(PSJ_420)
        update = parser.update(info)
        device = update_device(update)
        assert device.manufacturer == "Poshiji"
        assert "PSJ-420" in device.model
        assert {k for k in sensor_values(update)} <= {"signal_strength"}  # nothing invented
        assert not backend.capabilities.session_battery
        assert not backend.capabilities.passive_battery
    unknown = advertisement(payload=b"\x00" * 13)
    assert backend.parse_advertisement(unknown) is None
    assert not backend.supported(unknown)


def test_catalog_entries_are_complete_and_disjoint():
    """A model is one PRESETS entry; check what discovery and packing derive from it."""
    fingerprints = {}
    for key, preset in devices.PRESETS.items():
        fingerprint = preset.extra.get("advertisement")
        assert isinstance(fingerprint, bytes) and fingerprint, f"{key} has no fingerprint"
        assert preset.colors in PALETTES, f"{key} palette {preset.colors} has no pixel mapping"
        assert preset_for_advertisement(fingerprint + b"\x00") is preset
        for other_key, other in fingerprints.items():
            assert not fingerprint.startswith(other) and not other.startswith(fingerprint), (
                f"{key} and {other_key} fingerprints overlap"
            )
        fingerprints[key] = fingerprint


def test_new_model_is_one_catalog_entry(monkeypatch):
    """Adding a preset with its own fingerprint wires up detection, naming and packing."""
    other = dataclasses.replace(
        PSJ_420,
        key="psj-290",
        display_name='PSJ-290 2.9" BWRY',
        width=296,
        height=128,
        extra={"advertisement": bytes.fromhex("fd022901009964060102ffff")},
    )
    monkeypatch.setitem(devices.PRESETS, other.key, other)
    backend = esl_ble.get("poshiji")
    info = advertisement(payload=other.extra["advertisement"] + b"\x1e")
    assert esl_ble.detect(info) is backend
    assert backend.parse_advertisement(info).model_key == "psj-290"
    assert backend.parse_advertisement(advertisement()).model_key == "psj-420"
    assert backend.preset_for("psj-290") is other
    assert "PSJ-290" in update_device(backend.create_parser(other).update(info)).model
    obj = writer.prepare(other, Image.new("RGB", (296, 128), "white"), "")
    assert obj[25:33] == (296).to_bytes(4, "big") + (128).to_bytes(4, "big")
    assert int.from_bytes(obj[8:12], "big") == len(obj)


def test_foreign_preset_is_refused_before_connecting(monkeypatch):
    connect = AsyncMock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr(base, "establish_connection", connect)
    foreign = dataclasses.replace(PSJ_420, width=296, height=128)
    result = asyncio.run(esl_ble.get("poshiji").write_image(advertisement(), foreign, object()))
    assert not result.success and result.error == "Unsupported Poshiji preset"
    connect.assert_not_awaited()


@pytest.mark.parametrize("error", [None, ValueError("bad response"), TimeoutError()])
def test_session_result_and_disconnect(monkeypatch, error):
    client = SimpleNamespace(is_connected=True, disconnect=AsyncMock())
    monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=client))
    transport = SimpleNamespace(write_object=AsyncMock(return_value=True, side_effect=error))
    factory = MagicMock(return_value=transport)
    monkeypatch.setattr(writer, "XteClient", factory)
    image, encoded = object(), b"XTEK-encoded"
    prepare = MagicMock(return_value=encoded)
    monkeypatch.setattr(esl_ble.get("poshiji"), "prepare_image", prepare)
    result = asyncio.run(
        esl_ble.get("poshiji").write_image(
            advertisement(),
            PSJ_420,
            image,
            attempt=2,
            write_delay_ms=30,
        )
    )
    # Encoded before connecting, in a worker thread, then handed to the session.
    prepare.assert_called_once_with(PSJ_420, image, advertisement().address)
    factory.assert_called_once_with(client, 2, 30)
    transport.write_object.assert_awaited_once_with(encoded)
    client.disconnect.assert_awaited_once()
    assert result.success is (error is None)
    assert result.battery_mv is None
    if error is not None:
        assert result.error == (str(error) or type(error).__name__)


def test_connection_failure_is_reported(monkeypatch):
    monkeypatch.setattr(base, "establish_connection", AsyncMock(side_effect=OSError("unavailable")))
    monkeypatch.setattr(esl_ble.get("poshiji"), "prepare_image", MagicMock(return_value=b""))
    result = asyncio.run(esl_ble.get("poshiji").write_image(advertisement(), PSJ_420, object()))
    assert not result.success and result.error == "unavailable"
