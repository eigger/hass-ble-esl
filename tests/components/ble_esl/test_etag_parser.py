"""ETAG advertisement matcher and protocol discovery."""

from types import SimpleNamespace

import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble.etag.devices import PRESETS, preset_for_advertisement
from custom_components.ble_esl.esl_ble.etag.parser import EtagParser, is_etag_advertisement
from tests.components.ble_esl.bt import binary_values, sensor_values

# Captured ETAG flags and service UUIDs; the battery AD record follows.
PREFIX = bytes.fromhex("02010605030a18f5fe1107595a00e4862a9e8fe911bc7c98434218")


def _info(name="ETAG-52500058B6", **kwargs):
    return SimpleNamespace(
        name=name,
        address="48:87:2D:C5:C3:19",
        rssi=-71,
        manufacturer_data={0x8748: bytes.fromhex("2dc5c319")},
        service_uuids=[],
        **kwargs,
    )


def test_matches_only_etag_names():
    assert is_etag_advertisement(_info("ETAG-52500058B6"))
    assert not is_etag_advertisement(_info("easyTag3D"))
    assert not is_etag_advertisement(_info(None))


def test_discovery_names_the_model():
    info = _info("ETAG-52500058B6")
    protocol = esl_ble.detect(info)
    assert protocol.id == "etag"
    assert protocol.parse_advertisement(info).model_key == "etag213"
    assert preset_for_advertisement(info) is PRESETS["etag213"]
    assert protocol.preset_for(None).height == 122
    assert protocol.parse_advertisement(_info("other")) is None


@pytest.mark.parametrize("percent", [0, 10, 11, 94, 95, 100])
def test_advertised_battery_percentage(percent):
    """Publish the app's percentage directly, including a valid zero reading."""
    update = EtagParser().update(_info(raw=PREFIX + bytes((2, 255, percent))))
    assert sensor_values(update)["battery"] == percent
    assert binary_values(update)["battery"] is (percent <= 10)
    assert "voltage" not in sensor_values(update)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        b"",
        PREFIX,
        PREFIX + b"\x02\xff",
        PREFIX + b"\x02\xff\x65",
        PREFIX + b"\x02\xff\xff",
        PREFIX + b"\x03\xff\x5f\x00",
        PREFIX + b"\x00\x02\xff\x5f",
        b"\x1f\x09\x02\xff\x5f",
    ],
)
def test_missing_or_invalid_battery(raw):
    """Do not infer charge from the MAC record, truncated data or invalid values."""
    update = EtagParser().update(_info(raw=raw))
    assert "battery" not in sensor_values(update)
    assert "battery" not in binary_values(update)


def test_older_service_info_without_raw():
    """Older HA versions and sources without raw data retain discovery support."""
    assert "battery" not in sensor_values(EtagParser().update(_info()))
    assert esl_ble.EtagProtocol().parse_advertisement(_info()).raw == {}


def test_scan_response_preserves_last_battery():
    """The separate MAC/name scan response does not erase an advertised reading."""
    parser = EtagParser()
    parser.update(_info(raw=PREFIX + b"\x02\xff\x5e"))
    update = parser.update(_info(raw=bytes.fromhex("07ff48872dc5c319")))
    assert sensor_values(update)["battery"] == 94


def test_battery_updates_and_record_offsets():
    """Walk AD lengths rather than assuming the app's fixed byte offset."""
    parser = EtagParser()
    parser.update(_info(raw=PREFIX + b"\x02\xff\x5f"))
    update = parser.update(_info(raw=bytes.fromhex("07ff48872dc5c31902ff0a")))
    assert sensor_values(update)["battery"] == 10
    assert binary_values(update)["battery"] is True


def test_other_device_does_not_publish_battery():
    update = EtagParser().update(_info("Other", raw=PREFIX + b"\x02\xff\x5f"))
    assert "battery" not in sensor_values(update)


def test_protocol_reports_battery_in_diagnostics():
    protocol = esl_ble.EtagProtocol()
    assert protocol.capabilities.passive_battery
    parsed = protocol.parse_advertisement(_info(raw=PREFIX + b"\x02\xff\x5f"))
    assert parsed.raw == {"battery_percent": 95}
    assert parsed.model_key == "etag213"
    assert parsed.battery_mv is None
