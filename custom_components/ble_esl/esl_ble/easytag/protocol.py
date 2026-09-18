"""Pure protocol codecs, framing, CRC, RLE, and image quantization for easyTag."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import (
    CHUNK_LEN,
    HEADER_LEN,
    KEY_INDEX_CONFIG,
    KEY_INDEX_IMAGE,
    KEY_INDEX_NOTIFY,
    KEY_TABLE,
    PACKET_LEN,
)

if TYPE_CHECKING:
    from PIL import Image

# CRC-16/CMS: poly 0x8005, init 0xFFFF, MSB-first, no reflection, no xorout
def crc16(data: bytes, length: int | None = None) -> int:
    """CRC-16/CMS check value: crc16(b"123456789") == 0xAEE7."""
    n = len(data) if length is None else length
    crc = 0xFFFF
    for i in range(n):
        crc ^= data[i] << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


# Verify CRC self-test on load
if crc16(b"123456789") != 0xAEE7:
    raise RuntimeError("easyTag CRC-16/CMS self-test failed")


def mac_xor(mac: str) -> int:
    """Compute XOR of 6 MAC address bytes."""
    raw = bytes.fromhex(mac.replace(":", ""))
    x = 0
    for i in range(6):
        x ^= raw[i]
    return x


def xor_key(mac: str, key_index: int) -> int:
    """Derive session XOR key from MAC and key table index."""
    return mac_xor(mac) ^ ord(KEY_TABLE[key_index])


def obfuscate(buf: bytes, mac: str, key_index: int, *, skip_byte9: bool = False) -> bytes:
    """Apply XOR obfuscation to packet bytes."""
    k = xor_key(mac, key_index)
    return bytes(b if (skip_byte9 and i == 9) else b ^ k for i, b in enumerate(buf))


def packet_count(payload_len: int) -> int:
    """Calculate packet count for framed data payload: ((len + 204) - 3) // 200."""
    return (payload_len + PACKET_LEN - 3) // CHUNK_LEN


def build_header(
    cmd: int,
    ident: bytes,
    key_index: int,
    payload_len: int,
    count: int,
    marker: bytes,
    mac: str,
) -> bytes:
    """Build and obfuscate a 20-byte command header frame."""
    h = bytearray(HEADER_LEN)
    h[0] = 0xFF
    h[1] = cmd
    h[2:9] = ident
    h[9] = key_index
    h[10:14] = payload_len.to_bytes(4, "big")
    h[14:16] = count.to_bytes(2, "big")
    h[16:18] = marker
    h[18:20] = crc16(h, 18).to_bytes(2, "big")
    return obfuscate(bytes(h), mac, key_index, skip_byte9=True)


def build_data_packet(seq: int, chunk: bytes, key_index: int, mac: str) -> bytes:
    """Build and obfuscate a 204-byte data frame with trailing CRC."""
    p = bytearray(PACKET_LEN)
    p[0:2] = seq.to_bytes(2, "big")
    p[2 : 2 + len(chunk)] = chunk
    p[202:204] = crc16(p, 202).to_bytes(2, "big")
    return obfuscate(bytes(p), mac, key_index, skip_byte9=False)


def _frames(
    cmd: int,
    ident: bytes,
    key_index: int,
    marker: bytes,
    payload: bytes,
    mac: str,
) -> list[bytes]:
    count = packet_count(len(payload))
    out = [build_header(cmd, ident, key_index, len(payload), count, marker, mac)]
    for seq in range(1, count + 1):
        chunk = payload[(seq - 1) * CHUNK_LEN : seq * CHUNK_LEN]
        out.append(build_data_packet(seq, chunk, key_index, mac))
    return out


def build_image_frames(mac: str, payload: bytes) -> list[bytes]:
    """Command 0xFC: Send image data payload."""
    return _frames(0xFC, b"easyTag", KEY_INDEX_IMAGE, b"BT", payload, mac)


def build_status_frames(mac: str) -> list[bytes]:
    """Command 0xF0: Battery/temperature query ping (1 payload byte 0x00)."""
    return _frames(0xF0, b"easyTag", KEY_INDEX_CONFIG, b"BT", b"\x00", mac)


def parse_notify(mac: str, frame: bytes) -> dict:
    """De-obfuscate and unpack 20-byte notify response frame."""
    k = xor_key(mac, KEY_INDEX_NOTIFY)
    plain = bytes(b ^ k for b in frame)
    if len(plain) <= 3:
        return {}
    decivolts = plain[2]
    temp = plain[3] - 256 if plain[3] > 127 else plain[3]
    return {
        "battery_v": decivolts / 10.0,
        "battery_mv": decivolts * 100,
        "temperature_c": temp,
        "plain": plain.hex(),
    }


