"""Poshiji discovery, model catalog, config persistence and session integration tests."""

import asyncio
import dataclasses
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from bt import binary_values, sensor_values, service_info, update_device
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


def test_discovery_profile_and_advertised_readings():
    backend = esl_ble.get("poshiji")
    assert backend.brand == "Poshiji"
    assert PSJ_420.confidence == CONFIDENCE_REPORTED
    assert PSJ_420.verified
    assert backend.capabilities.passive_battery and not backend.capabilities.session_battery
    for tail in (0x1E, 0x1B):
        info = advertisement(tail)
        assert [b.id for b in esl_ble.all_backends() if b.supported(info)] == ["poshiji"]
        assert esl_ble.detect(info) is backend
        adv = backend.parse_advertisement(info)
        assert adv.model_key == "psj-420" and adv.battery_mv is None
        assert adv.sw_version == "4.0.2" and adv.hw_version == "2"
        assert adv.raw["device_number"] == 153 and adv.raw["battery_percent"] == 100
        parser = backend.create_parser(PSJ_420)
        update = parser.update(info)
        device = update_device(update)
        assert device.manufacturer == "Poshiji"
        assert "PSJ-420" in device.model
        assert device.sw_version == "4.0.2" and device.hw_version == "2"
        assert sensor_values(update)["battery"] == 100
        assert binary_values(update)["battery"] is False
        assert set(sensor_values(update)) == {"signal_strength", "battery"}  # no temperature
    unknown = advertisement(payload=b"\x00" * 13)
    assert backend.parse_advertisement(unknown) is None
    assert not backend.supported(unknown)


def test_identity_survives_battery_and_firmware_changes():
    """The model is the device number; battery and firmware bytes may change."""
    backend = esl_ble.get("poshiji")
    drained = advertisement(payload=bytes.fromhex("fd024103009905060102ffff1b"))
    assert backend.supported(drained)
    adv = backend.parse_advertisement(drained)
    assert adv.model_key == "psj-420" and adv.sw_version == "4.1.3"
    update = backend.create_parser(PSJ_420).update(drained)
    assert sensor_values(update)["battery"] == 5
    assert binary_values(update)["battery"] is True


def test_unknown_device_number_is_not_claimed_but_reported_once(caplog):
    """An XTE tag of another type (PSJ-213, device number 140) is left alone."""
    backend = esl_ble.get("poshiji")
    psj_213 = advertisement(payload=bytes.fromhex("fd024002008c63060102ffff1c"))
    with caplog.at_level(logging.INFO, logger="custom_components.ble_esl.esl_ble.poshiji"):
        assert not backend.supported(psj_213)
        assert backend.parse_advertisement(psj_213) is None
        assert esl_ble.detect(psj_213) is None
        assert not backend.supported(psj_213)
    reports = [r for r in caplog.records if "Unsupported Poshiji/XTE tag" in r.message]
    assert len(reports) == 1
    assert "device number 140" in reports[0].message and "4.0.2" in reports[0].message
    assert "fd024002008c63060102ffff1c" in reports[0].message


def test_catalog_entries_are_complete_and_disjoint():
    """A model is one PRESETS entry; check what discovery and packing derive from it."""
    device_numbers = {}
    for key, preset in devices.PRESETS.items():
        number = preset.extra.get("device_number")
        assert isinstance(number, int) and 0 < number <= 0xFFFF, f"{key} has no device number"
        assert number not in device_numbers, (
            f"{key} shares a device number with {device_numbers[number]}"
        )
        assert preset.colors in PALETTES, f"{key} palette {preset.colors} has no pixel mapping"
        record = b"\xfd\x02\x40\x02" + number.to_bytes(2, "big") + b"\x64\x06"
        assert preset_for_advertisement(record) is preset
        device_numbers[number] = key


def test_new_model_is_one_catalog_entry(monkeypatch):
    """Adding a preset with its own fingerprint wires up detection, naming and packing."""
    other = dataclasses.replace(
        PSJ_420,
        key="psj-290",
        display_name='PSJ-290 2.9" BWRY',
        width=296,
        height=128,
        extra={"device_number": 140},
    )
    monkeypatch.setitem(devices.PRESETS, other.key, other)
    backend = esl_ble.get("poshiji")
    info = advertisement(payload=bytes.fromhex("fd024002008c63060102ffff1c"))
    assert esl_ble.detect(info) is backend
    assert backend.parse_advertisement(info).model_key == "psj-290"
    assert backend.parse_advertisement(advertisement()).model_key == "psj-420"
    assert backend.preset_for("psj-290") is other
    # A stale configured model is corrected by what the tag advertises.
    assert backend.refine_preset(PSJ_420, backend.parse_advertisement(info)) is other
    assert backend.refine_preset(other, backend.parse_advertisement(advertisement())) is PSJ_420
    assert backend.refine_preset(PSJ_420, None) is PSJ_420
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
