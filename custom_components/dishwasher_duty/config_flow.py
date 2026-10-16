"""Config and options flow for Dishwasher Duty.

Both flows have two steps: first the source sensor, then the state values
(offered from the sensor's ``options`` attribute), persons and co-claim
settings.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import voluptuous as vol

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
    DEFAULT_TITLE,
    DOMAIN,
)

SETTINGS_KEYS = (
    CONF_FINISHED_VALUE,
    CONF_RUNNING_VALUE,
    CONF_PERSONS,
    CONF_ALLOW_CO_CLAIM,
    CONF_CO_CLAIM_WINDOW,
    CONF_DEBOUNCE,
)


def _source_schema(default: str | None) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_SENSOR, description={"suggested_value": default}
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        }
    )


def _state_options(hass: HomeAssistant, source: str, *extra: str) -> list[str]:
    """Possible states of the source sensor (ENUM ``options`` attribute)."""
    values: list[str] = []
    state = hass.states.get(source)
    if state is not None:
        raw = state.attributes.get("options")
        if isinstance(raw, list | tuple):
            values.extend(str(v) for v in raw)
    for value in extra:
        if value and value.casefold() not in {v.casefold() for v in values}:
            values.append(value)
    return values


def _pick(options: list[str], wanted: str) -> str:
    """Return the sensor's own spelling of ``wanted`` if it offers one."""
    for option in options:
        if option.casefold() == wanted.casefold():
            return option
    return wanted


def _settings_schema(hass: HomeAssistant, source: str, defaults: dict[str, Any]) -> vol.Schema:
    finished = defaults.get(CONF_FINISHED_VALUE, DEFAULT_FINISHED_VALUE)
    running = defaults.get(CONF_RUNNING_VALUE, DEFAULT_RUNNING_VALUE)
    options = _state_options(hass, source, finished, running)
    state_selector = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )
    return vol.Schema(
        {
            vol.Required(CONF_RUNNING_VALUE, default=_pick(options, running)): state_selector,
            vol.Required(CONF_FINISHED_VALUE, default=_pick(options, finished)): state_selector,
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


def _validate_settings(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    finished = str(user_input.get(CONF_FINISHED_VALUE, "")).strip()
    running = str(user_input.get(CONF_RUNNING_VALUE, "")).strip()
    if not user_input.get(CONF_PERSONS):
        errors["base"] = "no_persons"
    if not finished:
        errors[CONF_FINISHED_VALUE] = "no_finished_value"
    if not running:
        errors[CONF_RUNNING_VALUE] = "no_running_value"
    elif finished and finished.casefold() == running.casefold():
        errors[CONF_FINISHED_VALUE] = "same_values"
    return errors


def _clean_settings(user_input: dict[str, Any]) -> dict[str, Any]:
    """Build the stored settings from the submitted form only."""
    return {
        CONF_FINISHED_VALUE: str(user_input[CONF_FINISHED_VALUE]).strip(),
        CONF_RUNNING_VALUE: str(user_input[CONF_RUNNING_VALUE]).strip(),
        CONF_PERSONS: list(user_input[CONF_PERSONS]),
        CONF_ALLOW_CO_CLAIM: bool(user_input[CONF_ALLOW_CO_CLAIM]),
        CONF_CO_CLAIM_WINDOW: int(user_input[CONF_CO_CLAIM_WINDOW]),
        CONF_DEBOUNCE: int(user_input[CONF_DEBOUNCE]),
    }


def _sensor_in_use(hass: HomeAssistant, source: str, exclude_entry_id: str | None) -> bool:
    """True if another entry already tracks this source sensor."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == exclude_entry_id:
            continue
        if (
            entry.unique_id == source
            or {**entry.data, **entry.options}.get(CONF_SOURCE_SENSOR) == source
        ):
            return True
    return False


def _title_for(hass: HomeAssistant, source: str) -> str:
    """First dishwasher: "Dishwasher Duty"; more: "Dishwasher Duty (<sensor>)"."""
    if not hass.config_entries.async_entries(DOMAIN):
        return DEFAULT_TITLE
    state = hass.states.get(source)
    return f"{DEFAULT_TITLE} ({state.name if state else source})"


class DishwasherDutyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial configuration."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        self._source: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: pick the source sensor."""
        if user_input is not None:
            source = user_input[CONF_SOURCE_SENSOR]
            await self.async_set_unique_id(source)
            self._abort_if_unique_id_configured()
            if _sensor_in_use(self.hass, source, None):
                return self.async_abort(reason="already_configured")
            self._source = source
            return await self.async_step_settings()
        return self.async_show_form(step_id="user", data_schema=_source_schema(None))

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: state values, persons and co-claim behaviour."""
        assert self._source is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_settings(user_input)
            if not errors:
                return self.async_create_entry(
                    title=_title_for(self.hass, self._source),
                    data={CONF_SOURCE_SENSOR: self._source, **_clean_settings(user_input)},
                )
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(self.hass, self._source, user_input or {}),
            errors=errors,
            description_placeholders={"sensor": self._source},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> DishwasherDutyOptionsFlow:
        return DishwasherDutyOptionsFlow()


class DishwasherDutyOptionsFlow(OptionsFlow):
    """Edit every setting after setup."""

    def __init__(self) -> None:
        self._source: str | None = None

    @property
    def _current(self) -> dict[str, Any]:
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: source sensor."""
        errors: dict[str, str] = {}
        if user_input is not None:
            source = user_input[CONF_SOURCE_SENSOR]
            if _sensor_in_use(self.hass, source, self.config_entry.entry_id):
                errors[CONF_SOURCE_SENSOR] = "already_configured"
            else:
                self._source = source
                return await self.async_step_settings()
        return self.async_show_form(
            step_id="init",
            data_schema=_source_schema(self._current.get(CONF_SOURCE_SENSOR)),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: everything else."""
        assert self._source is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_settings(user_input)
            if not errors:
                if self.config_entry.unique_id != self._source:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, unique_id=self._source
                    )
                return self.async_create_entry(
                    data={CONF_SOURCE_SENSOR: self._source, **_clean_settings(user_input)}
                )
        defaults = user_input or {k: self._current[k] for k in SETTINGS_KEYS if k in self._current}
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(self.hass, self._source, defaults),
            errors=errors,
            description_placeholders={"sensor": self._source},
        )
