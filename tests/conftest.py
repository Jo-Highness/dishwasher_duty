"""Common fixtures for Dishwasher Duty tests."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dishwasher_duty.const import (
    CONF_ALLOW_CO_CLAIM,
    CONF_CO_CLAIM_WINDOW,
    CONF_DEBOUNCE,
    CONF_FINISHED_VALUE,
    CONF_PERSONS,
    CONF_RUNNING_VALUE,
    CONF_SOURCE_SENSOR,
    DOMAIN,
)
from custom_components.dishwasher_duty.coordinator import DishwasherDutyCoordinator

SENSOR = "sensor.dishwasher_operation_state"
PERSONS = ["person.alice", "person.bob", "person.carol"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def build_data(**overrides: Any) -> dict[str, Any]:
    data = {
        CONF_SOURCE_SENSOR: SENSOR,
        CONF_FINISHED_VALUE: "Finished",
        CONF_RUNNING_VALUE: "Run",
        CONF_PERSONS: PERSONS,
        CONF_ALLOW_CO_CLAIM: True,
        CONF_CO_CLAIM_WINDOW: 90,
        CONF_DEBOUNCE: 0,
    }
    data.update(overrides)
    return data


@pytest.fixture
def make_coordinator(
    hass,
) -> Callable[..., Coroutine[Any, Any, DishwasherDutyCoordinator]]:
    async def _factory(**overrides: Any) -> DishwasherDutyCoordinator:
        entry = MockConfigEntry(domain=DOMAIN, data=build_data(**overrides))
        entry.add_to_hass(hass)
        coordinator = DishwasherDutyCoordinator(hass, entry)
        await coordinator._async_restore()
        return coordinator

    return _factory


async def feed(coordinator: DishwasherDutyCoordinator, *states: str) -> None:
    """Drive the source-sensor state machine through a sequence of states."""
    for state in states:
        await coordinator._async_process_state(state)
