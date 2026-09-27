"""easyTag frames: a 20-byte header and 204-byte packets, CRC'd and XOR-obfuscated."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .const import CMD_IMAGE, IDENTIFIER, KEY_INDEX_IMAGE, KEY_INDEX_REPLY, KEY_TABLE, MARKER

CHUNK = 200
KEY_INDEX_OFFSET = 9  # the header sends its key index in the clear


def crc16(data: bytes) -> int:
    """CRC-16/CMS: poly 0x8005, init 0xFFFF, no reflection, no final XOR."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1 ^ 0x8005 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def session_key(mac: str, key_index: int) -> int:
    """The six MAC bytes XORed together, XORed with the key table character."""
    key = ord(KEY_TABLE[key_index])
    for byte in bytes.fromhex(mac.replace(":", "")):
        key ^= byte
    return key


def obfuscate(data: bytes, key: int, *, keep: int | None = None) -> bytes:
    """XOR every byte with `key`, except the one at index `keep`."""
    return bytes(b if i == keep else b ^ key for i, b in enumerate(data))


def packet_count(size: int) -> int:
    """Data packets for a payload: (size + 201) // 200, one more than needed at 0 or 199 mod 200."""
    return (size + CHUNK + 1) // CHUNK


def image_frames(mac: str, payload: bytes) -> list[bytes]:
    """The header, then the payload in numbered 200-byte chunks, ready to write."""
    key = session_key(mac, KEY_INDEX_IMAGE)
    count = packet_count(len(payload))
    header = (
        bytes((0xFF, CMD_IMAGE))
        + IDENTIFIER
        + bytes((KEY_INDEX_IMAGE,))
        + struct.pack(">IH", len(payload), count)
        + MARKER
    )
    frames = [obfuscate(_with_crc(header), key, keep=KEY_INDEX_OFFSET)]
    for number in range(1, count + 1):
        chunk = payload[(number - 1) * CHUNK : number * CHUNK].ljust(CHUNK, b"\0")
        frames.append(obfuscate(_with_crc(struct.pack(">H", number) + chunk), key))
    return frames


def _with_crc(data: bytes) -> bytes:
    return data + struct.pack(">H", crc16(data))


@dataclass(frozen=True)
class Reply:
    """What the tag notifies once the panel has redrawn."""

    battery_mv: int
    temperature_c: int


def parse_reply(mac: str, frame: bytes) -> Reply | None:
    """Byte 2 is the battery in 0.1 V, byte 3 the temperature (signed °C)."""
    if len(frame) < 4:
        return None
    plain = obfuscate(frame, session_key(mac, KEY_INDEX_REPLY))
    return Reply(battery_mv=plain[2] * 100, temperature_c=int.from_bytes(plain[3:4], signed=True))
