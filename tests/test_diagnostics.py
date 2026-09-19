"""Tests for the config-entry diagnostics download."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from unittest.mock import MagicMock

from conftest import ADDRESS, make_entry

from custom_components.ble_esl import diagnostics
from custom_components.ble_esl.esl_ble.wolink.const import MANUFACTURER_ID


def _advertisement():
    info = MagicMock()
    info.name = "WOLINK-0055"
    info.address = ADDRESS
    info.rssi = -61
    info.source = "hci0"
    info.connectable = True
    info.time = 1234.5
    # PID=0x1234, AppVer=258, HwVer=772, DispVer=0x0506, battery 3000 mV
    info.manufacturer_data = {
        MANUFACTURER_ID: bytes([0x12, 0x34, 0x02, 0x01, 0x04, 0x03, 0x06, 0x05, 0x0B, 0xB8])
    }
    info.service_uuids = []
    return info


def test_diagnostics_content_and_redaction(monkeypatch):
    async def _test():
        hass = MagicMock()
        entry = make_entry(
            model='2.9" BWRY 296x128', sw_version="258", hw_version="772", write_lock=True
        )
        entry.version = 1
        entry.unique_id = ADDRESS
        entry.data = {"protocol": "wolink", "model": "290"}
        entry.options = {"retry_count": 2}
        data = entry.runtime_data
        data.failure_coordinator.data = 3
        data.last_failure_coordinator.data = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
        data.last_image_data = b"png" * 10
        monkeypatch.setattr(
            diagnostics, "async_last_service_info", lambda *a, **k: _advertisement()
        )

        result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

        # JSON-serialisable, as HA will dump it.
        json.dumps(result)

        # The MAC never appears; the short identifier does.
        assert ADDRESS not in json.dumps(result)
        assert result["device"]["address"] == "**REDACTED**"
        assert result["entry"]["unique_id"] == "**REDACTED**"
        assert result["device"]["identifier"] == "54200055"

        assert result["backend"]["id"] == "wolink"
        assert result["backend"]["capabilities"]["passive_battery"] is True
        assert result["preset"]["key"] == "290"
        assert result["preset"]["extra"]["mirror"] is True
        assert result["entry"]["options"] == {"retry_count": 2}
        assert result["entry"]["effective_options"] == {
            "retry_count": 2,
            "write_delay_ms": 0,
            "prevent_duplicate_send": False,
            "debounce_ms": 0,
            "protocol": "wolink",
            "model": "290",
        }

        adv = result["advertisement"]
        assert adv["rssi"] == -61
        assert adv["manufacturer_data"] == {"0xBBAA": "12340201040306050bb8"}
        assert adv["parsed"]["battery_mv"] == 3000
        assert adv["parsed"]["sw_version"] == "258"

        assert result["write_state"] == {
            "write_lock": True,
            "in_progress": False,
            "debounce_pending": False,
            "write_generation": 0,
            "last_image_png_bytes": 30,
        }
        assert result["sensors"]["failure_count"] == 3
        assert result["sensors"]["last_failure"] == "2026-09-20T12:00:00+00:00"

    asyncio.run(_test())


def test_diagnostics_without_advertisement(monkeypatch):
    async def _test():
        entry = make_entry()
        entry.version, entry.unique_id, entry.data, entry.options = 1, ADDRESS, {}, {}
        monkeypatch.setattr(diagnostics, "async_last_service_info", lambda *a, **k: None)
        result = await diagnostics.async_get_config_entry_diagnostics(MagicMock(), entry)
        assert result["advertisement"] is None
        assert result["sensors"]["last_failure"] is None
        assert result["write_state"]["last_image_png_bytes"] is None
        json.dumps(result)

    asyncio.run(_test())


def test_diagnostics_masks_mac_in_name_and_source_and_survives_parse_errors(monkeypatch):
    async def _test():
        entry = make_entry()
        entry.version, entry.unique_id, entry.data, entry.options = 1, ADDRESS, {}, {}
        info = _advertisement()
        info.name = ADDRESS.replace(":", "")  # e.g. Poshiji advertises its MAC as the name
        info.source = f"proxy-{ADDRESS.lower()}"  # a proxy id may embed a MAC
        monkeypatch.setattr(diagnostics, "async_last_service_info", lambda *a, **k: info)
        monkeypatch.setattr(entry.runtime_data.backend, "parse_advertisement", lambda i: 1 / 0)

        result = await diagnostics.async_get_config_entry_diagnostics(MagicMock(), entry)

        dump = json.dumps(result)
        assert ADDRESS not in dump and ADDRESS.replace(":", "") not in dump
        assert result["advertisement"]["name"] == "**REDACTED**"
        assert result["advertisement"]["source"] == "proxy-**REDACTED**"
        assert result["advertisement"]["parsed"] == {"error": "ZeroDivisionError: division by zero"}
        assert result["advertisement"]["rssi"] == -61  # the rest of the download is intact

    asyncio.run(_test())
