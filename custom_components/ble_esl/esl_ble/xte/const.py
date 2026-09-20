"""XTE constants."""

BRAND = "Poshiji"
SERVICE_UUID = "00002760-08c2-11e1-9073-0e8ac72e1001"
WRITE_UUID = "00002760-08c2-11e1-9073-0e8ac72e0001"
NOTIFY_UUID = "00002760-08c2-11e1-9073-0e8ac72e0002"
MANUFACTURER_ID = 0x5258
# The advertisement carries a percentage, not a voltage; flag the last tenth.
BATTERY_LOW_PERCENT = 10
BLOCK_DATA_SIZE = 1211  # 1220-byte logical block, including its 9-byte header.
# Settle after enabling notifications before the first command, like the other
# backends (PickSmart 0.2 s, easyTag 0.8 s); some adapters and proxies drop a
# write issued immediately after the CCCD write.
NOTIFY_SETTLE_S = 0.5
# Two-bit pixel value -> RGB, per preset ``colors``. Only the BWRY mapping
# (00 black, 01 white, 10 yellow, 11 red) has been captured; a model with
# another palette needs its mapping added here before its preset can load.
PALETTES: dict[str, tuple[tuple[int, int, int], ...]] = {
    "BWRY": ((0, 0, 0), (255, 255, 255), (255, 255, 0), (255, 0, 0)),
}
