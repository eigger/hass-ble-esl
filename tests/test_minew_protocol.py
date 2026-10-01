"""Minew discovery and explicit refusal of unverified writes."""

from types import SimpleNamespace

import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble.base import WriteRefused


async def test_minew_is_explicitly_discovery_only():
    info = SimpleNamespace(name="", manufacturer_data={0x0639: b"\xca\x21"}, service_uuids=[])
    protocol = esl_ble.detect(info)
    assert protocol.id == "minew"
    assert protocol.writable is False
    with pytest.raises(WriteRefused, match="not yet verified"):
        await protocol.write_prepared(None, None, None)


def identification_frame(screen_id=65):
    """Synthetic CA00 frame with independently chosen packed metadata."""
    payload = bytearray(24)
    payload[:2] = b"\xca\x00"
    payload[2:8] = bytes.fromhex("8033080000e1")
    payload[8] = 87
    payload[9:11] = ((2 << 13) | (5 << 7) | 9).to_bytes(2, "big")
    payload[11:19] = ((0x1234 << 28) | (screen_id << 16)).to_bytes(8, "big")
    return bytes(payload)


def test_identification_model_firmware_and_battery():
    from bt import sensor_values, service_info

    from custom_components.ble_esl.esl_ble.minew.wire import device_info

    info = service_info("E1:00:00:08:33:80", manufacturer_data={0x0639: identification_frame()})
    metadata = device_info(info)
    assert metadata == {
        "id": "E10000083380",
        "battery_percent": 87,
        "firmware": "2.5.9",
        "screen_id": 65,
        "product_id": "1234",
    }
    protocol = esl_ble.detect(info)
    advertisement = protocol.parse_advertisement(info)
    assert advertisement.model_key == "mtag15"
    assert advertisement.sw_version == "2.5.9"
    update = protocol.create_parser(protocol.preset_for("mtag15")).update(info)
    assert sensor_values(update)["battery"] == 87


def test_unknown_screen_and_status_do_not_claim_a_model():
    from bt import service_info

    protocol = esl_ble.get("minew")
    unknown = service_info(
        "E1:00:00:08:33:80", manufacturer_data={0x0639: identification_frame(123)}
    )
    assert protocol.supported(unknown)
    assert protocol.parse_advertisement(unknown).model_key is None
    status = service_info("E1:00:00:08:33:80", manufacturer_data={0x0639: b"\xca\x21"})
    assert protocol.supported(status)
    assert protocol.parse_advertisement(status) is None


def test_malformed_identification_fails_explicitly():
    from custom_components.ble_esl.esl_ble.minew.wire import device_info

    with pytest.raises(ValueError, match="24-byte"):
        device_info(SimpleNamespace(manufacturer_data={0x0639: b"\xca\x00"}))
