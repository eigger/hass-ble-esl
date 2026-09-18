"""WOLINK BLE ESL protocol — pure functions and codecs."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING
import zlib

from PIL import Image

from ..base import DevicePreset
from .const import (
    BLOCK_SIZE,
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

if TYPE_CHECKING:
    pass


def _opcode_bytes(opcode: int) -> bytes:
    return bytes([opcode & 0xFF, (opcode >> 8) & 0xFF])


def compress_wolink_blocks(data: bytes) -> bytes:
    """Block-deflate format used by WOLINK image/OTA commands.

    Format: A5 A6 <block_count> 02 [<idx:1B> <size:u16le> <raw_deflate>] x N
    """
    blocks = [data[i : i + BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]
    out = bytearray([0xA5, 0xA6, len(blocks), 0x02])
    for i, block in enumerate(blocks):
        compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
        compressed = compressor.compress(block) + compressor.flush()
        out.append(i + 1)
        out.extend(len(compressed).to_bytes(2, "little"))
        out.extend(compressed)
    return bytes(out)


def crc16_modbus(data: bytes) -> int:
    """CRC-16/MODBUS (init 0xFFFF, poly 0xA001 reflected, no xorout)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


if crc16_modbus(b"123456789") != 0x4B37:
    raise RuntimeError("crc16_modbus self-test failed")


def parse_manufacturer_data(data: bytes) -> dict:
    """Parse 0xBBAA manufacturer-data value (company ID already stripped).

    Layout: PID(2B) + AppVer(2B) + HwVer(2B) + DispVer(2B) + BatVoltage_mv(2B) = 10 bytes.
    """
    if len(data) < 10:
        raise ValueError(
            f"expected at least 10 bytes of manufacturer data, got {len(data)}"
        )
    return {
        "pid": data[0:2].hex(),
        "app_ver": struct.unpack_from("<H", data, 2)[0],
        "hw_ver": struct.unpack_from("<H", data, 4)[0],
        "disp_ver": struct.unpack_from("<H", data, 6)[0],
        "battery_mv": _battery_mv(data[8:10]),
    }


def _battery_mv(raw: bytes) -> int:
    """Decode a 2-byte battery-voltage field as big-endian millivolts."""
    if len(raw) < 2:
        raise ValueError("battery field needs at least 2 bytes")
    return (raw[0] << 8) | raw[1]


def battery_looks_plausible(millivolts: int) -> bool:
    """True if millivolts is in the plausible range for a coin/AA-class cell."""
    return 1500 <= millivolts <= 4200


def cmd_load_image_chunk(pointer: int, data: bytes) -> bytes:
    return _opcode_bytes(OP_LOAD_IMAGE) + pointer.to_bytes(4, "little") + data


def cmd_refresh_raw(size: int) -> bytes:
    return _opcode_bytes(OP_REFRESH_RAW) + size.to_bytes(4, "little")


def cmd_refresh_compressed(size: int) -> bytes:
    return _opcode_bytes(OP_REFRESH_COMPRESSED) + size.to_bytes(4, "little")


def multiscreen_picture_tag(slot: int) -> bytes:
    if not 0 <= slot <= 10:
        raise ValueError("slot must be 0-10")
    return f"PIC{slot:02d}\0".encode("ascii")


def cmd_multiscreen_store_chunk(pointer: int, data: bytes) -> bytes:
    return _opcode_bytes(OP_MULTISCREEN_STORE) + pointer.to_bytes(4, "little") + data


def cmd_multiscreen_store_end(total_length: int) -> bytes:
    return _opcode_bytes(OP_MULTISCREEN_STORE) + total_length.to_bytes(4, "little")


def cmd_unbind_clear() -> bytes:
    return _opcode_bytes(OP_UNBIND_CLEAR)


def cmd_ota_erase() -> bytes:
    return _opcode_bytes(OP_OTA_ERASE)


def cmd_ota_send_chunk(pointer: int, data: bytes) -> bytes:
    return _opcode_bytes(OP_OTA_SEND) + pointer.to_bytes(4, "little") + data


def cmd_ota_apply(firmware_size: int, crc16: int) -> bytes:
    return (
        _opcode_bytes(OP_OTA_APPLY)
        + firmware_size.to_bytes(4, "little")
        + crc16.to_bytes(2, "little")
    )


def cmd_rgb(
    red: int, green: int, blue: int, on_ms: int, off_ms: int, work_ms: int
) -> bytes:
    return (
        _opcode_bytes(OP_RGB)
        + bytes([red & 0xFF, green & 0xFF, blue & 0xFF])
        + on_ms.to_bytes(2, "little")
        + off_ms.to_bytes(2, "little")
        + work_ms.to_bytes(4, "little")
    )


