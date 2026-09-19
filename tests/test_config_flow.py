"""Tests for BLE ESL config flow and options flow."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.config_flow import (
    BleEslConfigFlow,
    OptionsFlowHandler,
    _model_selector_options,
    _title,
)
from custom_components.ble_esl.const import (
    CONF_DEBOUNCE_MS,
    CONF_MODEL,
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_PROTOCOL,
    CONF_RETRY_COUNT,
    CONF_WRITE_DELAY_MS,
)
from custom_components.ble_esl.esl_ble.wolink.const import (
    MANUFACTURER_ID,
    SERVICE_UUID,
)
from custom_components.ble_esl.esl_ble.wolink.devices import PRESETS


def test_model_selector_options():
    """Verify options in model selector for UI."""
    options = _model_selector_options("wolink")
    assert len(options) == len(PRESETS)
    values = [opt["value"] for opt in options]
    assert "290" in values
    assert "750" in values


def test_title_helper():
    """Verify title generation for discovered device."""
    info = MagicMock()
    info.address = "66:66:54:20:00:55"
    backend = esl_ble.get("wolink")
    title = _title(info, backend, "290")
    assert title == 'Zhsunyco 54200055 (2.9" BWRY)'


def test_config_flow_bluetooth_step():
    """Verify bluetooth discovery flow to entry creation."""

    async def _test():
        flow = BleEslConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        # 1. Unsupported device
        unsupported_info = MagicMock()
        unsupported_info.address = "11:22:33:44:55:66"
        unsupported_info.manufacturer_data = {}
        unsupported_info.service_uuids = []
        flow.async_abort = MagicMock(return_value={"type": "abort", "reason": "not_supported"})

        result = await flow.async_step_bluetooth(unsupported_info)
        assert result["type"] == "abort"
        assert result["reason"] == "not_supported"

        # 2. Supported WOLINK device
        supported_info = MagicMock()
        supported_info.address = "66:66:54:20:00:55"
        supported_info.manufacturer_data = {MANUFACTURER_ID: b"\x00" * 10}
        supported_info.service_uuids = [SERVICE_UUID]

        flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})
        confirm_result = await flow.async_step_bluetooth(supported_info)
        assert confirm_result["type"] == "form"
        assert confirm_result["step_id"] == "bluetooth_confirm"

        # Confirm form submit -> goes to model step
        model_step_result = await flow.async_step_bluetooth_confirm(user_input={})
        assert model_step_result["type"] == "form"
        assert model_step_result["step_id"] == "model"

        # Submit model selection
        flow.async_create_entry = MagicMock(
            side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
        )
        entry_result = await flow.async_step_model(user_input={CONF_MODEL: "290"})
        assert entry_result["type"] == "create_entry"
        assert entry_result["data"][CONF_PROTOCOL] == "wolink"
        assert entry_result["data"][CONF_MODEL] == "290"
        assert "54200055" in entry_result["title"]

    asyncio.run(_test())


def test_options_flow():
    """Verify options flow allows updating model and write settings."""

    async def _test():
        config_entry = MagicMock()
        config_entry.data = {CONF_PROTOCOL: "wolink", CONF_MODEL: "290"}
        config_entry.options = {
            CONF_RETRY_COUNT: 5,
            CONF_WRITE_DELAY_MS: 50,
            CONF_PREVENT_DUPLICATE_SEND: True,
            CONF_DEBOUNCE_MS: 2000,
        }

        options_flow = OptionsFlowHandler()
        options_flow.config_entry = config_entry
        options_flow.async_create_entry = MagicMock(
            side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
        )

        user_input = {
            CONF_MODEL: "750",
            CONF_RETRY_COUNT: 4,
            CONF_WRITE_DELAY_MS: 10,
            CONF_PREVENT_DUPLICATE_SEND: False,
            CONF_DEBOUNCE_MS: 0,
        }
        result = await options_flow.async_step_init(user_input=user_input)
        assert result["type"] == "create_entry"
        assert result["data"][CONF_MODEL] == "750"
        assert result["data"][CONF_RETRY_COUNT] == 4

    asyncio.run(_test())


def test_build_options_schema_fallback(monkeypatch):
    """Verify options schema falls back to first available preset when DEFAULT_MODEL is missing."""
    import voluptuous as vol

    from custom_components.ble_esl.config_flow import _build_options_schema
    from custom_components.ble_esl.esl_ble.base import (
        BleBackend,
        BleParser,
        Capabilities,
        DevicePreset,
    )

    monkeypatch.setattr(esl_ble, "_BACKENDS", dict(esl_ble._BACKENDS))

    class MockParser(BleParser):
        brand = "Mock"
        fallback_name = "Mock"
        is_advertisement = staticmethod(lambda info: "mock_no_290" in info.service_uuids)

    class MockNo290Backend(BleBackend):
        id = "mock_no_290"
        label = "MOCK"
        name = "Mock No 290"
        capabilities = Capabilities(
            passive_battery=False,
            session_battery=False,
            session_temperature=False,
            model_detection=False,
            palettes=("BW",),
        )
        PRESETS = {
            "custom_1": DevicePreset(
                key="custom_1",
                display_name="Custom 1",
                width=100,
                height=100,
                colors="BW",
            )
        }
        parser_cls = MockParser

        def parse_advertisement(self, service_info):
            return None

        async def write_image(self, *args, **kwargs):
            return MagicMock()

    esl_ble.register(MockNo290Backend())
    _build_options_schema("mock_no_290")

    # Check vol.Required was called with default="custom_1"
    calls = [
        call
        for call in vol.Required.call_args_list
        if len(call.args) > 0 and call.args[0] == CONF_MODEL
    ]
    assert len(calls) > 0
    assert calls[-1].kwargs.get("default") == "custom_1"


def test_config_flow_auto_model_detection_skips_step():
    """Verify backend with model_detection=True skips model selection step in config flow."""

    async def _test():
        from custom_components.ble_esl.esl_ble.picksmart.const import MANUFACTURER_ID as PS_MFG_ID

        flow = BleEslConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})
        flow.async_create_entry = MagicMock(
            side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
        )

        # PickSmart 2.9" BWR advertisement: device_id 0x0033, 3.0V, FW 0x0101
        service_info = MagicMock()
        service_info.address = "AA:BB:CC:DD:EE:FF"
        service_info.service_uuids = []
        service_info.manufacturer_data = {PS_MFG_ID: bytes.fromhex("331e010100")}

        # Step 1: Bluetooth discovery
        confirm_result = await flow.async_step_bluetooth(service_info)
        assert confirm_result["type"] == "form"
        assert confirm_result["step_id"] == "bluetooth_confirm"
        assert flow._detected_model == "0x0033"

        # Step 2: Confirming skips async_step_model and directly creates entry
        entry_result = await flow.async_step_bluetooth_confirm(user_input={})
        assert entry_result["type"] == "create_entry"
        assert entry_result["data"][CONF_PROTOCOL] == "picksmart"
        assert entry_result["data"][CONF_MODEL] == "0x0033"

    asyncio.run(_test())


def test_options_flow_hides_model_for_model_detection_backend():
    """Verify options schema does not expose CONF_MODEL for backends with model_detection=True."""
    import voluptuous as vol

    from custom_components.ble_esl.config_flow import _build_options_schema

    vol.Required.reset_mock()
    _build_options_schema("picksmart")
    called_keys = [call.args[0] for call in vol.Required.call_args_list if len(call.args) > 0]
    assert CONF_MODEL not in called_keys
    assert CONF_RETRY_COUNT in called_keys
