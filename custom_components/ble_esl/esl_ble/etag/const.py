"""ETAG GATT identifiers, timing and panel firmware."""

from __future__ import annotations

# Guangdong SID Technology, maker of the Bluetooth Label app (com.gdsid.tag).
BRAND = "Hipoink"
NAME_PREFIX = "ETAG-"

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
FIRMWARE_UUID = "00002a26-0000-1000-8000-00805f9b34fb"

REPLY_TIMEOUT_S = 30.0
REFRESH_SETTLE_S = 1.0

# Panel firmware read from FIRMWARE_UUID, mapped to whether the panel scans
# its columns and rows in reverse. NP61 is verified; MN50 is derived from the app.
PANELS = {"SE0213NP61-TNG-A0": False, "SE0213MN50-TNG-A0": True}

# Command bytes (second byte of every packet) and the reply command each gets.
CMD_IMAGE = 1
REPLIES = {5: 6, 0x11: 0x12, 7: 8, CMD_IMAGE: 2, 3: 4}
CMD_VERSION = 7  # its reply carries no status byte
