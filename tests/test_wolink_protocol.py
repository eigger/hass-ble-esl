"""Tests for WOLINK protocol codec, framing, CRC, compression, and plane encoding."""

from __future__ import annotations

import struct
import zlib

from PIL import Image
import pytest

from custom_components.ble_esl.esl_ble.base import DevicePreset
from custom_components.ble_esl.esl_ble.wolink.const import (
    OP_LOAD_IMAGE,
    OP_MULTISCREEN_REFRESH,
    OP_MULTISCREEN_STORE,
    OP_OTA_APPLY,
    OP_OTA_ERASE,
    OP_OTA_SEND,
    OP_REFRESH_COMPRESSED,
    OP_REFRESH_RAW,
    OP_RGB,
    OP_UNBIND_CLEAR,
)
from custom_components.ble_esl.esl_ble.wolink.devices import PRESETS
from custom_components.ble_esl.esl_ble.wolink.protocol import (
    _battery_mv,
    battery_looks_plausible,
    cmd_load_image_chunk,
    cmd_multiscreen_refresh,
    cmd_multiscreen_store_chunk,
    cmd_multiscreen_store_end,
    cmd_ota_apply,
    cmd_ota_erase,
    cmd_ota_send_chunk,
    cmd_refresh_compressed,
    cmd_refresh_raw,
    cmd_rgb,
    cmd_unbind_clear,
    compress_wolink_blocks,
    crc16_modbus,
    encode_planes,
    multiscreen_picture_tag,
    parse_manufacturer_data,
    quantize_image,
)


def test_crc16_modbus():
    """Verify CRC-16/MODBUS calculation."""
    assert crc16_modbus(b"123456789") == 0x4B37
    assert crc16_modbus(b"") == 0xFFFF


def test_compress_wolink_blocks_and_decompress():
    """Verify raw deflate block compression format."""
    data = b"WOLINK_TEST_PAYLOAD_" * 500  # 10000 bytes -> 2 blocks (8192 + 1808)
    compressed = compress_wolink_blocks(data)

    assert compressed[0] == 0xA5
    assert compressed[1] == 0xA6
    block_count = compressed[2]
    assert block_count == 2
    assert compressed[3] == 0x02

    # Extract and decompress each block
    offset = 4
    recovered = bytearray()
    for b in range(block_count):
        idx = compressed[offset]
        assert idx == b + 1
        size = struct.unpack_from("<H", compressed, offset + 1)[0]
        raw_deflate = compressed[offset + 3 : offset + 3 + size]
        decompressed = zlib.decompress(raw_deflate, -15)
        recovered.extend(decompressed)
        offset += 3 + size

    assert bytes(recovered) == data


def test_command_builders():
    """Verify wire format and opcodes of command builder functions."""
    # Load image chunk: 0x00 0xA5 + pointer(4B LE) + data
    cmd_chunk = cmd_load_image_chunk(0x100, b"\x01\x02\x03")
    assert cmd_chunk[:2] == bytes([OP_LOAD_IMAGE & 0xFF, OP_LOAD_IMAGE >> 8])
    assert struct.unpack_from("<I", cmd_chunk, 2)[0] == 0x100
    assert cmd_chunk[6:] == b"\x01\x02\x03"

    # Refresh raw: 0x01 0xA5 + size(4B LE)
    cmd_raw = cmd_refresh_raw(5000)
    assert cmd_raw[:2] == bytes([OP_REFRESH_RAW & 0xFF, OP_REFRESH_RAW >> 8])
    assert struct.unpack_from("<I", cmd_raw, 2)[0] == 5000

    # Refresh compressed: 0x02 0xA5 + size(4B LE)
    cmd_comp = cmd_refresh_compressed(2500)
    assert cmd_comp[:2] == bytes([OP_REFRESH_COMPRESSED & 0xFF, OP_REFRESH_COMPRESSED >> 8])
    assert struct.unpack_from("<I", cmd_comp, 2)[0] == 2500

    # Unbind clear: 0x04 0xA5
    assert cmd_unbind_clear() == bytes([OP_UNBIND_CLEAR & 0xFF, OP_UNBIND_CLEAR >> 8])

    # Multiscreen store tag & chunks
    assert multiscreen_picture_tag(0) == b"PIC00\0"
    assert multiscreen_picture_tag(10) == b"PIC10\0"
    with pytest.raises(ValueError):
        multiscreen_picture_tag(11)

    cmd_ms_chunk = cmd_multiscreen_store_chunk(20, b"DATA")
    assert cmd_ms_chunk[:2] == bytes([OP_MULTISCREEN_STORE & 0xFF, OP_MULTISCREEN_STORE >> 8])
    assert struct.unpack_from("<I", cmd_ms_chunk, 2)[0] == 20

    cmd_ms_end = cmd_multiscreen_store_end(12345)
    assert cmd_ms_end[:2] == bytes([OP_MULTISCREEN_STORE & 0xFF, OP_MULTISCREEN_STORE >> 8])
    assert struct.unpack_from("<I", cmd_ms_end, 2)[0] == 12345

    # OTA
    assert cmd_ota_erase() == bytes([OP_OTA_ERASE & 0xFF, OP_OTA_ERASE >> 8])
    cmd_ota_c = cmd_ota_send_chunk(0, b"FW")
    assert cmd_ota_c[:2] == bytes([OP_OTA_SEND & 0xFF, OP_OTA_SEND >> 8])
    cmd_ota_a = cmd_ota_apply(1024, 0x1234)
    assert cmd_ota_a[:2] == bytes([OP_OTA_APPLY & 0xFF, OP_OTA_APPLY >> 8])
    assert struct.unpack_from("<IH", cmd_ota_a, 2) == (1024, 0x1234)

    # RGB
    cmd_r = cmd_rgb(255, 128, 0, 100, 200, 1000)
    assert cmd_r[:2] == bytes([OP_RGB & 0xFF, OP_RGB >> 8])
    assert cmd_r[2:5] == bytes([255, 128, 0])

    # Multiscreen refresh
    cmd_ms_ref = cmd_multiscreen_refresh(0, -1)
    assert cmd_ms_ref[:2] == bytes([OP_MULTISCREEN_REFRESH & 0xFF, OP_MULTISCREEN_REFRESH >> 8])
    assert struct.unpack_from("<bb", cmd_ms_ref, 2) == (0, -1)


