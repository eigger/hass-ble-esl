"""ETAG advertisement matcher and protocol discovery."""

from types import SimpleNamespace

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble.etag.devices import PRESETS, preset_for_advertisement
from custom_components.ble_esl.esl_ble.etag.parser import is_etag_advertisement


def _info(name):
    return SimpleNamespace(name=name, manufacturer_data={}, service_uuids=[])


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
