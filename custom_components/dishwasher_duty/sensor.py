"""Sensor platform for Dishwasher Duty."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    DOMAIN,
)
from .coordinator import DishwasherDutyCoordinator, person_key
from .entity import DishwasherDutyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cycle counter and per-person credit sensors."""
    coordinator: DishwasherDutyCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [TotalCyclesSensor(coordinator)]
    entities.extend(PersonCreditsSensor(coordinator, p) for p in coordinator.persons)
    async_add_entities(entities)


class TotalCyclesSensor(DishwasherDutyEntity, SensorEntity):
    """Overall counter of finished dishwasher cycles."""

    _attr_icon = "mdi:dishwasher"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: DishwasherDutyCoordinator) -> None:
        super().__init__(coordinator, "total_cycles")
        self._attr_name = "Dishwasher Duty Total Cycles"
        self.entity_id = "sensor.dishwasher_duty_total_cycles"

    @property
    def native_value(self) -> int:
        return self.coordinator.total_cycles

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            ATTR_LAST_CYCLE_FINISHED: data.get(ATTR_LAST_CYCLE_FINISHED),
            ATTR_CURRENT_CYCLE_CLAIMED_BY: data.get(ATTR_CURRENT_CYCLE_CLAIMED_BY),
            ATTR_LAST_CLAIM_CREDITS: data.get(ATTR_LAST_CLAIM_CREDITS),
        }


class PersonCreditsSensor(DishwasherDutyEntity, SensorEntity):
    """Accumulated unload credits for one person."""

    _attr_icon = "mdi:account-check"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "credits"

    def __init__(self, coordinator: DishwasherDutyCoordinator, person: str) -> None:
        super().__init__(coordinator, f"person_{person_key(person)}")
        self._person = person
        self._attr_name = f"Dishwasher Duty {person_key(person).title()}"
        self.entity_id = f"sensor.dishwasher_duty_{person_key(person)}"

    @property
    def native_value(self) -> float:
        return self.coordinator.person_stats(self._person)[ATTR_CREDITS_TOTAL]

    @property
    def extra_state_attributes(self) -> dict:
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
