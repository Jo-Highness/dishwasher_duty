"""Config- and options-flow tests for Dishwasher Duty."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dishwasher_duty.const import (
    CONF_CO_CLAIM_WINDOW,
    CONF_SOURCE_SENSOR,
    DOMAIN,
)

from .conftest import SENSOR, build_data


async def test_form_shown(hass) -> None:
    """The initial step shows the setup form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_flow_happy_path(hass) -> None:
    """A valid submission creates the entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], build_data())

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Dishwasher Duty"
    assert result["data"][CONF_SOURCE_SENSOR] == SENSOR


async def test_flow_requires_persons(hass) -> None:
    """Submitting without any person shows the no_persons error."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], build_data(persons=[])
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_persons"}


async def test_options_flow_update_window(hass) -> None:
    """The co-claim window can be changed through the options flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=build_data())
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], build_data(co_claim_window=120)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_CO_CLAIM_WINDOW] == 120
