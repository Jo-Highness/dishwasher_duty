"""Config- and options-flow tests for Dishwasher Duty."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dishwasher_duty.const import (
    CONF_CO_CLAIM_WINDOW,
    CONF_FINISHED_VALUE,
    CONF_PERSONS,
    CONF_RUNNING_VALUE,
    CONF_SOURCE_SENSOR,
    DOMAIN,
)

from .conftest import PERSONS, SENSOR, build_data

HOME_CONNECT_OPTIONS = [
    "inactive",
    "ready",
    "delayedstart",
    "run",
    "pause",
    "actionrequired",
    "finished",
    "error",
    "aborting",
]


def _settings(**overrides: Any) -> dict[str, Any]:
    data = build_data(**overrides)
    data.pop(CONF_SOURCE_SENSOR)
    return data


def _defaults(result) -> dict[str, Any]:
    """Map field name -> default of a shown form."""
    out = {}
    for key in result["data_schema"].schema:
        default = key.default() if callable(key.default) else None
        out[str(key)] = default
    return out


def _select_options(result, field: str) -> list[str]:
    for key, value in result["data_schema"].schema.items():
        if str(key) == field:
            return list(value.config["options"])
    raise AssertionError(field)


async def _start(hass, sensor: str = SENSOR):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SOURCE_SENSOR: sensor}
    )


async def test_flow_happy_path(hass) -> None:
    """Sensor step, then settings step, creates the entry with a unique_id."""
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "settings"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], _settings())
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Dishwasher Duty"
    assert result["data"][CONF_SOURCE_SENSOR] == SENSOR
    assert result["data"][CONF_PERSONS] == PERSONS
    assert result["result"].unique_id == SENSOR


async def test_state_values_offered_from_sensor_options(hass) -> None:
    """The select offers the sensor's ENUM options and pre-selects run/finished."""
    hass.states.async_set(SENSOR, "ready", {"options": HOME_CONNECT_OPTIONS})
    result = await _start(hass)

    options = _select_options(result, CONF_FINISHED_VALUE)
    assert options == HOME_CONNECT_OPTIONS
    defaults = _defaults(result)
    assert defaults[CONF_FINISHED_VALUE] == "finished"
    assert defaults[CONF_RUNNING_VALUE] == "run"


async def test_state_values_use_sensor_spelling(hass) -> None:
    """If the sensor uses another case, its own spelling is pre-selected."""
    hass.states.async_set(SENSOR, "Ready", {"options": ["Ready", "Run", "Finished"]})
    result = await _start(hass)
    defaults = _defaults(result)
    assert defaults[CONF_FINISHED_VALUE] == "Finished"
    assert defaults[CONF_RUNNING_VALUE] == "Run"


async def test_custom_state_value_allowed(hass) -> None:
    """Values that are not in the sensor's options can be entered."""
    hass.states.async_set(SENSOR, "idle", {"options": ["idle", "washing", "done"]})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _settings(running_value="washing", finished_value="Clean")
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_FINISHED_VALUE] == "Clean"


async def test_flow_requires_persons(hass) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _settings(persons=[])
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_persons"}


async def test_flow_rejects_identical_values(hass) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _settings(running_value="Run", finished_value="run")
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_FINISHED_VALUE: "same_values"}


async def test_flow_rejects_blank_values(hass) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _settings(running_value=" ", finished_value=" ")
    )
    assert result["errors"] == {
        CONF_FINISHED_VALUE: "no_finished_value",
        CONF_RUNNING_VALUE: "no_running_value",
    }


async def test_duplicate_sensor_aborts(hass) -> None:
    MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR).add_to_hass(hass)
    result = await _start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_duplicate_sensor_of_legacy_entry_aborts(hass) -> None:
    """Entries from 1.0.x without unique_id are detected through their data."""
    MockConfigEntry(domain=DOMAIN, data=build_data()).add_to_hass(hass)
    result = await _start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_second_dishwasher_gets_own_title(hass) -> None:
    MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR).add_to_hass(hass)
    other = "sensor.kitchen_dishwasher_operation_state"
    hass.states.async_set(other, "ready", {"friendly_name": "Kitchen dishwasher"})
    result = await _start(hass, other)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _settings())
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Dishwasher Duty (Kitchen dishwasher)"
    assert result["result"].unique_id == other


async def _options(hass, entry, sensor: str = SENSOR):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SOURCE_SENSOR: sensor}
    )


async def test_options_flow_update_window(hass) -> None:
    """The co-claim window can be changed through the options flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR)
    entry.add_to_hass(hass)
    result = await _options(hass, entry)
    assert result["step_id"] == "settings"
    # Current values are pre-filled.
    assert _defaults(result)[CONF_FINISHED_VALUE] == "Finished"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _settings(co_claim_window=120)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_CO_CLAIM_WINDOW] == 120
    assert entry.options[CONF_SOURCE_SENSOR] == SENSOR


async def test_options_flow_change_sensor_updates_unique_id(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR)
    entry.add_to_hass(hass)
    new = "sensor.new_dishwasher_operation_state"
    result = await _options(hass, entry, new)
    result = await hass.config_entries.options.async_configure(result["flow_id"], _settings())
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SOURCE_SENSOR] == new
    assert entry.unique_id == new


async def test_options_flow_rejects_sensor_of_other_entry(hass) -> None:
    other = "sensor.other_dishwasher"
    MockConfigEntry(
        domain=DOMAIN, data=build_data(source_sensor=other), unique_id=other
    ).add_to_hass(hass)
    entry = MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR)
    entry.add_to_hass(hass)
    result = await _options(hass, entry, other)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_SOURCE_SENSOR: "already_configured"}


async def test_options_flow_validates_settings(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR)
    entry.add_to_hass(hass)
    result = await _options(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _settings(persons=[])
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_persons"}
