"""Button platform for Dishwasher Duty (per-person claim buttons)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DishwasherDutyCoordinator, person_key
from .entity import DishwasherDutyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one 'I unloaded it' button per authorised person."""
    coordinator: DishwasherDutyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(ClaimButton(coordinator, p) for p in coordinator.persons)


class ClaimButton(DishwasherDutyEntity, ButtonEntity):
    """Lets a person claim the open cycle with one tap."""

    _attr_icon = "mdi:hand-back-right-outline"

    def __init__(self, coordinator: DishwasherDutyCoordinator, person: str) -> None:
        super().__init__(coordinator, f"claim_{person_key(person)}")
        self._person = person
        self._attr_name = f"Dishwasher Duty Claim {person_key(person).title()}"
        self.entity_id = f"button.dishwasher_duty_claim_{person_key(person)}"

    async def async_press(self) -> None:
        await self.coordinator.async_claim(self._person)
