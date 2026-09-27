"""XTE constants."""

from __future__ import annotations

BRAND = "Poshiji"
MANUFACTURER_ID = 0x5258

SERVICE_UUID = "00002760-08c2-11e1-9073-0e8ac72e1001"
WRITE_UUID = "00002760-08c2-11e1-9073-0e8ac72e0001"
NOTIFY_UUID = "00002760-08c2-11e1-9073-0e8ac72e0002"

# Some adapters and proxies drop a write issued right after the CCCD write.
NOTIFY_SETTLE_S = 0.5
REPLY_TIMEOUT_S = 5.0
MAX_CHUNK = 244
MIN_CHUNK = 20

BLOCK_DATA_SIZE = 1211  # a 1220-byte block minus its 9-byte header

CMD_START = 0x01
CMD_END = 0x04
REPLY_START = bytes.fromhex("01ffbd")
REPLY_END = bytes.fromhex("04ff")

# The advertisement carries a percentage, not a voltage; flag the last tenth.
BATTERY_LOW_PERCENT = 10

# Tag types that group their 2-bit codes into nibbles; not implemented, so
# writes to them are refused before connecting.
UNSUPPORTED_PACKING_DEVICE_NUMBERS = frozenset({97, 102, 106, 109, 119, 122})
