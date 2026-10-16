"""Binary sensor platform for Dishwasher Duty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DishwasherDutyConfigEntry
from .const import (
    ATTR_CLAIM_OPEN_SINCE,
    ATTR_CO_CLAIM_WINDOW_UNTIL,
    ATTR_CURRENT_CLAIMERS,
)
from .coordinator import DishwasherDutyCoordinator
from .entity import DishwasherDutyEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DishwasherDutyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the claimable binary sensor."""
    async_add_entities([ClaimableBinarySensor(entry.runtime_data)])


class ClaimableBinarySensor(DishwasherDutyEntity, BinarySensorEntity):
    """True while the current cycle can still be claimed."""

    _attr_translation_key = "claimable"

    def __init__(self, coordinator: DishwasherDutyCoordinator) -> None:
        super().__init__(coordinator, "claimable")

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return bool(data.get("claim_open", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            ATTR_CLAIM_OPEN_SINCE: data.get("claim_open_since"),
            ATTR_CO_CLAIM_WINDOW_UNTIL: data.get("co_claim_window_until"),
            ATTR_CURRENT_CLAIMERS: data.get("current_claimers", []),
        }