def compress_rle(pixels: list[int]) -> bytes:
    """Run-length encode bitplane pixels per eLabel k3.c#a."""
    out = bytearray()
    n, i = len(pixels), 0
    while i < n:
        val = pixels[i]
        run = 0
        while i + run < n and pixels[i + run] == val and run < 0xFFFF:
            run += 1
        if run < 7:
            byte = 0x80 | (val << 6)
            for k in range(1, 7):
                if i + k < n:
                    byte |= pixels[i + k] << (6 - k)
            out.append(byte)
            i += 7
        elif run <= 31:
            out.append((val << 6) | run)
            i += run
        elif run <= 255:
            out.append((val << 6) | 1)
            out.append(run)
            i += run
        else:
            out.append((val << 6) | 0)
            out.append(run & 0xFF)
            out.append((run >> 8) & 0xFF)
            i += run
    return bytes(out)


def decompress_rle(data: bytes, count: int) -> list[int]:
    """Decompress RLE bitplane bytes."""
    out: list[int] = []
    i = 0
    while i < len(data) and len(out) < count:
        b = data[i]
        i += 1
        if b & 0x80:
            for k in range(7):
                out.append((b >> (6 - k)) & 1)
        else:
            c, f = (b >> 6) & 1, b & 0x3F
            if f >= 2:
                run = f
            elif f == 1:
                run = data[i]
                i += 1
            else:
                run = data[i] | (data[i + 1] << 8)
                i += 2
            out.extend([c] * run)
    return out


def align8(v: int) -> int:
    """Round up to nearest multiple of 8."""
    return (v + 7) & ~7


def _pack_msb(plane: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(plane), 8):
        byte = 0
        for k, bit in enumerate(plane[i : i + 8]):
            byte |= bit << (7 - k)
        out.append(byte)
    return bytes(out)


def encode_image(
    plane_bw: list[int],
    plane_red: list[int] | None,
    width: int,
    height: int,
) -> bytes:
    """Serialize bitplanes, choosing shorter of RLE vs raw encoding."""
    w, h = align8(width), align8(height)
    expected = w * h
    if len(plane_bw) != expected:
        raise ValueError(
            f"plane_bw must be {expected} entries (got {len(plane_bw)})"
        )

    def hx(v: int, digits: int) -> str:
        return f"{v:0{digits}X}"

    # RLE vs Raw
    rle_bw = compress_rle(plane_bw)
    fc = f"FC{hx(0, 4)}{hx(0, 4)}{hx(h - 1, 4)}{hx(w - 1, 4)}{hx(len(rle_bw), 8)}{rle_bw.hex().upper()}"
    raw_bw = _pack_msb(plane_bw)
    fe = f"FE{hx(0, 4)}{hx(0, 4)}{hx(h - 1, 4)}{hx(w - 1, 4)}{raw_bw.hex().upper()}"

    if plane_red is not None:
        rle_red = compress_rle(plane_red)
        fc += (
            f"FC8{hx(0, 3)}{hx(0, 4)}8{hx(h - 1, 3)}{hx(w - 1, 4)}"
            f"{hx(len(rle_red), 8)}{rle_red.hex().upper()}"
        )
        raw_red = _pack_msb(plane_red)
        fe += f"03{hx(0, 4)}{hx(0, 4)}{hx(h - 1, 4)}{hx(w - 1, 4)}{raw_red.hex().upper()}"

    return bytes.fromhex(fc if len(fc) <= len(fe) else fe)


PALETTE_BW = [(0, 0, 0), (250, 250, 250)]
PALETTE_BWR = [(0, 0, 0), (250, 250, 250), (230, 0, 0)]


def quantize_image(
    image: Image.Image,
    width: int,
    height: int,
    colors: str = "BWR",
    dither: bool = True,
) -> tuple[list[int], list[int] | None]:
    """Quantize PIL image to 8-aligned BW and Red bitplanes."""
    img_rgb = image.convert("RGB")
    palette = PALETTE_BWR if "R" in colors else PALETTE_BW
    has_red = "R" in colors

    px = [
        [list(img_rgb.getpixel((x, y))) for y in range(height)]
        for x in range(width)
    ]
    idx = [[0] * height for _ in range(width)]

    for x in range(width):
        for y in range(height):
            c = px[x][y]
            best, bd = 0, 1 << 30
            for n, p in enumerate(palette):
                d = sum((c[k] - p[k]) ** 2 for k in range(3))
                if d < bd:
                    best, bd = n, d
            idx[x][y] = best
            if not dither:
                continue
            for k in range(3):
                err = c[k] - palette[best][k]

                def add(nx, ny, num):
                    px[nx][ny][k] = max(
                        0, min(255, px[nx][ny][k] + ((err * num) >> 4))
                    )

                if y + 1 < height:
                    add(x, y + 1, 7)
                if x + 1 < width:
                    if y - 1 > 0:
                        add(x + 1, y - 1, 3)
                    add(x + 1, y, 5)
                    if y + 1 < height:
                        add(x + 1, y + 1, 1)

    w, h = align8(width), align8(height)
    bw = [0] * (w * h)
    red = [0] * (w * h) if has_red else None
    for x in range(width):
        for y in range(height):
            i = y * w + x
            if idx[x][y] == 0:
                bw[i] = 1  # black ink
            elif idx[x][y] == 2 and red is not None:
                red[i] = 1  # red ink

    return bw, red
