"""Base entity for Dishwasher Duty."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DishwasherDutyCoordinator


class DishwasherDutyEntity(CoordinatorEntity[DishwasherDutyCoordinator]):
    """Base class for Dishwasher Duty entities."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: DishwasherDutyCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Dishwasher Duty",
            manufacturer="Dishwasher Duty",
            model="Dishwasher unload tracker",
        )
