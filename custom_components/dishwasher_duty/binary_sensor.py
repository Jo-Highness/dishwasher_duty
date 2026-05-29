"""Binary sensor platform for Dishwasher Duty."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_CLAIM_OPEN_SINCE,
    ATTR_CO_CLAIM_WINDOW_UNTIL,
    ATTR_CURRENT_CLAIMERS,
    DOMAIN,
)
from .coordinator import DishwasherDutyCoordinator
from .entity import DishwasherDutyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the claimable binary sensor."""
    coordinator: DishwasherDutyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ClaimableBinarySensor(coordinator)])


class ClaimableBinarySensor(DishwasherDutyEntity, BinarySensorEntity):
    """True while the current cycle can still be claimed."""

    _attr_icon = "mdi:hand-back-right"

    def __init__(self, coordinator: DishwasherDutyCoordinator) -> None:
        super().__init__(coordinator, "claimable")
        self._attr_name = "Dishwasher Duty Claimable"
        self.entity_id = "binary_sensor.dishwasher_duty_claimable"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return bool(data.get("claim_open", False))

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            ATTR_CLAIM_OPEN_SINCE: data.get("claim_open_since"),
            ATTR_CO_CLAIM_WINDOW_UNTIL: data.get("co_claim_window_until"),
            ATTR_CURRENT_CLAIMERS: data.get("current_claimers", []),
        }
