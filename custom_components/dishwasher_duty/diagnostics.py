"""Diagnostics support for Dishwasher Duty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import DishwasherDutyConfigEntry
from .const import CONF_PERSONS

TO_REDACT = {CONF_PERSONS}
RECENT_CYCLES = 10


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DishwasherDutyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (person ids are pseudonymised)."""
    coordinator = entry.runtime_data
    alias = {person: f"person_{index}" for index, person in enumerate(coordinator.persons, 1)}

    def _anon(person: str) -> str:
        return alias.setdefault(person, f"person_{len(alias) + 1}")

    source = hass.states.get(coordinator.source_sensor)
    recent = [
        {
            "finished_timestamp": cycle.get("finished_timestamp"),
            "claimed_at": cycle.get("claimed_at"),
            "status": cycle.get("status"),
            "claimers": [_anon(p) for p in cycle.get("claimers", [])],
            "credits": {_anon(p): c for p, c in cycle.get("credits", {}).items()},
        }
        for cycle in coordinator.cycles[-RECENT_CYCLES:]
    ]
    return {
        "entry": {
            "title": entry.title,
            "version": f"{entry.version}.{entry.minor_version}",
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
            "person_count": len(coordinator.persons),
        },
        "source_sensor": {
            "entity_id": coordinator.source_sensor,
            "state": source.state if source else None,
            "options": source.attributes.get("options") if source else None,
            "finished_value": coordinator.finished_value,
            "running_value": coordinator.running_value,
            "last_state": coordinator.last_state,
        },
        "state": {
            "total_cycles": coordinator.total_cycles,
            "stored_cycles": len(coordinator.cycles),
            "claim_open": coordinator.claim_open,
            "current_claimers": [
                _anon(p) for p in (coordinator.data or {}).get("current_claimers", [])
            ],
            "co_claim_window_until": (coordinator.data or {}).get("co_claim_window_until"),
        },
        "recent_cycles": recent,
    }