def cmd_multiscreen_refresh(screen_a: int, screen_b: int) -> bytes:
    return _opcode_bytes(OP_MULTISCREEN_REFRESH) + struct.pack(
        "<bb", screen_a, screen_b
    )


def _color_distance(r1: int, g1: int, b1: int, r2: int, g2: int, b2: int) -> float:
    r_mean = (r1 + r2) / 2
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2
    return (
        (2 + r_mean / 256) * dr * dr
        + 4 * dg * dg
        + (2 + (255 - r_mean) / 256) * db * db
    )


def quantize_image(
    img: Image.Image, width: int, height: int, colors: str = "BWRY"
) -> tuple[list[int], list[int], list[int]]:
    """Quantize a PIL Image into (plane_bw, plane_red, plane_yellow) bit planes."""
    if img.size != (width, height):
        img = img.resize((width, height), Image.Resampling.LANCZOS)
    rgb_img = img.convert("RGB")
    pixels = rgb_img.load()

    plane_bw: list[int] = []
    plane_red: list[int] = []
    plane_yellow: list[int] = []

    has_red = "R" in colors
    has_yellow = "Y" in colors

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            dist_black = _color_distance(r, g, b, 0, 0, 0)
            dist_white = _color_distance(r, g, b, 255, 255, 255)
            candidates = [("black", dist_black), ("white", dist_white)]
            if has_red:
                candidates.append(("red", _color_distance(r, g, b, 255, 0, 0)))
            if has_yellow:
                candidates.append(("yellow", _color_distance(r, g, b, 255, 255, 0)))

            best_color = min(candidates, key=lambda c: c[1])[0]
            if best_color == "black":
                plane_bw.append(1)
                plane_red.append(0)
                plane_yellow.append(0)
            elif best_color == "red":
                plane_bw.append(0)
                plane_red.append(1)
                plane_yellow.append(0)
            elif best_color == "yellow":
                plane_bw.append(0)
                plane_red.append(0)
                plane_yellow.append(1)
            else:  # white
                plane_bw.append(0)
                plane_red.append(0)
                plane_yellow.append(0)

    return plane_bw, plane_red, plane_yellow


def encode_planes(
    plane_bw: list[int] | bytes,
    plane_red: list[int] | bytes,
    plane_yellow: list[int] | bytes | None,
    preset: DevicePreset,
) -> bytes:
    """Convert bit planes to 2bpp packed bytes matching panel scan orientation."""
    width, height = preset.width, preset.height
    expected = width * height
    if plane_yellow is None:
        plane_yellow = [0] * expected

    for name, plane in (
        ("plane_bw", plane_bw),
        ("plane_red", plane_red),
        ("plane_yellow", plane_yellow),
    ):
        if len(plane) != expected:
            raise ValueError(
                f"{name} has {len(plane)} entries, expected {expected} "
                f"({width}x{height} for {preset.display_name or 'this preset'}). "
                "A wrong preset produces a scrambled image rather than an error, "
                "so this is checked up front."
            )

    mirror = bool(preset.extra.get("mirror", False))
    rotate_cw = bool(preset.extra.get("rotate_cw", False))
    row_major = bool(preset.extra.get("row_major", False))

    if mirror:

        def flip_h(plane: list[int] | bytes) -> list[int]:
            flipped = list(plane)
            for y in range(height):
                for x in range(width // 2):
                    a, b = y * width + x, y * width + (width - 1 - x)
                    flipped[a], flipped[b] = flipped[b], flipped[a]
            return flipped

        plane_bw = flip_h(plane_bw)
        plane_red = flip_h(plane_red)
        plane_yellow = flip_h(plane_yellow)

    if row_major:
        buf_h, buf_w = height, width
    else:
        buf_h, buf_w = width, height

    # Row stride is byte-aligned (ceil(buf_w / 4) bytes per row).
    # For displays where buf_w is not a multiple of 4 (e.g. 213: 250x122, buf_w=122 -> 31 bytes),
    # trailing sub-pixels are padded with white (0b01) so no scanline pixels are truncated.
    num_col_groups = (buf_w + 3) // 4
    raw = bytearray()
    for row in range(buf_h):
        for col_group in range(num_col_groups):
            byte = 0
            for p in range(4):
                col = col_group * 4 + p
                if col < buf_w:
                    if row_major:
                        orig_x, orig_y = col, row
                    elif rotate_cw:
                        orig_x, orig_y = width - 1 - row, col
                    else:
                        orig_x, orig_y = row, height - 1 - col

                    idx = orig_y * width + orig_x
                    if plane_bw[idx]:
                        color = 0b00
                    elif plane_red[idx]:
                        color = 0b11
                    elif plane_yellow[idx]:
                        color = 0b10
                    else:
                        color = 0b01
                else:
                    color = 0b01  # Padding pixel is white
                byte |= color << (6 - p * 2)
            raw.append(byte)
    return bytes(raw)
