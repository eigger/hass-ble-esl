"""easyTag constants."""

from __future__ import annotations

BRAND = "Zhsunyco"
NAME_PREFIX = "easyTag"

SERVICE_UUID = "00001523-1212-efde-1523-785feabcd123"
WRITE_UUID = "00001525-1212-efde-1523-785feabcd123"
NOTIFY_UUID = "00001526-1212-efde-1523-785feabcd123"

NOTIFY_SETTLE_S = 0.3
PRE_HEADER_S = 0.5
PACKET_GAP_S = 0.020
EVERY_FIFTH_EXTRA_S = 0.003
REPLY_TIMEOUT_S = 20.0

# XOR key: the MAC bytes XORed together, then a character of this table.
KEY_TABLE = (
    "b8b26356ec4473bd3f36e6495d756703a4bb835139f0b161423b5f286c4e97d6"
    "0015bab2cdefb7ae0fcb099b599cc44d391645dde4b89b6e50f53dc046ec25ac"
    "b8b26356ec4473bd3f36e6495d756703a4bb835139f0b161423b5f286c4e97d6"
    "0015bab2cdefb7ae0fcb099b599ac44d391645dde4b89b6e50f53dc046ec25ac"
)
KEY_INDEX_IMAGE = 98
KEY_INDEX_REPLY = 0

CMD_IMAGE = 0xFC
IDENTIFIER = b"easyTag"
MARKER = b"BT"
