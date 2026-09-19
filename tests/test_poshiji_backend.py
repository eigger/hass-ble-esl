"""PSJ-420 discovery, config persistence and session integration tests."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from bluetooth import device_of, sensor_values, service_info
import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble import base
from custom_components.ble_esl.esl_ble.base import CONFIDENCE_REPORTED
from custom_components.ble_esl.esl_ble.poshiji import writer
from custom_components.ble_esl.esl_ble.poshiji.devices import PSJ_420


def advertisement(tail=0x1B, payload=None):
    return service_info(
        "AA:BB:CC:DD:EE:FF",
        name="FFEEDDCCBBAA",
        manufacturer_data={
            0x5258: payload
            if payload is not None
            else bytes.fromhex("fd024002009964060102ffff") + bytes([tail])
        },
    )


def test_discovery_profile_and_no_invented_sensors():
    backend = esl_ble.get("poshiji")
    assert backend.brand == "Poshiji"
    assert PSJ_420.confidence == CONFIDENCE_REPORTED
    assert PSJ_420.verified
    for tail in (0x1E, 0x1B):
        info = advertisement(tail)
        assert [b.id for b in esl_ble.all_backends() if b.supported(info)] == ["poshiji"]
        assert esl_ble.detect(info) is backend
        adv = backend.parse_advertisement(info)
        assert adv.model_key == "psj-420" and adv.battery_mv is None
        parser = backend.create_parser(PSJ_420)
        update = parser.update(info)
        device = device_of(update)
        assert device.manufacturer == "Poshiji"
        assert "PSJ-420" in device.model
        assert {k for k in sensor_values(update)} <= {"signal_strength"}  # nothing invented
        assert not backend.capabilities.session_battery
        assert not backend.capabilities.passive_battery
    unknown = advertisement(payload=b"\x00" * 13)
    assert backend.parse_advertisement(unknown) is None
    assert not backend.supported(unknown)


@pytest.mark.parametrize("error", [None, ValueError("bad response"), TimeoutError()])
def test_session_result_and_disconnect(monkeypatch, error):
    client = SimpleNamespace(is_connected=True, disconnect=AsyncMock())
    monkeypatch.setattr(base, "establish_connection", AsyncMock(return_value=client))
    transport = SimpleNamespace(write_object=AsyncMock(return_value=True, side_effect=error))
    factory = MagicMock(return_value=transport)
    monkeypatch.setattr(writer, "XteClient", factory)
    image, encoded = object(), b"XTEK-encoded"
    prepare = MagicMock(return_value=encoded)
    monkeypatch.setattr(esl_ble.get("poshiji"), "prepare_image", prepare)
    result = asyncio.run(
        esl_ble.get("poshiji").write_image(
            advertisement(),
            PSJ_420,
            image,
            attempt=2,
            write_delay_ms=30,
        )
    )
    # Encoded before connecting, in a worker thread, then handed to the session.
    prepare.assert_called_once_with(PSJ_420, image, advertisement().address)
    factory.assert_called_once_with(client, 2, 30)
    transport.write_object.assert_awaited_once_with(encoded)
    client.disconnect.assert_awaited_once()
    assert result.success is (error is None)
    assert result.battery_mv is None
    if error is not None:
        assert result.error == (str(error) or type(error).__name__)


def test_connection_failure_is_reported(monkeypatch):
    monkeypatch.setattr(base, "establish_connection", AsyncMock(side_effect=OSError("unavailable")))
    monkeypatch.setattr(esl_ble.get("poshiji"), "prepare_image", MagicMock(return_value=b""))
    result = asyncio.run(esl_ble.get("poshiji").write_image(advertisement(), PSJ_420, object()))
    assert not result.success and result.error == "unavailable"
