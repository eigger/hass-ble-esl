"""Constants for the BLE ESL integration."""

from __future__ import annotations

from asyncio import Lock

from homeassistant.util.hass_dict import HassKey

DOMAIN = "ble_esl"

SERVICE_WRITE = "write"
SERVICE_WRITE_GUARDED = "write_guarded"

#: hass.data key of the single asyncio.Lock that serialises BLE writes across
#: all tags (one transfer at a time per HA instance).
DATA_LOCK: HassKey[Lock] = HassKey(f"{DOMAIN}_ble_lock")

# Options / Config keys
CONF_PROTOCOL = "protocol"
CONF_MODEL = "model"
CONF_RETRY_COUNT = "retry_count"
CONF_WRITE_DELAY_MS = "write_delay_ms"
CONF_PREVENT_DUPLICATE_SEND = "prevent_duplicate_send"
CONF_DEBOUNCE_MS = "debounce_ms"

# Defaults
DEFAULT_PROTOCOL = "wolink"
DEFAULT_MODEL = "290"
DEFAULT_RETRY_COUNT = 3
DEFAULT_WRITE_DELAY_MS = 0
DEFAULT_PREVENT_DUPLICATE_SEND = False
DEFAULT_DEBOUNCE_MS = 0

# Session-polled battery (e.g. easyTag): % is a linear map of the voltage over
# min-max, and at or below min the battery-low binary sensor turns on.
SESSION_MIN_VOLTAGE = 2.2
SESSION_MAX_VOLTAGE = 3.0

#: Config-entry data key under which the write-lock switch persists its state.
WRITE_LOCK = "write_lock"
