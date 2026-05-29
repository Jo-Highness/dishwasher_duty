"""Config and options flow for Dishwasher Duty."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ALLOW_CO_CLAIM,
    CONF_CO_CLAIM_WINDOW,
    CONF_DEBOUNCE,
    CONF_FINISHED_VALUE,
    CONF_PERSONS,
    CONF_RUNNING_VALUE,
    CONF_SOURCE_SENSOR,
    DEFAULT_ALLOW_CO_CLAIM,
    DEFAULT_CO_CLAIM_WINDOW,
    DEFAULT_DEBOUNCE,
    DEFAULT_FINISHED_VALUE,
    DEFAULT_RUNNING_VALUE,
    DOMAIN,
)

TITLE = "Dishwasher Duty"


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_SENSOR,
                description={"suggested_value": defaults.get(CONF_SOURCE_SENSOR)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(
                CONF_FINISHED_VALUE,
                default=defaults.get(CONF_FINISHED_VALUE, DEFAULT_FINISHED_VALUE),
            ): selector.TextSelector(),
            vol.Required(
                CONF_RUNNING_VALUE,
                default=defaults.get(CONF_RUNNING_VALUE, DEFAULT_RUNNING_VALUE),
            ): selector.TextSelector(),
            vol.Required(
                CONF_PERSONS, default=defaults.get(CONF_PERSONS, [])
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="person", multiple=True)
            ),
            vol.Required(
                CONF_ALLOW_CO_CLAIM,
                default=defaults.get(CONF_ALLOW_CO_CLAIM, DEFAULT_ALLOW_CO_CLAIM),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_CO_CLAIM_WINDOW,
                default=defaults.get(CONF_CO_CLAIM_WINDOW, DEFAULT_CO_CLAIM_WINDOW),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5, max=600, step=5, mode="box", unit_of_measurement="s"
                )
            ),
            vol.Required(
                CONF_DEBOUNCE,
                default=defaults.get(CONF_DEBOUNCE, DEFAULT_DEBOUNCE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=120, step=1, mode="box", unit_of_measurement="s"
                )
            ),
        }
    )


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not user_input.get(CONF_PERSONS):
        errors["base"] = "no_persons"
    if not str(user_input.get(CONF_FINISHED_VALUE, "")).strip():
        errors["base"] = "no_finished_value"
    return errors


class DishwasherDutyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                user_input[CONF_CO_CLAIM_WINDOW] = int(user_input[CONF_CO_CLAIM_WINDOW])
                user_input[CONF_DEBOUNCE] = int(user_input[CONF_DEBOUNCE])
                return self.async_create_entry(title=TITLE, data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> DishwasherDutyOptionsFlow:
        return DishwasherDutyOptionsFlow(entry)


class DishwasherDutyOptionsFlow(OptionsFlow):
    """Edit every setting after setup."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                user_input[CONF_CO_CLAIM_WINDOW] = int(user_input[CONF_CO_CLAIM_WINDOW])
                user_input[CONF_DEBOUNCE] = int(user_input[CONF_DEBOUNCE])
                return self.async_create_entry(title="", data=user_input)
        defaults = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )
