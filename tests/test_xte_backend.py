"""XTE discovery, model catalog, config persistence and session integration tests."""

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
from custom_components.ble_esl.esl_ble.base import CONFIDENCE_COMMUNITY, CONFIDENCE_REPORTED
from custom_components.ble_esl.esl_ble.xte import devices, writer
from custom_components.ble_esl.esl_ble.xte.const import PALETTES
from custom_components.ble_esl.esl_ble.xte.devices import (
    PSJ_213,
    PSJ_420,
    preset_for_advertisement,
)
from custom_components.ble_esl.esl_ble.xte.protocol import buffer_size, encode_rle, make_blocks


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
    backend = esl_ble.get("xte")
    assert backend.brand == "Poshiji"
    assert PSJ_420.confidence == CONFIDENCE_REPORTED
    assert PSJ_420.verified
    assert backend.capabilities.passive_battery and not backend.capabilities.session_battery
    for tail in (0x1E, 0x1B):
        info = advertisement(tail)
        assert [b.id for b in esl_ble.all_backends() if b.supported(info)] == ["xte"]
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
    backend = esl_ble.get("xte")
    drained = advertisement(payload=bytes.fromhex("fd024103009905060102ffff1b"))
    assert backend.supported(drained)
    adv = backend.parse_advertisement(drained)
    assert adv.model_key == "psj-420" and adv.sw_version == "4.1.3"
    update = backend.create_parser(PSJ_420).update(drained)
    assert sensor_values(update)["battery"] == 5
    assert binary_values(update)["battery"] is True


def test_psj213_is_detected_and_packed_portrait():
    """PSJ-213: device number 140, viewed 250x122, portrait 122x250 buffer."""
    backend = esl_ble.get("xte")
    assert PSJ_213.confidence == CONFIDENCE_COMMUNITY and not PSJ_213.verified
    info = advertisement(payload=bytes.fromhex("fd024002008c63060102ffff1c"))
    assert esl_ble.detect(info) is backend
    adv = backend.parse_advertisement(info)
    assert adv.model_key == "psj-213" and adv.raw["battery_percent"] == 99
    assert backend.refine_preset(PSJ_420, adv) is PSJ_213
    update = backend.create_parser(PSJ_213).update(info)
    assert "PSJ-213" in update_device(update).model and sensor_values(update)["battery"] == 99
    obj = writer.prepare(PSJ_213, Image.new("RGB", (250, 122), "white"), "")
    assert obj[25:33] == (122).to_bytes(4, "big") + (250).to_bytes(4, "big")
    rows = (b"\x55" * 30 + b"\x50") * 250  # 31-byte rows: 30 white bytes, then 2 px + 2 pad
    assert obj[33] == 1 and obj[38:] == encode_rle(rows[:3875]) + encode_rle(rows[3875:])
    assert len(make_blocks(obj)) == 1


def test_unknown_device_number_is_claimed_without_a_model_and_reported_once(caplog):
    """An XTE tag of an uncaptured type is ours, needs a manual model, and is logged once."""
    backend = esl_ble.get("xte")
    unknown = advertisement(payload=bytes.fromhex("fd024002008d63060102ffff1c"))
    with caplog.at_level(logging.INFO, logger="custom_components.ble_esl.esl_ble.xte"):
        assert backend.supported(unknown)
        assert esl_ble.detect(unknown) is backend
        assert backend.supported(unknown)
    adv = backend.parse_advertisement(unknown)
    assert adv.model_key is None
    assert adv.raw["device_number"] == 141 and adv.raw["battery_percent"] == 99
    # The configured (hand-picked) model stays, stamped with the seen device number.
    size_only = devices.PRESETS["psj-290"]
    refined = backend.refine_preset(size_only, adv)
    assert refined.key == "psj-290" and refined.extra["seen_device_number"] == 141
    assert refined.extra["rotation"] == 90
    assert backend.refine_preset(refined, adv) is refined  # no churn on repeated refines
    update = backend.create_parser(size_only).update(unknown)
    assert '2.9" BWRY' in update_device(update).model and sensor_values(update)["battery"] == 99
    reports = [r for r in caplog.records if "unknown device number" in r.message]
    assert len(reports) == 1
    assert "device number 141" in reports[0].message and "4.0.2" in reports[0].message
    assert "fd024002008d63060102ffff1c" in reports[0].message


