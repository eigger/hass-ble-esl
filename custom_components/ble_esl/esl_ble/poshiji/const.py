"""Poshiji PSJ-420 XTE constants."""

BRAND = "Poshiji"
SERVICE_UUID = "00002760-08c2-11e1-9073-0e8ac72e1001"
WRITE_UUID = "00002760-08c2-11e1-9073-0e8ac72e0001"
NOTIFY_UUID = "00002760-08c2-11e1-9073-0e8ac72e0002"
MANUFACTURER_ID = 0x5258
# Two observed PSJ-420 advertisements differ only in the final byte (1e/1b).
# Its meaning is unconfirmed; exclude it from the model fingerprint, but keep
# the exact length and remaining bytes to avoid claiming other XTE models.
ADVERTISEMENT = bytes.fromhex("fd024002009964060102ffff1e")
WIDTH, HEIGHT = 400, 300
BLOCK_DATA_SIZE = 1211  # 1220-byte logical block, including its 9-byte header.
# Settle after enabling notifications before the first command, like the other
# backends (PickSmart 1.0 s, WOLINK 0.5 s, easyTag 0.3 s); some adapters and
# proxies drop a write issued immediately after the CCCD write.
NOTIFY_SETTLE_S = 0.5
PALETTE = ((0, 0, 0), (255, 255, 255), (255, 255, 0), (255, 0, 0))
