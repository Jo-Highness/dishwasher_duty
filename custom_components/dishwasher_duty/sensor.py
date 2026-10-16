"""Sensor platform for Dishwasher Duty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DishwasherDutyConfigEntry
from .const import (
    ATTR_CLAIMS_COUNT_TOTAL,
    ATTR_CREDITS_THIS_MONTH,
    ATTR_CREDITS_THIS_WEEK,
    ATTR_CREDITS_THIS_YEAR,
    ATTR_CREDITS_TODAY,
    ATTR_CREDITS_TOTAL,
    ATTR_CURRENT_CYCLE_CLAIMED_BY,
    ATTR_LAST_CLAIM,
    ATTR_LAST_CLAIM_CREDITS,
    ATTR_LAST_CYCLE_FINISHED,
)
from .coordinator import DishwasherDutyCoordinator
from .entity import DishwasherDutyEntity, DishwasherDutyPersonEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DishwasherDutyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the cycle counter and per-person credit sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [TotalCyclesSensor(coordinator)]
    entities.extend(PersonCreditsSensor(coordinator, p) for p in coordinator.persons)
    async_add_entities(entities)


class TotalCyclesSensor(DishwasherDutyEntity, SensorEntity):
    """Overall counter of finished dishwasher cycles."""

    _attr_translation_key = "total_cycles"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: DishwasherDutyCoordinator) -> None:
        super().__init__(coordinator, "total_cycles")

    @property
    def native_value(self) -> int:
        return self.coordinator.total_cycles

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            ATTR_LAST_CYCLE_FINISHED: data.get(ATTR_LAST_CYCLE_FINISHED),
            ATTR_CURRENT_CYCLE_CLAIMED_BY: data.get(ATTR_CURRENT_CYCLE_CLAIMED_BY),
            ATTR_LAST_CLAIM_CREDITS: data.get(ATTR_LAST_CLAIM_CREDITS),
        }


class PersonCreditsSensor(DishwasherDutyPersonEntity, SensorEntity):
    """Accumulated unload credits for one person."""

    _attr_translation_key = "person_credits"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "credits"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: DishwasherDutyCoordinator, person: str) -> None:
        super().__init__(coordinator, "person", person)

    @property
    def native_value(self) -> float:
        return self.coordinator.person_stats(self._person)[ATTR_CREDITS_TOTAL]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stats = self.coordinator.person_stats(self._person)
        return {
            ATTR_CREDITS_TOTAL: stats[ATTR_CREDITS_TOTAL],
            ATTR_CREDITS_TODAY: stats[ATTR_CREDITS_TODAY],
            ATTR_CREDITS_THIS_WEEK: stats[ATTR_CREDITS_THIS_WEEK],
            ATTR_CREDITS_THIS_MONTH: stats[ATTR_CREDITS_THIS_MONTH],
            ATTR_CREDITS_THIS_YEAR: stats[ATTR_CREDITS_THIS_YEAR],
            ATTR_CLAIMS_COUNT_TOTAL: stats[ATTR_CLAIMS_COUNT_TOTAL],
            ATTR_LAST_CLAIM: stats[ATTR_LAST_CLAIM],
            "person": self._person,
        }
