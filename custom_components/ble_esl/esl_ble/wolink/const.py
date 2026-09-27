"""WOLINK constants."""

from __future__ import annotations

BRAND = "Zhsunyco"
MANUFACTURER_ID = 0xBBAA

SERVICE_UUID = "30323032-4c53-4545-4c42-4b4e494c4f57"
DATA_CHAR = "31323032-4c53-4545-4c42-4b4e494c4f57"
AUTH_CHAR = "33323032-4c53-4545-4c42-4b4e494c4f57"
STATUS_CHAR = "34323032-4c53-4545-4c42-4b4e494c4f57"

AES_KEY = bytes.fromhex("9b609f28bc49e25729bd7b8df22b4420")

OP_WRITE_DATA = 0xA500
OP_REFRESH_COMPRESSED = 0xA502

DEVICE_ERRORS = {
    1: "epd initialization error",
    2: "epd write error",
    3: "data decompression error",
    4: "OTA error",
    5: "unlock failed",
}
ERROR_UNLOCK_FAILED = 5
