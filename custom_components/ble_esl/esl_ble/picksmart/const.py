"""Constants for PickSmart (gicisky) ESL BLE protocol."""

from __future__ import annotations

MANUFACTURER_ID = 20563  # 0x5053

SERVICE_UUID_PREFIX = "0000f"
SERVICE_UUIDS = (
    "0000fef0-0000-1000-8000-00805f9b34fb",
    "0000fdf0-0000-1000-8000-00805f9b34fb",
    "0000fcf0-0000-1000-8000-00805f9b34fb",
)

CMD_START = 0x01
CMD_SIZE = 0x02
CMD_IMAGE = 0x03
RESP_IMAGE_DATA = 0x05

CONNECT_TIMEOUT = 30.0
FEEDBACK_TIMEOUT = 10.0

# The tag re-requests a chunk it could not accept. Give up only after this
# many consecutive requests for the same part; the n-th resend first waits
# RESEND_BACKOFF_S * n (50 ms, 100 ms, ...) to let the tag finish its
# previous write.
MAX_SAME_PART_REQUESTS = 6
RESEND_BACKOFF_S = 0.05

# Brand the tags are sold under; used as the HA device manufacturer
BRAND = "Gicisky"
