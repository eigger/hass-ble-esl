"""PickSmart constants."""

from __future__ import annotations

BRAND = "Gicisky"
MANUFACTURER_ID = 0x5053

SERVICE_UUID_PREFIX = "0000f"
SERVICE_UUIDS = (
    "0000fef0-0000-1000-8000-00805f9b34fb",
    "0000fdf0-0000-1000-8000-00805f9b34fb",
    "0000fcf0-0000-1000-8000-00805f9b34fb",
)

CMD_START = 0x01
CMD_SIZE = 0x02
CMD_IMAGE = 0x03
REPLY_START = bytes((0x01, 0xF4, 0x00))
REPLY_SIZE = 0x02
REPLY_PART = 0x05
PART_NEXT = 0x00  # "send part N" (N follows as u32 little endian)
PART_DONE = 0x08  # the tag has every part
PART_SIZE = 240

REPLY_TIMEOUT_S = 10.0

# A tag may drop the first START after the notification subscription, and a
# dropped START is never answered. So wait briefly, then probe: resend START
# on a short timeout until one is answered. Answers came in 0.05-0.19 s.
NOTIFY_SETTLE_S = 0.2
START_PROBE_TIMEOUT_S = 0.4
START_PROBE_ATTEMPTS = 3

# The tag asks for a part again when it could not take it. Give up after this
# many requests in a row for one part; the n-th resend first waits
# RESEND_BACKOFF_S * (n - 1).
MAX_SAME_PART_REQUESTS = 6
RESEND_BACKOFF_S = 0.05