def test_parse_manufacturer_data():
    """Verify 0xBBAA manufacturer broadcast payload unpacking."""
    raw = bytes(
        [
            0x12,
            0x34,  # PID: "1234"
            0x01,
            0x02,  # AppVer: 0x0102 = 258 (big-endian)
            0x03,
            0x04,  # HwVer: 0x0304 = 772
            0x05,
            0x06,  # DispVer: 0x0506 = 1286
            0x0B,
            0xB8,  # BatVoltage_mv: 0x0BB8 = 3000 mV
        ]
    )
    info = parse_manufacturer_data(raw)
    assert info["pid"] == "1234"
    assert info["app_ver"] == 258
    assert info["hw_ver"] == 772
    assert info["disp_ver"] == 1286
    assert info["battery_mv"] == 3000
    assert battery_looks_plausible(info["battery_mv"]) is True

    # Short payload
    with pytest.raises(ValueError):
        parse_manufacturer_data(b"\x01\x02\x03")


def test_parse_manufacturer_data_captured_advertisement():
    """Versions use the same big-endian layout as the battery millivolts.

    Captured from the 2.9\" tag in discussion 55. Little-endian would report
    app 3584 (0x0E00) and hardware 12291 (0x3003) instead of 14 and 0x0330.
    """
    info = parse_manufacturer_data(bytes.fromhex("3000000e033003030b9d"))
    assert info == {
        "pid": "3000",
        "app_ver": 0x000E,
        "hw_ver": 0x0330,
        "disp_ver": 0x0303,
        "battery_mv": 2973,
    }


def test_battery_plausibility_and_endian():
    """Verify battery voltage decoder and plausibility guard."""
    assert _battery_mv(bytes([0x0B, 0xB8])) == 3000  # 3.0 V
    assert _battery_mv(bytes([0x09, 0xC4])) == 2500  # 2.5 V
    assert battery_looks_plausible(3000) is True
    assert battery_looks_plausible(1400) is False  # Too low
    assert battery_looks_plausible(4500) is False  # Too high (or swapped endian)


def test_quantize_image():
    """Verify quantizing PIL image to bit planes."""
    img = Image.new("RGB", (2, 2), "white")
    pixels = img.load()
    pixels[0, 0] = (0, 0, 0)  # Black
    pixels[1, 0] = (255, 255, 255)  # White
    pixels[0, 1] = (255, 0, 0)  # Red
    pixels[1, 1] = (255, 255, 0)  # Yellow

    plane_bw, plane_red, plane_yellow = quantize_image(img, 2, 2, "BWRY")
    assert plane_bw == [1, 0, 0, 0]
    assert plane_red == [0, 0, 1, 0]
    assert plane_yellow == [0, 0, 0, 1]


def test_encode_planes_2bpp_mapping():
    """Verify 2bpp bit packing: 00=Black, 01=White, 10=Yellow, 11=Red."""
    preset = DevicePreset(
        key="test",
        display_name="Test",
        width=4,
        height=1,
        colors="BWRY",
        extra={"row_major": True, "mirror": False, "rotate_cw": False},
    )
    # 4 pixels: Black (00), White (01), Yellow (10), Red (11)
    plane_bw = [1, 0, 0, 0]
    plane_red = [0, 0, 0, 1]
    plane_yellow = [0, 0, 1, 0]

    packed = encode_planes(plane_bw, plane_red, plane_yellow, preset)
    assert len(packed) == 1
    # Bits: 00 01 10 11 = 0x1B
    assert packed[0] == 0b00011011


