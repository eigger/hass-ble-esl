"""Passive coordinator updates from Bluetooth advertisements in real HA."""

from homeassistant.core import HomeAssistant

from tests.components.ble_esl.bt import inject_bluetooth_service_info
from tests.components.ble_esl.conftest import (
    IDENT,
    WOLINK_MFR_BYTES,
    device_of,
    wolink_service_info,
)


async def test_advertisement_updates_device_versions(hass: HomeAssistant, wolink_entry) -> None:
    """process_service_info mirrors new firmware/hardware versions onto the device."""
    newer = (
        bytes([0x12, 0x34, 0x03, 0x01, 0x05, 0x03]) + WOLINK_MFR_BYTES[6:]
    )  # app 0x0301, hw 0x0503
    inject_bluetooth_service_info(hass, wolink_service_info(mfr_bytes=newer))
    await hass.async_block_till_done()

    device = device_of(hass)
    assert device.sw_version == "769" and device.hw_version == "1283"
    assert wolink_entry.runtime_data.sw_version == "769"


async def test_low_battery_advertisement(hass: HomeAssistant, wolink_entry) -> None:
    low = WOLINK_MFR_BYTES[:8] + bytes([0x08, 0x98])  # 2200 mV
    inject_bluetooth_service_info(hass, wolink_service_info(mfr_bytes=low))
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.zhsunyco_{IDENT}_battery").state == "0"
    assert hass.states.get(f"binary_sensor.zhsunyco_{IDENT}_battery").state == "on"