def test_size_only_presets_pack_at_their_resolution():
    """Size-only entries have no device number but are complete for a manual pick."""
    expected_buffers = {
        "psj-154": (200, 200),  # square: no rotation
        "psj-266": (152, 296),
        "psj-290": (128, 296),
        "psj-350": (384, 184),  # larger: landscape like the PSJ-420
        "psj-370": (416, 240),
        "psj-750": (800, 480),
    }
    for key, (buf_w, buf_h) in expected_buffers.items():
        preset = devices.PRESETS[key]
        assert "device_number" not in preset.extra and not preset.verified
        assert (preset.extra.get("rotation", 0) == 90) == (key in ("psj-266", "psj-290"))
        assert buffer_size(preset) == (buf_w, buf_h)
        obj = writer.prepare(preset, Image.new("RGB", (preset.width, preset.height)), "")
        assert obj[25:33] == buf_w.to_bytes(4, "big") + buf_h.to_bytes(4, "big")


def test_catalog_entries_are_complete_and_disjoint():
    """A model is one PRESETS entry; check what discovery and packing derive from it."""
    device_numbers = {}
    for key, preset in devices.PRESETS.items():
        assert preset.colors in PALETTES, f"{key} palette {preset.colors} has no pixel mapping"
        number = preset.extra.get("device_number")
        if number is None:
            continue  # size-only entry, picked by hand until its device number is known
        assert isinstance(number, int) and 0 < number <= 0xFFFF, f"{key} device number"
        assert number not in device_numbers, (
            f"{key} shares a device number with {device_numbers[number]}"
        )
        record = b"\xfd\x02\x40\x02" + number.to_bytes(2, "big") + b"\x64\x06"
        assert preset_for_advertisement(record) is preset
        device_numbers[number] = key
    assert {"psj-420", "psj-213"} <= set(device_numbers.values())


def test_new_model_is_one_catalog_entry(monkeypatch):
    """Adding a preset with its own fingerprint wires up detection, naming and packing."""
    other = dataclasses.replace(
        PSJ_420,
        key="psj-290",
        display_name='PSJ-290 2.9" BWRY',
        width=296,
        height=128,
        extra={"device_number": 141},
    )
    monkeypatch.setitem(devices.PRESETS, other.key, other)
    backend = esl_ble.get("xte")
    info = advertisement(payload=bytes.fromhex("fd024002008d63060102ffff1c"))
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
    result = asyncio.run(esl_ble.get("xte").write_image(advertisement(), foreign, object()))
    assert not result.success and result.error == "Unsupported XTE preset"
    connect.assert_not_awaited()


@pytest.mark.parametrize("number", [97, 102, 106, 109, 119, 122])
def test_unimplemented_pixel_layout_is_refused_before_connecting(monkeypatch, number):
    """A hand-picked size on a tag type with another pixel layout never gets a bad image."""
    connect = AsyncMock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr(base, "establish_connection", connect)
    backend = esl_ble.get("xte")
    payload = (
        bytes.fromhex("fd024002") + number.to_bytes(2, "big") + bytes.fromhex("63060102ffff1c")
    )
    adv = backend.parse_advertisement(advertisement(payload=payload))
    preset = backend.refine_preset(devices.PRESETS["psj-290"], adv)
    result = asyncio.run(backend.write_image(advertisement(), preset, object()))
    assert not result.success and f"device number {number}" in result.error
    connect.assert_not_awaited()
    # Any other seen device number writes normally (the stamp is not a rejection).
    other = backend.refine_preset(
        devices.PRESETS["psj-290"],
        backend.parse_advertisement(
            advertisement(payload=bytes.fromhex("fd024002008d63060102ffff1c"))
        ),
    )
    monkeypatch.setattr(base, "establish_connection", AsyncMock(side_effect=OSError("down")))
    result = asyncio.run(backend.write_image(advertisement(), other, object()))
    assert result.error == "down"


@pytest.mark.parametrize("error", [None, ValueError("bad response"), TimeoutError()])
def test_session_result_and_disconnect(monkeypatch, error):
    client = SimpleNamespace(is_connected=True, disconnect=AsyncMock())
    monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=client))
    transport = SimpleNamespace(write_object=AsyncMock(return_value=True, side_effect=error))
    factory = MagicMock(return_value=transport)
    monkeypatch.setattr(writer, "XteClient", factory)
    image, encoded = object(), b"XTEK-encoded"
    prepare = MagicMock(return_value=encoded)
    monkeypatch.setattr(esl_ble.get("xte"), "prepare_image", prepare)
    result = asyncio.run(
        esl_ble.get("xte").write_image(
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
    monkeypatch.setattr(esl_ble.get("xte"), "prepare_image", MagicMock(return_value=b""))
    result = asyncio.run(esl_ble.get("xte").write_image(advertisement(), PSJ_420, object()))
    assert not result.success and result.error == "unavailable"
