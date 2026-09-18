"""Constants for easyTag (eLabel) ESL BLE protocol."""

from __future__ import annotations

SERVICE_UUID = "00001523-1212-efde-1523-785feabcd123"
WRITE_UUID = "00001525-1212-efde-1523-785feabcd123"
NOTIFY_UUID = "00001526-1212-efde-1523-785feabcd123"
CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"
NAME_PREFIX = "easyTag"

# Protocol frame timing delays (seconds)
CONNECT_TIMEOUT = 30.0
FEEDBACK_TIMEOUT = 20.0
POST_CCCD_DELAY = 0.300
PRE_HEADER_DELAY = 0.500
INTER_PACKET_DELAY = 0.020
EVERY_5TH_BONUS = 0.003
MAX_ATTEMPTS = 2

# Obfuscation key table (256 chars)
KEY_TABLE = (
    "b8b26356ec4473bd3f36e6495d756703a4bb835139f0b161423b5f286c4e97d6"
    "0015bab2cdefb7ae0fcb099b599cc44d391645dde4b89b6e50f53dc046ec25ac"
    "b8b26356ec4473bd3f36e6495d756703a4bb835139f0b161423b5f286c4e97d6"
    "0015bab2cdefb7ae0fcb099b599ac44d391645dde4b89b6e50f53dc046ec25ac"
)

KEY_INDEX_IMAGE = 98  # KEY_TABLE[98] == '1' -> magic 0x31
KEY_INDEX_CONFIG = 92  # KEY_TABLE[92] == 'c' -> magic 0x63
KEY_INDEX_NOTIFY = 0  # KEY_TABLE[0]  == 'b' -> magic 0x62

HEADER_LEN = 20
PACKET_LEN = 204
CHUNK_LEN = 200

# Brand the tags are sold under; used as the HA device manufacturer
BRAND = "Zhsunyco"
