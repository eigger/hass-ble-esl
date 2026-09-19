from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


# Base class mock supporting subscripting (e.g., BaseClass[T])
class MockBase:
    def __init__(self, *args, **kwargs):
        pass

    def __init_subclass__(cls, **kwargs):
        pass

    def __class_getitem__(cls, item):
        return cls


class MockEntity(MockBase):
    @property
    def unique_id(self) -> str | None:
        return getattr(self, "_attr_unique_id", None)

    @property
    def entity_category(self):
        return getattr(self, "_attr_entity_category", None)

    @property
    def device_class(self):
        return getattr(self, "_attr_device_class", None)


class MockCoordinatorEntity(MockEntity):
    def __init__(self, coordinator=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coordinator = coordinator

    def _handle_coordinator_update(self) -> None:
        pass


class MockConfigFlow(MockBase):
    def _set_confirm_only(self) -> None:
        pass


class MockSensorEntity(MockEntity):
    pass


class MockPassiveBluetoothProcessorEntity(MockEntity):
    pass


class MockBinarySensorEntity(MockEntity):
    pass


class MockImageEntity(MockEntity):
    pass


class MockSwitchEntity(MockEntity):
    pass


class MockRestoreText(MockEntity):
    pass


class MockRestoreEntity(MockEntity):
    """Distinct from MockEntity: RestoreEntity and SwitchEntity are siblings in HA."""


class MockModule(types.ModuleType):
    """A ModuleType that dynamically returns MagicMocks for unassigned attributes."""

    def __getattr__(self, name):
        val = MagicMock()
        setattr(self, name, val)
        return val


# ── Mock External Modules ─────────────────────────────────────────────────────

# Mock voluptuous
sys.modules["voluptuous"] = MagicMock()

# Mock propcache
propcache_mock = MagicMock()
propcache_mock.cached_property = property
sys.modules["propcache"] = propcache_mock
sys.modules["propcache.api"] = propcache_mock

# Mock sensor_state_data
sys.modules["sensor_state_data"] = MagicMock()


# Mock bluetooth_sensor_state_data
class MockBluetoothData:
    def __init__(self):
        self.title = None
        self._device_name = None
        self._device_type = None
        self._device_manufacturer = None
        self._device_sw_version = None
        self._device_hw_version = None
        self._sensor_values = {}
        self._binary_sensor_values = {}

    def supported(self, data) -> bool:
        self._start_update(data)
        return bool(self._device_type)

    def set_title(self, title: str) -> None:
        self.title = title

    def set_device_name(self, name: str) -> None:
        self._device_name = name

    def get_device_name(self) -> str | None:
        return self._device_name

    def set_device_type(self, type_: str) -> None:
        self._device_type = type_

    def set_device_manufacturer(self, manufacturer: str) -> None:
        self._device_manufacturer = manufacturer

    def set_device_sw_version(self, version: str) -> None:
        self._device_sw_version = version

    def set_device_hw_version(self, version: str) -> None:
        self._device_hw_version = version

    def update_predefined_sensor(self, desc, val) -> None:
        self._sensor_values[desc] = val

    def update_predefined_binary_sensor(self, desc, val) -> None:
        self._binary_sensor_values[desc] = val

    def update(self, service_info):
        self._start_update(service_info)
        return MagicMock()


bt_sensor_state_data = MagicMock()
bt_sensor_state_data.BluetoothData = MockBluetoothData
sys.modules["bluetooth_sensor_state_data"] = bt_sensor_state_data

# Mock home_assistant_bluetooth
sys.modules["home_assistant_bluetooth"] = MagicMock()

# Mock bleak
sys.modules["bleak"] = MagicMock()
sys.modules["bleak.backends.device"] = MagicMock()
sys.modules["bleak_retry_connector"] = MagicMock()


# ── Mock Home Assistant Modules ────────────────────────────────────────────────

ha = MockModule("homeassistant")
sys.modules["homeassistant"] = ha

ha_components = MockModule("homeassistant.components")
sys.modules["homeassistant.components"] = ha_components
ha.components = ha_components


# Mock homeassistant.exceptions
class MockHomeAssistantError(Exception):
    """Mock HomeAssistantError."""


ha_exceptions = MockModule("homeassistant.exceptions")
ha_exceptions.HomeAssistantError = MockHomeAssistantError
sys.modules["homeassistant.exceptions"] = ha_exceptions
ha.exceptions = ha_exceptions

# Setup bluetooth passive update processor mocks
ha_bt = MockModule("homeassistant.components.bluetooth")
ha_bt_processor = MockModule("homeassistant.components.bluetooth.passive_update_processor")


class MockPassiveBluetoothDataProcessor(MockBase):
    def async_add_entities_listener(self, *args, **kwargs):
        return MagicMock()


ha_bt_processor.PassiveBluetoothProcessorCoordinator = MockBase
ha_bt_processor.PassiveBluetoothDataProcessor = MockPassiveBluetoothDataProcessor
ha_bt_processor.PassiveBluetoothProcessorEntity = MockPassiveBluetoothProcessorEntity
sys.modules["homeassistant.components.bluetooth"] = ha_bt
sys.modules["homeassistant.components.bluetooth.passive_update_processor"] = ha_bt_processor
ha_components.bluetooth = ha_bt

# Mock other components
ha_recorder = MockModule("homeassistant.components.recorder")
ha_recorder_history = MockModule("homeassistant.components.recorder.history")
sys.modules["homeassistant.components.recorder"] = ha_recorder
sys.modules["homeassistant.components.recorder.history"] = ha_recorder_history
ha_components.recorder = ha_recorder

ha_diagnostics = MockModule("homeassistant.components.diagnostics")


def _mock_redact(data, to_redact):
    """Mirror HA's async_redact_data: recursively replace listed keys' values."""
    if isinstance(data, dict):
        return {
            k: "**REDACTED**" if k in to_redact else _mock_redact(v, to_redact)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_mock_redact(v, to_redact) for v in data]
    return data


ha_diagnostics.async_redact_data = _mock_redact
sys.modules["homeassistant.components.diagnostics"] = ha_diagnostics
ha_components.diagnostics = ha_diagnostics

ha_onboarding = MockModule("homeassistant.components.onboarding")
sys.modules["homeassistant.components.onboarding"] = ha_onboarding
ha_components.onboarding = ha_onboarding

ha_sensor = MockModule("homeassistant.components.sensor")
ha_sensor.SensorEntity = MockSensorEntity
ha_sensor.SensorEntityDescription = MockBase
sys.modules["homeassistant.components.sensor"] = ha_sensor
ha_components.sensor = ha_sensor

ha_binary_sensor = MockModule("homeassistant.components.binary_sensor")
ha_binary_sensor.BinarySensorEntity = MockBinarySensorEntity
sys.modules["homeassistant.components.binary_sensor"] = ha_binary_sensor
ha_components.binary_sensor = ha_binary_sensor

ha_image = MockModule("homeassistant.components.image")
ha_image.ImageEntity = MockImageEntity
ha_image.Image = MockBase
sys.modules["homeassistant.components.image"] = ha_image
ha_components.image = ha_image

ha_switch = MockModule("homeassistant.components.switch")
ha_switch.SwitchEntity = MockSwitchEntity
sys.modules["homeassistant.components.switch"] = ha_switch
ha_components.switch = ha_switch

ha_text = MockModule("homeassistant.components.text")
ha_text.RestoreText = MockRestoreText
sys.modules["homeassistant.components.text"] = ha_text
ha_components.text = ha_text

# Mock config entries
ha_config_entries = MockModule("homeassistant.config_entries")
ha_config_entries.ConfigFlow = MockConfigFlow
ha_config_entries.ConfigFlowResult = dict
ha_config_entries.OptionsFlowWithReload = MockBase
sys.modules["homeassistant.config_entries"] = ha_config_entries
ha.config_entries = ha_config_entries

ha_const = MockModule("homeassistant.const")
sys.modules["homeassistant.const"] = ha_const
ha.const = ha_const

ha_core = MockModule("homeassistant.core")
ha_core.callback = lambda f: f
sys.modules["homeassistant.core"] = ha_core
ha.core = ha_core

ha_helpers = MockModule("homeassistant.helpers")
sys.modules["homeassistant.helpers"] = ha_helpers
ha.helpers = ha_helpers

ha_dr = MockModule("homeassistant.helpers.device_registry")
ha_dr.DeviceInfo = dict
ha_dr.CONNECTION_BLUETOOTH = "bluetooth"
sys.modules["homeassistant.helpers.device_registry"] = ha_dr
ha_helpers.device_registry = ha_dr

ha_update_coordinator = MockModule("homeassistant.helpers.update_coordinator")
ha_update_coordinator.CoordinatorEntity = MockCoordinatorEntity
ha_update_coordinator.DataUpdateCoordinator = MockBase
sys.modules["homeassistant.helpers.update_coordinator"] = ha_update_coordinator
ha_helpers.update_coordinator = ha_update_coordinator

ha_helpers_service = MockModule("homeassistant.helpers.service")
sys.modules["homeassistant.helpers.service"] = ha_helpers_service
ha_helpers.service = ha_helpers_service

ha_helpers_event = MockModule("homeassistant.helpers.event")
sys.modules["homeassistant.helpers.event"] = ha_helpers_event
ha_helpers.event = ha_helpers_event

ha_helpers_selector = MockModule("homeassistant.helpers.selector")
ha_helpers_selector.SelectOptionDict = dict
sys.modules["homeassistant.helpers.selector"] = ha_helpers_selector
ha_helpers.selector = ha_helpers_selector

ha_helpers_entity = MockModule("homeassistant.helpers.entity")
ha_helpers_entity.EntityCategory = ha_const.EntityCategory
sys.modules["homeassistant.helpers.entity"] = ha_helpers_entity
ha_helpers.entity = ha_helpers_entity

ha_helpers_entity_platform = MockModule("homeassistant.helpers.entity_platform")
sys.modules["homeassistant.helpers.entity_platform"] = ha_helpers_entity_platform
ha_helpers.entity_platform = ha_helpers_entity_platform

ha_helpers_sensor = MockModule("homeassistant.helpers.sensor")
sys.modules["homeassistant.helpers.sensor"] = ha_helpers_sensor
ha_helpers.sensor = ha_helpers_sensor

ha_restore = MockModule("homeassistant.helpers.restore_state")
ha_restore.RestoreEntity = MockRestoreEntity
sys.modules["homeassistant.helpers.restore_state"] = ha_restore
ha_helpers.restore_state = ha_restore

ha_util = MockModule("homeassistant.util")
ha_util_dt = MockModule("homeassistant.util.dt")
sys.modules["homeassistant.util"] = ha_util
sys.modules["homeassistant.util.dt"] = ha_util_dt
ha.util = ha_util
ha.util.dt = ha_util_dt

ha_util_hass_dict = MockModule("homeassistant.util.hass_dict")
ha_util_hass_dict.HassKey = str  # a HassKey is just a hashable key
sys.modules["homeassistant.util.hass_dict"] = ha_util_hass_dict
ha_util.hass_dict = ha_util_hass_dict

ha_helpers_cv = MockModule("homeassistant.helpers.config_validation")
sys.modules["homeassistant.helpers.config_validation"] = ha_helpers_cv
ha_helpers.config_validation = ha_helpers_cv

ha_helpers_typing = MockModule("homeassistant.helpers.typing")
sys.modules["homeassistant.helpers.typing"] = ha_helpers_typing
ha_helpers.typing = ha_helpers_typing


# ── Test helpers ──────────────────────────────────────────────────────────────

ADDRESS = "66:66:54:20:00:55"


def make_runtime_data(**overrides):
    """A BleEslRuntimeData with MagicMock coordinators and the WOLINK 2.9" preset.

    Imported lazily so the HA mocks above are in place first.
    """
    from custom_components.ble_esl.data import BleEslRuntimeData
    from custom_components.ble_esl.esl_ble.wolink import WolinkBleBackend

    backend = overrides.pop("backend", None) or WolinkBleBackend()
    preset = overrides.pop("preset", None) or backend.presets()["290"]
    fields = dict(
        address=ADDRESS,
        backend=backend,
        preset=preset,
        parser=MagicMock(),
        device_id="mock_device_id",
        manufacturer="Zhsunyco",
        model=None,
        sw_version=None,
        hw_version=None,
        bt_coordinator=MagicMock(),
        image_coordinator=MagicMock(data=None),
        preview_coordinator=MagicMock(data=None),
        connectivity_coordinator=MagicMock(data=False),
        duration_coordinator=MagicMock(data=0.0),
        failure_coordinator=MagicMock(data=0),
        last_failure_coordinator=MagicMock(data=None),
        battery_coordinator=MagicMock(data=None),
        temperature_coordinator=MagicMock(data=None),
    )
    fields.update(overrides)
    return BleEslRuntimeData(**fields)


def make_entry(entry_id="test_entry", **runtime_overrides):
    """A MagicMock config entry carrying runtime data."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.runtime_data = make_runtime_data(**runtime_overrides)
    return entry
