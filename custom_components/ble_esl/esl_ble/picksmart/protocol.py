"""Image quantization, pixel packing, and packet framing for PickSmart (gicisky)."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING
from PIL import Image

from ..base import DevicePreset
from .compression import compress as compress_quicklz

if TYPE_CHECKING:
    pass


def overlay_images(
    base: Image.Image,
    overlay: Image.Image,
    position: tuple[int, int] = (0, 0),
    center: bool = False,
) -> Image.Image:
    """Overlay image on top of base image."""
    base_rgb = base.convert("RGB") if base.mode != "RGB" else base.copy()
    w_base, h_base = base_rgb.size
    ov = overlay.convert("RGB")
    if ov.width > w_base or ov.height > h_base:
        ov = ov.crop((0, 0, w_base, h_base))
    if center:
        position = ((w_base - ov.width) // 2, (h_base - ov.height) // 2)
    base_rgb.paste(ov, position)
    return base_rgb


def make_cmd_packet(cmd: int, packet_size: int, compression2: bool = False) -> bytes:
    """Build command handshake packet."""
    if cmd == 0x02:
        if compression2:
            packet = bytearray(6)
            packet[0] = cmd
            struct.pack_into("<I", packet, 1, packet_size)
            packet[5] = 0x01
            return bytes(packet)
        packet = bytearray(8)
        packet[0] = cmd
        struct.pack_into("<I", packet, 1, packet_size)
        packet[-3:] = b"\x00\x00\x00"
        return bytes(packet)
    return bytes([cmd])


def make_size_packet(part: int, image_packets: bytes | list[int]) -> bytes:
    """Build 240-byte chunk packet with part sequence header."""
    start = part * 240
    packet_size = len(image_packets)
    chunk = image_packets[start : start + min(240, packet_size - start)]
    packet = bytearray(4 + len(chunk))
    struct.pack_into("<I", packet, 0, part)
    packet[4:] = bytes(chunk)
    return bytes(packet)


def _make_four_color_packet(
    pixels,
    width: int,
    height: int,
    mirror_x: bool,
    mirror_y: bool,
    invert_luminance: bool,
) -> bytes:
    byte_data = bytearray()
    current_byte = 0
    shift_counter = 3

    y_range = range(height - 1, -1, -1) if mirror_y else range(height)
    x_range = range(width - 1, -1, -1) if mirror_x else range(width)

    for y in y_range:
        for x in x_range:
            r, g, b = pixels[x, y]
            pixel_is_white = r > 128 and g > 128 and b > 128
            pixel_is_black = r <= 128 and g <= 128 and b <= 128
            is_white = pixel_is_black if invert_luminance else pixel_is_white

            is_red = r > 128
            is_green = g > 128
            is_blue = b > 128
            if is_green and is_red and is_blue:
                is_green = False
            if is_red and is_white:
                is_red = False

            # 00: Black, 01: White, 10: Yellow, 11: Red
            val = 2 if is_green else (3 if is_red else (1 if is_white else 0))
            current_byte |= val << (shift_counter * 2)

            if shift_counter == 0:
                byte_data.append(current_byte)
                current_byte = 0
                shift_counter = 3
            else:
                shift_counter -= 1

    return bytes(byte_data)


def _compress_byte_data(
    byte_data: list[int], byte_data_red: list[int] | None, width: int, height: int
) -> bytes:
    byte_per_line = height // 8
    buf = bytearray([0x00, 0x00, 0x00, 0x00])
    pos = 0
    for _ in range(width):
        buf.extend([
            0x75,
            byte_per_line + 7,
            byte_per_line,
            0x00, 0x00, 0x00, 0x00,
        ])
        buf.extend(byte_data[pos : pos + byte_per_line])
        pos += byte_per_line

    if byte_data_red is not None:
        pos = 0
        for _ in range(width):
            buf.extend([
                0x75,
                byte_per_line + 7,
                byte_per_line,
                0x00, 0x00, 0x00, 0x00,
            ])
            buf.extend(byte_data_red[pos : pos + byte_per_line])
            pos += byte_per_line

    total_len = len(buf)
    struct.pack_into("<I", buf, 0, total_len)
    return bytes(buf)


def _compress_byte_data_2(
    pixels,
    width: int,
    height: int,
    mirror_x: bool,
    mirror_y: bool,
    invert_luminance: bool,
) -> bytes:
    total_pixels = width * height
    plane_bytes = total_pixels // 8
    bw_plane = bytearray(plane_bytes)
    red_plane = bytearray(plane_bytes)
    byte_idx = 0
    bit_pos = 7

    y_range = range(height - 1, -1, -1) if mirror_y else range(height)
    x_range = range(width - 1, -1, -1) if mirror_x else range(width)

    for y in y_range:
        for x in x_range:
            r, g, b = pixels[x, y]
            pixel_is_white = r > 128 and g > 128 and b > 128
            pixel_is_black = r <= 128 and g <= 128 and b <= 128
            is_white = pixel_is_black if invert_luminance else pixel_is_white
            is_red = (r > 128) and (g <= 128)

            if is_white:
                bw_plane[byte_idx] |= 1 << bit_pos
            if is_red:
                red_plane[byte_idx] |= 1 << bit_pos

            bit_pos -= 1
            if bit_pos < 0:
                byte_idx += 1
                bit_pos = 7

    raw = bytes(bw_plane) + bytes(red_plane)
    try:
        return compress_quicklz(raw)
    except Exception:
        return raw


def encode_image(image: Image.Image, preset: DevicePreset) -> bytes:
    """Encode PIL Image to PickSmart byte stream per preset configurations."""
    extra = preset.extra
    tft = extra.get("tft", False)
    rotation = extra.get("rotation", 0)
    mirror_x = extra.get("mirror_x", False)
    mirror_y = extra.get("mirror_y", False)
    compression = extra.get("compression", False)
    compression2 = extra.get("compression2", False)
    invert_luminance = extra.get("invert_luminance", False)
    four_color = extra.get("four_color", False)
    support_red = "R" in preset.colors

    img = Image.new("RGB", (preset.width, preset.height), color="white")
    img = overlay_images(img, image)

    width, height = img.size
    if tft:
        img = img.resize((width // 2, height * 2), resample=Image.BICUBIC)

    if rotation != 0:
        img = img.rotate(rotation, expand=True)

    width, height = img.size
    pixels = img.load()

    if four_color:
        return _make_four_color_packet(
            pixels, width, height, mirror_x, mirror_y, invert_luminance
        )

    if compression2:
        return _compress_byte_data_2(
            pixels, width, height, mirror_x, mirror_y, invert_luminance
        )

    byte_data = []
    byte_data_red = []
    current_byte = 0
    current_byte_red = 0
    bit_pos = 7

    y_range = range(height - 1, -1, -1) if mirror_y else range(height)
    x_range = range(width - 1, -1, -1) if mirror_x else range(width)

    for y in y_range:
        for x in x_range:
            r, g, b = pixels[x, y]
            pixel_is_white = r > 128 and g > 128 and b > 128
            pixel_is_black = r <= 128 and g <= 128 and b <= 128
            is_white = pixel_is_black if invert_luminance else pixel_is_white

            if is_white:
                current_byte |= 1 << bit_pos
            if (r > 128) and (g <= 128) and (b <= 128):
                current_byte_red |= 1 << bit_pos

            bit_pos -= 1
            if bit_pos < 0:
                byte_data.append(current_byte)
                byte_data_red.append(current_byte_red)
                current_byte = 0
                current_byte_red = 0
                bit_pos = 7

    if bit_pos != 7:
        byte_data.append(current_byte)
        byte_data_red.append(current_byte_red)

    if compression:
        return _compress_byte_data(
            byte_data, byte_data_red if support_red else None, width, height
        )

    combined = byte_data + byte_data_red if support_red else byte_data
    return bytes(combined)
