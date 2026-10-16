"""The Dishwasher Duty integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_END,
    ATTR_PERSON,
    ATTR_PERSONS,
    ATTR_START,
    CONF_SOURCE_SENSOR,
    DOMAIN,
    ISSUE_SOURCE_SENSOR_MISSING,
    SERVICE_CANCEL_CLAIM,
    SERVICE_CLAIM,
    SERVICE_CLAIM_MULTIPLE,
    SERVICE_GET_STATISTICS,
    SERVICE_RESET_STATISTICS,
)
from .coordinator import DishwasherDutyCoordinator, person_key

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type DishwasherDutyConfigEntry = ConfigEntry[DishwasherDutyCoordinator]

_ENTRY_FIELD = {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}
CLAIM_SCHEMA = vol.Schema({vol.Required(ATTR_PERSON): cv.string, **_ENTRY_FIELD})
CLAIM_MULTIPLE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_PERSONS): vol.All(cv.ensure_list, [cv.string]), **_ENTRY_FIELD}
)
CANCEL_SCHEMA = vol.Schema({vol.Required(ATTR_PERSON): cv.string, **_ENTRY_FIELD})
GET_STATS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_START): cv.datetime,
        vol.Optional(ATTR_END): cv.datetime,
        vol.Optional(ATTR_PERSON): cv.string,
        **_ENTRY_FIELD,
    }
)
RESET_SCHEMA = vol.Schema({vol.Optional(ATTR_PERSON): cv.string, **_ENTRY_FIELD})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's actions (once, independent of entries)."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DishwasherDutyConfigEntry) -> bool:
    """Set up Dishwasher Duty from a config entry."""
    coordinator = DishwasherDutyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    _async_remove_orphaned_entities(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DishwasherDutyConfigEntry) -> bool:
    """Unload a config entry (the coordinator shuts itself down on unload)."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: DishwasherDutyConfigEntry) -> None:
    """Clean up a repair issue that belongs to a removed entry."""
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_SOURCE_SENSOR_MISSING}_{entry.entry_id}")


async def async_migrate_entry(hass: HomeAssistant, entry: DishwasherDutyConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version > 1:
        return False
    if entry.minor_version < 2:
        # 1.1 -> 1.2: entries get the source sensor as unique_id, so the same
        # dishwasher cannot be added twice.
        source = {**entry.data, **entry.options}.get(CONF_SOURCE_SENSOR)
        taken = {
            other.unique_id
            for other in hass.config_entries.async_entries(DOMAIN)
            if other.entry_id != entry.entry_id
        }
        unique_id = source if source and source not in taken else entry.unique_id
        hass.config_entries.async_update_entry(entry, unique_id=unique_id, minor_version=2)
        _LOGGER.debug("Migrated %s to version 1.2 (unique_id=%s)", entry.title, unique_id)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: DishwasherDutyConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _async_remove_orphaned_entities(
    hass: HomeAssistant, entry: DishwasherDutyConfigEntry, coordinator: DishwasherDutyCoordinator
) -> None:
    """Remove per-person entities of persons that are no longer configured."""
    expected = {f"{entry.entry_id}_total_cycles", f"{entry.entry_id}_claimable"}
    for person in coordinator.persons:
        expected.add(f"{entry.entry_id}_person_{person_key(person)}")
        expected.add(f"{entry.entry_id}_claim_{person_key(person)}")

    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id not in expected:
            _LOGGER.debug("Removing orphaned entity %s", reg_entry.entity_id)
            registry.async_remove(reg_entry.entity_id)


# ----------------------------------------------------------------------
# Actions (services)
# ----------------------------------------------------------------------
def _error(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


def _loaded_coordinators(hass: HomeAssistant) -> list[DishwasherDutyCoordinator]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _coordinators_for_call(
    hass: HomeAssistant, call: ServiceCall
) -> list[DishwasherDutyCoordinator]:
    """Return the coordinator selected by ``config_entry_id`` or all loaded ones."""
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise _error("entry_not_found", entry_id=entry_id)
        if entry.state is not ConfigEntryState.LOADED:
            raise _error("entry_not_loaded", title=entry.title)
        return [entry.runtime_data]
    coordinators = _loaded_coordinators(hass)
    if not coordinators:
        raise _error("not_configured")
    return coordinators


def _single_coordinator(hass: HomeAssistant, call: ServiceCall) -> DishwasherDutyCoordinator:
    coordinators = _coordinators_for_call(hass, call)
    if len(coordinators) > 1:
        raise _error("multiple_entries")
    return coordinators[0]


def _async_register_services(hass: HomeAssistant) -> None:
    async def _handle_claim(call: ServiceCall) -> None:
        await _dispatch_claim(hass, call, [call.data[ATTR_PERSON]])

    async def _handle_claim_multiple(call: ServiceCall) -> None:
        await _dispatch_claim(hass, call, call.data[ATTR_PERSONS])

    async def _handle_cancel(call: ServiceCall) -> None:
        person = call.data[ATTR_PERSON]
        coordinators = [c for c in _coordinators_for_call(hass, call) if c.knows_person(person)]
        if not coordinators:
            raise _error("unknown_person", person=person)
        open_ones = [c for c in coordinators if c.claim_open]
        if not open_ones:
            # Let the coordinator raise its translated "no open cycle" error.
            await coordinators[0].async_cancel_claim(person)
            return
        for coordinator in open_ones:
            await coordinator.async_cancel_claim(person)

    async def _handle_get_statistics(call: ServiceCall) -> ServiceResponse:
        coordinator = _single_coordinator(hass, call)
        start = call.data.get(ATTR_START)
        end = call.data.get(ATTR_END)
        if start:
            start = dt_util.as_utc(start)
        if end:
            end = dt_util.as_utc(end)
        return coordinator.get_statistics(start, end, call.data.get(ATTR_PERSON))

    async def _handle_reset(call: ServiceCall) -> None:
        person = call.data.get(ATTR_PERSON)
        for coordinator in _coordinators_for_call(hass, call):
            await coordinator.async_reset_statistics(person)

    hass.services.async_register(DOMAIN, SERVICE_CLAIM, _handle_claim, schema=CLAIM_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLAIM_MULTIPLE,
        _handle_claim_multiple,
        schema=CLAIM_MULTIPLE_SCHEMA,
    )
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_CLAIM, _handle_cancel, schema=CANCEL_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        _handle_get_statistics,
        schema=GET_STATS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_STATISTICS, _handle_reset, schema=RESET_SCHEMA
    )


async def _dispatch_claim(hass: HomeAssistant, call: ServiceCall, persons: list[str]) -> None:
    """Route a claim to the dishwasher(s) that know these persons."""
    coordinators = _coordinators_for_call(hass, call)

    handled = False
    last_error: ServiceValidationError | None = None
    for coordinator in coordinators:
        known = [p for p in persons if coordinator.knows_person(p)]
        if not known:
            continue
        try:
            await coordinator.async_claim_multiple(known)
            handled = True
        except ServiceValidationError as err:
            last_error = err
    if not handled:
        raise last_error or _error("unknown_person", person=", ".join(persons))
