"""The Dishwasher Duty integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_END,
    ATTR_PERSON,
    ATTR_PERSONS,
    ATTR_START,
    DOMAIN,
    SERVICE_CANCEL_CLAIM,
    SERVICE_CLAIM,
    SERVICE_CLAIM_MULTIPLE,
    SERVICE_GET_STATISTICS,
    SERVICE_RESET_STATISTICS,
)
from .coordinator import DishwasherDutyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "button"]

CLAIM_SCHEMA = vol.Schema({vol.Required(ATTR_PERSON): cv.string})
CLAIM_MULTIPLE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_PERSONS): vol.All(cv.ensure_list, [cv.string])}
)
CANCEL_SCHEMA = vol.Schema({vol.Required(ATTR_PERSON): cv.string})
GET_STATS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_START): cv.datetime,
        vol.Optional(ATTR_END): cv.datetime,
        vol.Optional(ATTR_PERSON): cv.string,
    }
)
RESET_SCHEMA = vol.Schema({vol.Optional(ATTR_PERSON): cv.string})


def _coordinators(hass: HomeAssistant) -> list[DishwasherDutyCoordinator]:
    return [
        c
        for c in hass.data.get(DOMAIN, {}).values()
        if isinstance(c, DishwasherDutyCoordinator)
    ]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dishwasher Duty from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = DishwasherDutyCoordinator(hass, entry)
    await coordinator.async_setup()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: DishwasherDutyCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    if not hass.data.get(DOMAIN):
        for service in (
            SERVICE_CLAIM,
            SERVICE_CLAIM_MULTIPLE,
            SERVICE_CANCEL_CLAIM,
            SERVICE_GET_STATISTICS,
            SERVICE_RESET_STATISTICS,
        ):
            hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_CLAIM):
        return

    async def _handle_claim(call: ServiceCall) -> None:
        await _dispatch_claim(hass, [call.data[ATTR_PERSON]])

    async def _handle_claim_multiple(call: ServiceCall) -> None:
        await _dispatch_claim(hass, call.data[ATTR_PERSONS])

    async def _handle_cancel(call: ServiceCall) -> None:
        person = call.data[ATTR_PERSON]
        for coordinator in _coordinators(hass):
            await coordinator.async_cancel_claim(person)

    async def _handle_get_statistics(call: ServiceCall) -> ServiceResponse:
        coordinators = _coordinators(hass)
        if not coordinators:
            raise ServiceValidationError("Dishwasher Duty is not configured")
        start = call.data.get(ATTR_START)
        end = call.data.get(ATTR_END)
        if start:
            start = dt_util.as_utc(start)
        if end:
            end = dt_util.as_utc(end)
        return coordinators[0].get_statistics(start, end, call.data.get(ATTR_PERSON))

    async def _handle_reset(call: ServiceCall) -> None:
        person = call.data.get(ATTR_PERSON)
        for coordinator in _coordinators(hass):
            await coordinator.async_reset_statistics(person)

    hass.services.async_register(DOMAIN, SERVICE_CLAIM, _handle_claim, schema=CLAIM_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_CLAIM_MULTIPLE, _handle_claim_multiple,
        schema=CLAIM_MULTIPLE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CANCEL_CLAIM, _handle_cancel, schema=CANCEL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GET_STATISTICS, _handle_get_statistics,
        schema=GET_STATS_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_STATISTICS, _handle_reset, schema=RESET_SCHEMA
    )


async def _dispatch_claim(hass: HomeAssistant, persons: list[str]) -> None:
    """Route a claim to the coordinator(s) that know these persons."""
    coordinators = _coordinators(hass)
    if not coordinators:
        raise ServiceValidationError("Dishwasher Duty is not configured")

    handled = False
    last_error: ServiceValidationError | None = None
    for coordinator in coordinators:
        known = [p for p in persons if coordinator._normalize_person(p) in coordinator.persons]
        if not known:
            continue
        try:
            await coordinator.async_claim_multiple(known)
            handled = True
        except ServiceValidationError as err:
            last_error = err
    if not handled:
        raise last_error or ServiceValidationError(
            "None of the given persons are authorised"
        )
