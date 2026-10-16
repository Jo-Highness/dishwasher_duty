"""Button platform for Dishwasher Duty (per-person claim buttons)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DishwasherDutyConfigEntry
from .coordinator import DishwasherDutyCoordinator
from .entity import DishwasherDutyPersonEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DishwasherDutyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one 'I unloaded it' button per authorised person."""
    coordinator = entry.runtime_data
    async_add_entities(ClaimButton(coordinator, p) for p in coordinator.persons)


class ClaimButton(DishwasherDutyPersonEntity, ButtonEntity):
    """Lets a person claim the open cycle with one tap."""

    _attr_translation_key = "claim"

    def __init__(self, coordinator: DishwasherDutyCoordinator, person: str) -> None:
        super().__init__(coordinator, "claim", person)

    async def async_press(self) -> None:
        await self.coordinator.async_claim(self._person)
