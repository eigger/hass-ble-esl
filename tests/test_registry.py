"""Tests for protocol registry, lookup, and mutual exclusivity detection."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble.base import BleBackend, BleParser, Capabilities, DevicePreset
from custom_components.ble_esl.esl_ble.easytag.const import (
    SERVICE_UUID as EASYTAG_SERVICE_UUID,
)
from custom_components.ble_esl.esl_ble.picksmart.const import (
    MANUFACTURER_ID as PICKSMART_MFR_ID,
    SERVICE_UUIDS as PICKSMART_SERVICE_UUIDS,
)
from custom_components.ble_esl.esl_ble.wolink.const import (
    MANUFACTURER_ID as WOLINK_MFR_ID,
    SERVICE_UUID as WOLINK_SERVICE_UUID,
)
from custom_components.ble_esl.esl_ble.xte.const import MANUFACTURER_ID as XTE_MFR_ID


def test_registry_get():
    """Verify backend retrieval by protocol ID."""
    assert esl_ble.get("wolink").id == "wolink"
    assert esl_ble.get("easytag").id == "easytag"
    assert esl_ble.get("picksmart").id == "picksmart"
    assert esl_ble.get("xte").id == "xte"

    with pytest.raises(KeyError, match="Unknown BLE backend: 'unknown'"):
        esl_ble.get("unknown")


def test_registry_all_backends():
    """Verify all_backends lists registered backends."""
    backend_ids = [b.id for b in esl_ble.all_backends()]
    assert "wolink" in backend_ids
    assert "easytag" in backend_ids
    assert "picksmart" in backend_ids
    assert "xte" in backend_ids


def test_registry_detect_mutual_exclusivity():
    """Verify the bundled protocols are strictly mutually exclusive during advertisement detection."""
    wolink_backend = esl_ble.get("wolink")
    easytag_backend = esl_ble.get("easytag")
    picksmart_backend = esl_ble.get("picksmart")
    xte_backend = esl_ble.get("xte")

    # 1. WOLINK Advertisement
    info_wolink = MagicMock()
    info_wolink.manufacturer_data = {WOLINK_MFR_ID: b"\x00" * 10}
    info_wolink.service_uuids = [WOLINK_SERVICE_UUID]
    info_wolink.name = "WOLINK_TAG"

    assert wolink_backend.supported(info_wolink) is True
    assert easytag_backend.supported(info_wolink) is False
    assert picksmart_backend.supported(info_wolink) is False
    assert xte_backend.supported(info_wolink) is False
    assert esl_ble.detect(info_wolink) is wolink_backend

    # 2. easyTag Advertisement
    info_easytag = MagicMock()
    info_easytag.manufacturer_data = {}
    info_easytag.service_uuids = [EASYTAG_SERVICE_UUID]
    info_easytag.name = "easyTag3D:00:11:22"

    assert easytag_backend.supported(info_easytag) is True
    assert wolink_backend.supported(info_easytag) is False
    assert picksmart_backend.supported(info_easytag) is False
    assert xte_backend.supported(info_easytag) is False
    assert esl_ble.detect(info_easytag) is easytag_backend

    # 3. PickSmart Advertisement
    info_picksmart = MagicMock()
    info_picksmart.manufacturer_data = {PICKSMART_MFR_ID: b"\x33\x1e\x81\x01\x40"}
    info_picksmart.service_uuids = [PICKSMART_SERVICE_UUIDS[0]]
    info_picksmart.name = "BleTag"

    assert picksmart_backend.supported(info_picksmart) is True
    assert wolink_backend.supported(info_picksmart) is False
    assert easytag_backend.supported(info_picksmart) is False
    assert xte_backend.supported(info_picksmart) is False
    assert esl_ble.detect(info_picksmart) is picksmart_backend

    # 4. XTE Advertisement
    info_xte = MagicMock()
    info_xte.manufacturer_data = {XTE_MFR_ID: bytes.fromhex("fd024002009964060102ffff1e")}
    info_xte.service_uuids = []
    info_xte.name = "FFEEDDCCBBAA"

    assert xte_backend.supported(info_xte) is True
    assert wolink_backend.supported(info_xte) is False
    assert easytag_backend.supported(info_xte) is False
    assert picksmart_backend.supported(info_xte) is False
    assert esl_ble.detect(info_xte) is xte_backend

    # 5. Unknown Advertisement
    info_other = MagicMock()
    info_other.manufacturer_data = {0x9999: b"\x00"}
    info_other.service_uuids = ["0000ffff-0000-1000-8000-00805f9b34fb"]
    info_other.name = "OtherDevice"

    assert esl_ble.detect(info_other) is None


def test_registry_custom_backend(monkeypatch):
    """Verify registering a new protocol backend dynamically."""
    monkeypatch.setattr(esl_ble, "_BACKENDS", dict(esl_ble._BACKENDS))

    class MockParser(BleParser):
        brand = "Mock"
        fallback_name = "Mock"
        is_advertisement = staticmethod(lambda info: "mock_uuid" in info.service_uuids)

    class MockTestBackend(BleBackend):
        id = "mock_test"
        label = "MOCK"
        name = "Mock Protocol"
        capabilities = Capabilities(
            passive_battery=False,
            session_battery=True,
            session_temperature=True,
            model_detection=False,
            palettes=("BW",),
        )
        PRESETS = {"m": DevicePreset(key="m", display_name="Mock", width=8, height=8, colors="BW")}
        parser_cls = MockParser

        def parse_advertisement(self, service_info):
            return None

        async def write_image(self, ble_device, preset, image, *, pacing_s=0.0):
            return MagicMock()

    mock_backend = MockTestBackend()
    esl_ble.register(mock_backend)

    assert esl_ble.get("mock_test") is mock_backend
    info = MagicMock()
    info.name = "Mock"
    info.manufacturer_data = {}
    info.service_uuids = ["mock_uuid"]
    assert esl_ble.detect(info) is mock_backend
