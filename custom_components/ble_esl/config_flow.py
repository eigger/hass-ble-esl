"""Config flow for the BLE ESL integration."""

from __future__ import annotations

import dataclasses
from typing import Any

from homeassistant.components import onboarding
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
    async_last_service_info,
)
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from . import esl_ble
from .const import (
    CONF_DEBOUNCE_MS,
    CONF_MODEL,
    CONF_PREVENT_DUPLICATE_SEND,
    CONF_PROTOCOL,
    CONF_RETRY_COUNT,
    DEFAULT_DEBOUNCE_MS,
    DEFAULT_MODEL,
    DEFAULT_PREVENT_DUPLICATE_SEND,
    DEFAULT_PROTOCOL,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
)
from .esl_ble import (
    CONFIDENCE_COMMUNITY,
    CONFIDENCE_ESTIMATED,
    CONFIDENCE_HARDWARE,
    CONFIDENCE_REPORTED,
    BleBackend,
    DevicePreset,
)


def _model_selector_options(
    protocol_id: str = DEFAULT_PROTOCOL,
) -> list[SelectOptionDict]:
    """Generate model selector options sorted with verified models first."""
    backend = esl_ble.get(protocol_id)
    presets = backend.presets()

    def sort_key(item: tuple[str, DevicePreset]) -> tuple[int, int]:
        _, preset = item
        order = {
            CONFIDENCE_HARDWARE: 0,
            CONFIDENCE_REPORTED: 1,
            CONFIDENCE_COMMUNITY: 2,
            CONFIDENCE_ESTIMATED: 3,
        }
        return (order.get(preset.confidence, 4), preset.width * preset.height)

    out = []
    for key, preset in sorted(presets.items(), key=sort_key):
        label = f"{preset.display_name} — {preset.width}x{preset.height}"
        if not preset.verified:
            label += " (unverified)"
        out.append(SelectOptionDict(value=key, label=label))
    return out


def advertised_model_key(
    backend: BleBackend, service_info: BluetoothServiceInfoBleak | None
) -> str | None:
    """Catalog model the advertisement names, or None when it does not."""
    if service_info is None or not backend.capabilities.model_detection:
        return None
    info = backend.parse_advertisement(service_info)
    if info is None or not info.model_key or info.model_key not in backend.presets():
        return None
    return info.model_key


def _model_fixed(hass: HomeAssistant, address: str | None, protocol_id: str) -> bool:
    """Hide the options model field when the advertisement names the model.

    No cached advertisement is not the same as an advertisement that leaves
    the model open: a sleeping tag must not grow a picker the next advertisement
    would overrule.
    """
    backend = esl_ble.get(protocol_id)
    if not backend.capabilities.model_detection or address is None:
        return False
    service_info = async_last_service_info(hass, address, connectable=True)
    if service_info is None:
        return True
    return advertised_model_key(backend, service_info) is not None


def _build_options_schema(
    protocol_id: str = DEFAULT_PROTOCOL, *, model_identified: bool = False
) -> dict[Any, Any]:
    backend = esl_ble.get(protocol_id)
    default_model = backend.preset_for(DEFAULT_MODEL).key

    schema: dict[Any, Any] = {}

    if not model_identified:
        schema[vol.Required(CONF_MODEL, default=default_model)] = SelectSelector(
            SelectSelectorConfig(
                options=_model_selector_options(protocol_id),
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

    schema.update(
        {
            vol.Required(CONF_RETRY_COUNT, default=DEFAULT_RETRY_COUNT): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=10,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_PREVENT_DUPLICATE_SEND,
                default=DEFAULT_PREVENT_DUPLICATE_SEND,
            ): bool,
            vol.Required(CONF_DEBOUNCE_MS, default=DEFAULT_DEBOUNCE_MS): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=120000,
                    step=1000,
                    mode=NumberSelectorMode.SLIDER,
                    unit_of_measurement="ms",
                )
            ),
        }
    )
    return schema


