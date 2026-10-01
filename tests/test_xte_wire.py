"""Codec checks for XTE wire formats without a BLE adapter or Home Assistant."""

from __future__ import annotations

import pytest

from custom_components.ble_esl.esl_ble.xte.devices import (
    PRESETS,
    preset_for_advertisement,
)
from custom_components.ble_esl.esl_ble.xte.wire import (
    blocks,
    command,
    image_object,
    parse_advertisement,
    run_length,
)

PSJ_420 = PRESETS["psj-420"]
PSJ_213 = PRESETS["psj-213"]


@pytest.mark.parametrize("tail", [0x1E, 0x1B, 0x00, 0xFF])
def test_advertisement_variable_tail(tail):
    data = bytes.fromhex("fd024002009964060102ffff") + bytes([tail])
    assert preset_for_advertisement(data) is PSJ_420


def test_advertisement_fields_psj420_and_psj213():
    """Field layout of the XTE manufacturer-data record."""
    ours = parse_advertisement(bytes.fromhex("fd024002009964060102ffff1e"))
    assert (ours.record_type, ours.hardware_revision, ours.firmware) == (0xFD, 2, "4.0.2")
    assert (ours.device_number, ours.battery_percent) == (153, 100)
    assert (ours.chip_type, ours.tx_power) == (0, 6)
    theirs = parse_advertisement(bytes.fromhex("fd024002008c63060102ffff1c"))
    assert (theirs.device_number, theirs.battery_percent, theirs.firmware) == (140, 99, "4.0.2")
    # Battery and firmware are readings, not identity.
    assert preset_for_advertisement(bytes.fromhex("fd024103009905060102ffff1b")) is PSJ_420
    assert preset_for_advertisement(bytes.fromhex("fd024002008c63060102ffff1c")) is PSJ_213
    assert preset_for_advertisement(bytes.fromhex("fd024002008d63060102ffff1c")) is None
    assert (
        parse_advertisement(bytes.fromhex("fd02400200 99 ff 06".replace(" ", ""))).battery_percent
        == 100
    )


@pytest.mark.parametrize(
    ("hex_data", "key", "number", "firmware", "battery"),
    [
        ("fd024002009a64060102ffff1a", "psj-290", 154, "4.0.2", 100),
        ("fd024001009c64060102ffff1a", "psj-266", 156, "4.0.1", 100),
        ("fd024002008c5f060102ffff1c", "psj-213", 140, "4.0.2", 95),
        ("0402400300996406ff01ffff1c", "psj-420", 153, "4.0.3", 100),
    ],
)
def test_captured_advertisements(hex_data, key, number, firmware, battery):
    """Advertisements captured from real tags of each size."""
    data = bytes.fromhex(hex_data)
    adv = parse_advertisement(data)
    assert (adv.device_number, adv.firmware, adv.battery_percent) == (number, firmware, battery)
    assert preset_for_advertisement(data) is PRESETS[key]


@pytest.mark.parametrize("record_type", [0xFD, 0xFE, 0xFC, 0x04])
def test_advertisement_record_types(record_type):
    data = bytes([record_type]) + bytes.fromhex("024002009964060102ffff1e")
    assert parse_advertisement(data).record_type == record_type
    assert preset_for_advertisement(data) is PSJ_420


@pytest.mark.parametrize(
    "data",
    [
        None,
        b"",
        bytes.fromhex("ff01"),  # the alternating 2-byte payload under the same company id
        bytes.fromhex("fd0240020099"),  # too short to carry battery and chip bytes
        bytes.fromhex("00024002009964060102ffff1e"),  # unknown record type
        b"\x00" * 13,
    ],
)
def test_advertisement_rejects_other_payloads(data):
    assert parse_advertisement(data) is None
    assert preset_for_advertisement(data) is None


def test_rle_boundaries():
    assert run_length(b"") == b""
    assert run_length(b"\x55" * 256 + b"\xaa" * 2) == bytes.fromhex("ff55015502aa")
    raw = bytes(range(256)) * 120
    encoded = run_length(raw)
    assert b"".join(bytes([v]) * n for n, v in zip(encoded[::2], encoded[1::2], strict=True)) == raw


def test_image_header_and_half_frame_run_boundary():
    obj = image_object(b"\xaa" * 30000, 400, 300)
    # Each independently encoded 15000-byte half is 58*255 + 210 bytes.
    encoded_half = bytes.fromhex("ffaa") * 58 + bytes.fromhex("d2aa")
    assert obj[38:] == encoded_half * 2
    assert obj[:4] == b"XTEK"
    assert int.from_bytes(obj[4:8], "big") == sum(obj[12:])
    assert int.from_bytes(obj[8:12], "big") == len(obj)
    assert obj[12:25] == bytes.fromhex("01000000110000000000000000")
    assert obj[25:34] == bytes.fromhex("000001900000012c01")
    assert int.from_bytes(obj[34:38], "big") == 236
    with pytest.raises(ValueError, match="30000 bytes"):
        image_object(b"\x00", 400, 300)
    with pytest.raises(ValueError, match="7750 bytes"):  # 122 px rows pad to 31 bytes
        image_object(b"\x00" * 7625, 122, 250)


def test_control_commands_from_capture():
    assert command(b"\x01" + (10244).to_bytes(4, "big")) == bytes.fromhex("585445010b2d0100002804")
    assert command(b"\x04\x00") == bytes.fromhex("5854450108040400")


def test_blocks_and_worst_case_size():
    obj = bytes(range(256)) * 40 + b"test"
    framed = blocks(obj)
    assert len(framed) == 9
    assert [len(b) for b in framed] == [1220] * 8 + [565]
    assert b"".join(b[9:] for b in framed) == obj
    for i, block in enumerate(framed):
        assert block[:4] == b"XTE\x02"
        assert int.from_bytes(block[4:6], "big") == len(block)
        assert block[6] == sum(block[7:]) & 255
        assert block[7:9] == bytes((9, i))
    raw = (bytes(range(256)) * 118)[:30000]
    assert len(image_object(raw, 400, 300)) == 60038
    assert len(blocks(image_object(raw, 400, 300))) == 50
