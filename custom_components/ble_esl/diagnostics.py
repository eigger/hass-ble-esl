"""Diagnostics support for BLE ESL.

Powers "Download diagnostics" on the device page. The aim is that a support
report needs nothing else: which backend and preset are in use, what the tag
advertises (model / firmware), the options in force, and the write state
and failure counters at the time of the download.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEBOUNCE_MS,
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_RETRY_COUNT,
    DEFAULT_DEBOUNCE_MS,
    DEFAULT_PREVENT_DUPLICATE_SEND,
    DEFAULT_RETRY_COUNT,
)
from .types import BleEslConfigEntry

OPTION_DEFAULTS = {
    CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
    CONF_PREVENT_DUPLICATE_SEND: DEFAULT_PREVENT_DUPLICATE_SEND,
    CONF_DEBOUNCE_MS: DEFAULT_DEBOUNCE_MS,
}

# The MAC identifies the tag's owner across reports; the 8-hex-digit
# identifier used in entity names is enough to tell devices apart.
TO_REDACT = {"address", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BleEslConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data
    backend = data.backend
    preset = data.preset

    service_info = async_last_service_info(hass, data.address, connectable=True)
    advertisement: dict[str, Any] | None = None
    if service_info is not None:
        try:
            parsed = _asdict_or_none(backend.parse_advertisement(service_info))
        except Exception as err:  # a bad frame must not break the download
            parsed = {"error": f"{type(err).__name__}: {err}"}
        advertisement = {
            # Some tags advertise their MAC as the name; the source may be a
            # proxy's MAC. Mask the tag's address wherever it appears.
            "name": _mask_mac(service_info.name, data.address),
            "rssi": service_info.rssi,
            "source": _mask_mac(service_info.source, data.address),
            "connectable": service_info.connectable,
            "time": service_info.time,
            "manufacturer_data": {
                f"0x{company:04X}": bytes(payload).hex()
                for company, payload in service_info.manufacturer_data.items()
            },
            "service_uuids": list(service_info.service_uuids),
            "parsed": parsed,
        }

    last_failure = data.last_failure_coordinator.data
    diagnostics = {
        "entry": {
            "version": entry.version,
            "unique_id": entry.unique_id,
            "data": dict(entry.data),
            "options": dict(entry.options),
            # What the write pipeline actually uses: defaults < data < options.
            "effective_options": {**OPTION_DEFAULTS, **entry.data, **entry.options},
        },
        "backend": {
            "id": backend.id,
            "label": backend.label,
            "name": backend.name,
            "brand": backend.brand,
            "capabilities": dataclasses.asdict(backend.capabilities),
        },
        "preset": {
            **dataclasses.asdict(preset),
            "extra": dict(preset.extra),
            "verified": preset.verified,
        },
        "device": {
            "identifier": data.identifier,
            "address": data.address,
            "manufacturer": data.manufacturer,
            "model": data.model,
            "sw_version": data.sw_version,
            "hw_version": data.hw_version,
        },
        "advertisement": advertisement,
        "write_state": {
            "write_lock": data.write_lock,
            "in_progress": data.start_time is not None,
            "debounce_pending": data.pending_write_cancel is not None,
            "write_generation": data.write_generation,
            "last_image_png_bytes": len(data.last_image_data) if data.last_image_data else None,
            "last_write": data.last_write_timing,
            "last_failure_write": data.last_failure_timing,
        },
        "sensors": {
            "connectivity": data.connectivity_coordinator.data,
            "write_duration_s": data.duration_coordinator.data,
            "failure_count": data.failure_coordinator.data,
            "last_failure": last_failure.isoformat() if last_failure else None,
            "battery_v": data.battery_coordinator.data,
            "temperature_c": data.temperature_coordinator.data,
        },
    }
    return async_redact_data(diagnostics, TO_REDACT)


def _mask_mac(value: Any, address: str) -> Any:
    """Replace the tag's MAC (with or without colons, any case) inside a string."""
    if not isinstance(value, str):
        return value
    plain = address.replace(":", "")
    for needle in (address, plain, address.lower(), plain.lower()):
        if needle and needle in value:
            value = value.replace(needle, "**REDACTED**")
    return value


def _asdict_or_none(obj: Any) -> dict[str, Any] | None:
    if obj is None:
        return None
    result = dataclasses.asdict(obj)
    if "raw" in result:
        result["raw"] = dict(result["raw"])
    return result
