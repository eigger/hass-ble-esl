"""Decode Minew tagble_v3 identification advertisements."""

from .const import COMPANY_ID


def device_info(advertisement):
    """Decode CA00 identification frames; CA21 status frames have no tag ID."""
    payload = advertisement.manufacturer_data.get(COMPANY_ID)
    if payload is None or payload[:2] != b"\xca\x00":
        return None
    if len(payload) != 24:
        raise ValueError(f"Expected a 24-byte Minew CA00 frame, got {len(payload)}")
    firmware = int.from_bytes(payload[9:11], "big")
    fields = int.from_bytes(payload[11:19], "big")
    return {
        "id": payload[2:8][::-1].hex().upper(),
        "battery_percent": payload[8],
        "firmware": f"{firmware >> 13}.{(firmware >> 7) & 63}.{firmware & 127}",
        "screen_id": (fields >> 16) & 0xFFF,
        "product_id": f"{(fields >> 28) & 0xFFFF:04x}",
    }