@dataclasses.dataclass
class Discovery:
    """A discovered bluetooth device."""

    title: str
    discovery_info: BluetoothServiceInfoBleak
    backend: BleBackend


def _title(
    discovery_info: BluetoothServiceInfoBleak,
    backend: BleBackend,
    model_key: str | None = None,
) -> str:
    identifier = discovery_info.address.replace(":", "")[-8:]
    preset = backend.presets().get(model_key) if model_key else None
    model_str = preset.display_name if preset else backend.name
    return f"{backend.brand} {identifier} ({model_str})"


class BleEslConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE ESL."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._backend: BleBackend | None = None
        self._protocol_id: str = DEFAULT_PROTOCOL
        self._discovered_devices: dict[str, Discovery] = {}
        self._detected_model: str | None = None

    def _create_entry(self, model_key: str) -> ConfigFlowResult:
        """Create entry with determined model key."""
        backend = self._backend or esl_ble.get(self._protocol_id)
        if self._discovery_info:
            title = _title(self._discovery_info, backend, model_key)
        else:
            title = self.context.get("title_placeholders", {}).get("name", "BLE ESL")

        return self.async_create_entry(
            title=title,
            data={
                CONF_PROTOCOL: backend.id,
                CONF_MODEL: model_key,
            },
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        backend = esl_ble.detect(discovery_info)
        if backend is None:
            return self.async_abort(reason="not_supported")

        self._backend = backend
        self._protocol_id = backend.id
        self._detected_model = advertised_model_key(backend, discovery_info)

        title = _title(discovery_info, backend, self._detected_model)
        self.context["title_placeholders"] = {"name": title}
        self._discovery_info = discovery_info

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            if self._detected_model:
                return self._create_entry(self._detected_model)
            return await self.async_step_model()

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            discovery = self._discovered_devices[address]

            self.context["title_placeholders"] = {"name": discovery.title}
            self._discovery_info = discovery.discovery_info
            self._backend = discovery.backend
            self._protocol_id = discovery.backend.id

            self._detected_model = advertised_model_key(discovery.backend, discovery.discovery_info)
            if self._detected_model:
                return self._create_entry(self._detected_model)

            return await self.async_step_model()

        current_addresses = self._async_current_ids(include_ignore=False)
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            backend = esl_ble.detect(discovery_info)
            if backend is not None:
                self._discovered_devices[address] = Discovery(
                    title=_title(discovery_info, backend),
                    discovery_info=discovery_info,
                    backend=backend,
                )

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        titles = {
            address: discovery.title for (address, discovery) in self._discovered_devices.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(titles)}),
        )

    async def async_step_model(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle model selection step."""
        backend = self._backend or esl_ble.get(self._protocol_id)

        if user_input is not None:
            model_key = user_input[CONF_MODEL]
            return self._create_entry(model_key)

        selector = SelectSelector(
            SelectSelectorConfig(
                options=_model_selector_options(backend.id),
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
        if backend.capabilities.model_detection and not self._detected_model:
            # The tag's type is unknown; no size is a better guess than another.
            field = vol.Required(CONF_MODEL)
        else:
            default_model = backend.preset_for(self._detected_model or DEFAULT_MODEL).key
            field = vol.Required(CONF_MODEL, default=default_model)
        schema = vol.Schema({field: selector})

        return self.async_show_form(
            step_id="model",
            data_schema=schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlowWithReload):
    """Handle options flow for BLE ESL."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            if CONF_MODEL not in user_input and CONF_MODEL in self.config_entry.options:
                # The field was hidden; saving must not drop an earlier pick.
                user_input = {**user_input, CONF_MODEL: self.config_entry.options[CONF_MODEL]}
            return self.async_create_entry(title="", data=user_input)

        suggested_values = {
            **self.config_entry.data,
            **self.config_entry.options,
        }
        protocol_id = suggested_values.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
        model_identified = _model_fixed(self.hass, self.config_entry.unique_id, protocol_id)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(_build_options_schema(protocol_id, model_identified=model_identified)),
                suggested_values,
            ),
        )