def test_encode_planes_length_guard():
    """Verify length guard raises ValueError when plane length doesn't match preset."""
    preset = PRESETS["290"]  # 296x128 = 37888
    wrong_length_plane = [0] * 100

    with pytest.raises(ValueError, match="plane_bw has 100 entries, expected 37888"):
        encode_planes(wrong_length_plane, [0] * 37888, [0] * 37888, preset)


def test_encode_planes_mirror_and_rotation():
    """Verify orientation flags (mirror, rotate_cw, row_major) produce expected buffer sizes."""
    preset_290 = PRESETS["290"]
    expected_len = (preset_290.width * preset_290.height) // 4
    plane_bw = [0] * (preset_290.width * preset_290.height)
    plane_red = [0] * (preset_290.width * preset_290.height)
    plane_yellow = [0] * (preset_290.width * preset_290.height)

    encoded = encode_planes(plane_bw, plane_red, plane_yellow, preset_290)
    assert len(encoded) == expected_len

    preset_750 = PRESETS["750"]
    expected_len_750 = (preset_750.width * preset_750.height) // 4
    plane_750 = [0] * (preset_750.width * preset_750.height)
    encoded_750 = encode_planes(plane_750, plane_750, plane_750, preset_750)
    assert len(encoded_750) == expected_len_750


def test_encode_split_planes_bw_then_red():
    """BWR split packing: BW bit 1 is white, red follows, MSB first."""
    preset = DevicePreset(
        key="bwr",
        display_name="bwr",
        width=8,
        height=1,
        colors="BWR",
        extra={"split_planes": True, "row_major": True},
    )
    black = [1] * 8  # quantizer: 1 = black
    white = [0] * 8
    off = [0] * 8
    assert encode_planes(black, off, off, preset) == bytes([0x00, 0x00])
    assert encode_planes(white, off, off, preset) == bytes([0xFF, 0x00])
    assert encode_planes(white, [1] * 8, off, preset) == bytes([0xFF, 0xFF])

    # White pixel at x=0 on a black row sets the high bit of the BW plane.
    one_white = [0, 1, 1, 1, 1, 1, 1, 1]
    assert encode_planes(one_white, off, off, preset) == bytes([0x80, 0x00])

    mirrored = DevicePreset(
        key="bwr",
        display_name="bwr",
        width=8,
        height=1,
        colors="BWR",
        extra={"split_planes": True, "row_major": True, "mirror": True},
    )
    assert encode_planes(one_white, off, off, mirrored)[0] == 0x01


def test_encode_split_planes_column_major():
    """With row_major off, x is the slow axis: pixel (0, 1) is the second bit."""
    preset = DevicePreset(
        key="bwr",
        display_name="bwr",
        width=4,
        height=2,
        colors="BWR",
        extra={"split_planes": True, "row_major": False},
    )
    # Index y * width + x. White (quantizer 0) only at (x=0, y=1).
    plane_bw = [1, 1, 1, 1, 0, 1, 1, 1]
    off = [0] * 8
    packed = encode_planes(plane_bw, off, off, preset)
    assert packed[0] == 0x40  # column x=0: y=0 black, y=1 white
    assert packed[1:] == bytes(len(packed) - 1)


def test_encode_290_bwr_is_two_full_frames():
    """2.9\" BWR is two 296x128 1bpp frames, not the 2bpp packing of preset 290."""
    preset = PRESETS["290-bwr"]
    count = preset.width * preset.height
    black = encode_planes([1] * count, [0] * count, [0] * count, preset)
    assert len(black) == count // 4  # same byte count as 2bpp: two 1bpp frames
    assert black == bytes(len(black))
    white = encode_planes([0] * count, [0] * count, [0] * count, preset)
    assert white[: count // 8] == bytes([0xFF]) * (count // 8)
    assert white[count // 8 :] == bytes(count // 8)


def test_encode_planes_213_non_multiple_of_4():
    """Verify 213 (250x122) encodes correctly with (buf_w + 3) // 4 byte alignment."""
    preset_213 = PRESETS["213"]  # 250x122, row_major=False -> buf_w=122 (122%4 == 2)
    plane = [0] * (250 * 122)
    encoded = encode_planes(plane, plane, plane, preset_213)
    # buf_h=250, num_col_groups=(122+3)//4 = 31 -> 250 * 31 = 7750 bytes
    assert len(encoded) == 250 * 31
