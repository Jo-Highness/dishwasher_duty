"""Base entity for Dishwasher Duty."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DishwasherDutyCoordinator, person_key


class DishwasherDutyEntity(CoordinatorEntity[DishwasherDutyCoordinator]):
    """Base class for Dishwasher Duty entities.

    Entity names are "<device name> <translated entity name>". The device is
    named after the config entry title ("Dishwasher Duty" for the first
    dishwasher), so the generated entity ids stay ``*.dishwasher_duty_*``.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: DishwasherDutyCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Dishwasher Duty",
            model="Dishwasher unload tracker",
            entry_type=DeviceEntryType.SERVICE,
        )


class DishwasherDutyPersonEntity(DishwasherDutyEntity):
    """Base class for entities that belong to one person."""

    def __init__(self, coordinator: DishwasherDutyCoordinator, prefix: str, person: str) -> None:
        super().__init__(coordinator, f"{prefix}_{person_key(person)}")
        self._person = person
        # The slug (not the display name) keeps entity ids like
        # sensor.dishwasher_duty_<slug> stable when a person is renamed.
        self._attr_translation_placeholders = {"person": person_key(person).title()}
