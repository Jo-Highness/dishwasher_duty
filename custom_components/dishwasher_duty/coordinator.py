"""Central logic for Dishwasher Duty: state tracking + claim engine.

A single :class:`DishwasherDutyCoordinator` owns all runtime state for one
dishwasher: it watches the source sensor for a valid ``Running -> Finished``
transition, opens a claim window, distributes credit among the people who
claim the cycle, persists the full cycle history and derives per-person
statistics.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALLOW_CO_CLAIM,
    CONF_CO_CLAIM_WINDOW,
    CONF_DEBOUNCE,
    CONF_FINISHED_VALUE,
    CONF_PERSONS,
    CONF_RUNNING_VALUE,
    CONF_SOURCE_SENSOR,
    DEFAULT_ALLOW_CO_CLAIM,
    DEFAULT_CO_CLAIM_WINDOW,
    DEFAULT_DEBOUNCE,
    DEFAULT_FINISHED_VALUE,
    DEFAULT_RUNNING_VALUE,
    DOMAIN,
    IGNORED_STATES,
    STATUS_CLAIMED,
    STATUS_UNCLAIMED,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def person_key(entity_id: str) -> str:
    """Return the object_id slug of a person entity id."""
    return entity_id.split(".", 1)[-1]


def distribute_credits(claimers: list[str]) -> dict[str, float]:
    """Split a credit of exactly 1.0 over the claimers (2 decimals, sum=1.0)."""
    n = len(claimers)
    if n == 0:
        return {}
    base = int(100 // n)  # cents each
    remainder = 100 - base * n  # leftover cents handed to the first claimers
    credits: dict[str, float] = {}
    for index, person in enumerate(claimers):
        cents = base + (1 if index < remainder else 0)
        credits[person] = round(cents / 100, 2)
    return credits


class DishwasherDutyCoordinator(DataUpdateCoordinator[dict]):
    """Track the dishwasher and manage cycle claims."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN)
        self.entry = entry
        self._config = {**entry.data, **entry.options}
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{entry.entry_id}"
        )
        self._lock = asyncio.Lock()
        self._unsubs: list = []
        self._unsub_timer = None

        # --- persisted state ---
        self.total_cycles: int = 0
        self.cycles: list[dict] = []
        self._last_state: str | None = None
        self._claim_open: bool = False
        self._current_cycle_id: str | None = None
        self._co_claim_until: datetime | None = None

    # ------------------------------------------------------------------
    # Config accessors
    # ------------------------------------------------------------------
    @property
    def source_sensor(self) -> str:
        return self._config[CONF_SOURCE_SENSOR]

    @property
    def finished_value(self) -> str:
        return self._config.get(CONF_FINISHED_VALUE, DEFAULT_FINISHED_VALUE)

    @property
    def running_value(self) -> str:
        return self._config.get(CONF_RUNNING_VALUE, DEFAULT_RUNNING_VALUE)

    @property
    def persons(self) -> list[str]:
        return list(self._config.get(CONF_PERSONS, []))

    @property
    def allow_co_claim(self) -> bool:
        return bool(self._config.get(CONF_ALLOW_CO_CLAIM, DEFAULT_ALLOW_CO_CLAIM))

    @property
    def co_claim_window(self) -> int:
        return int(self._config.get(CONF_CO_CLAIM_WINDOW, DEFAULT_CO_CLAIM_WINDOW))

    @property
    def debounce_seconds(self) -> int:
        return int(self._config.get(CONF_DEBOUNCE, DEFAULT_DEBOUNCE))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Restore state and start listeners."""
        await self._async_restore()

        self._unsubs.append(
            async_track_state_change_event(
                self.hass, [self.source_sensor], self._handle_state_event
            )
        )
        # Recompute the daily/period attributes at local midnight.
        self._unsubs.append(
            async_track_time_change(
                self.hass, self._handle_midnight, hour=0, minute=0, second=5
            )
        )

        # Re-arm or resolve a co-claim window that was open across a restart.
        if self._claim_open and self._co_claim_until is not None:
            if self._co_claim_until <= dt_util.utcnow():
                await self._async_finalize_current()
            else:
                self._schedule_co_claim_timer(self._co_claim_until)

        # Seed last_state from the live sensor if we have nothing stored.
        if self._last_state is None:
            state = self.hass.states.get(self.source_sensor)
            if state is not None:
                self._last_state = state.state

        self.async_set_updated_data(self._snapshot())

    async def async_shutdown(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        async with self._lock:
            await self._store.async_save(self._build_storage_data())

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _build_storage_data(self) -> dict:
        return {
            "total_cycles": self.total_cycles,
            "cycles": self.cycles,
            "last_state": self._last_state,
            "claim_open": self._claim_open,
            "current_cycle_id": self._current_cycle_id,
            "co_claim_until": (
                self._co_claim_until.isoformat() if self._co_claim_until else None
            ),
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._build_storage_data, 1)

    async def _async_restore(self) -> None:
        stored = await self._store.async_load()
        if not stored:
            return
        self.total_cycles = int(stored.get("total_cycles", 0))
        self.cycles = list(stored.get("cycles", []))
        self._last_state = stored.get("last_state")
        self._claim_open = bool(stored.get("claim_open", False))
        self._current_cycle_id = stored.get("current_cycle_id")
        until = stored.get("co_claim_until")
        self._co_claim_until = dt_util.parse_datetime(until) if until else None
        _LOGGER.debug(
            "%s: restored %d cycles, claim_open=%s", DOMAIN, self.total_cycles,
            self._claim_open,
        )

    # ------------------------------------------------------------------
    # State tracking
    # ------------------------------------------------------------------
    @callback
    def _handle_state_event(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        new_value = new_state.state if new_state else None
        self.hass.async_create_task(self._async_process_state(new_value))

    async def _async_process_state(self, new_value: str | None) -> None:
        async with self._lock:
            await self._process_state_locked(new_value)
        self.async_set_updated_data(self._snapshot())

    async def _process_state_locked(self, new_value: str | None) -> None:
        if new_value is None:
            return
        prev = self._last_state

        # A new run starting closes any still-open claim window.
        if new_value == self.running_value and self._claim_open:
            await self._close_open_window()

        # Only a genuine Running -> Finished transition opens a new cycle.
        if new_value == self.finished_value and prev == self.running_value:
            self._register_finished_cycle()

        # Always remember the raw previous state so glitches like
        # unavailable -> Finished are NOT counted as a cycle.
        self._last_state = new_value

    def _register_finished_cycle(self) -> None:
        now = dt_util.utcnow()
        # Optional debounce against rapid re-triggers.
        if self.debounce_seconds and self.cycles:
            last_ts = dt_util.parse_datetime(self.cycles[-1]["finished_timestamp"])
            if last_ts and (now - last_ts).total_seconds() < self.debounce_seconds:
                _LOGGER.debug("%s: debounced finished transition", DOMAIN)
                return

        cycle_id = f"{int(now.timestamp())}-{self.total_cycles + 1}"
        cycle = {
            "cycle_id": cycle_id,
            "finished_timestamp": now.isoformat(),
            "claimers": [],
            "credits": {},
            "claimed_at": None,
            "status": STATUS_UNCLAIMED,
        }
        self.cycles.append(cycle)
        self.total_cycles += 1
        self._claim_open = True
        self._current_cycle_id = cycle_id
        self._co_claim_until = None
        self._cancel_timer()
        _LOGGER.info(
            "%s: cycle %s finished (#%d) -> claim window open",
            DOMAIN, cycle_id, self.total_cycles,
        )
        self._save()

    # ------------------------------------------------------------------
    # Claim engine
    # ------------------------------------------------------------------
    def _current_cycle(self) -> dict | None:
        if self._current_cycle_id is None:
            return None
        for cycle in reversed(self.cycles):
            if cycle["cycle_id"] == self._current_cycle_id:
                return cycle
        return None

    async def async_claim(self, person: str) -> None:
        """Claim the open cycle for a single person."""
        await self.async_claim_multiple([person])

    async def async_claim_multiple(self, persons: list[str]) -> None:
        """Claim the open cycle for one or more people."""
        normalized = [self._normalize_person(p) for p in persons]
        async with self._lock:
            cycle = self._current_cycle()
            if not self._claim_open or cycle is None:
                raise ServiceValidationError("No claimable cycle is open")

            changed = False
            for person in normalized:
                if person not in self.persons:
                    raise ServiceValidationError(
                        f"{person} is not an authorised person"
                    )
                if person in cycle["claimers"]:
                    continue  # idempotent: one contribution per person/cycle
                cycle["claimers"].append(person)
                changed = True

            if not changed:
                return

            if not self.allow_co_claim:
                self._finalize_locked(cycle)
            elif self._co_claim_until is None:
                # First claim starts the co-claim window.
                self._co_claim_until = dt_util.utcnow() + timedelta(
                    seconds=self.co_claim_window
                )
                self._schedule_co_claim_timer(self._co_claim_until)
            self._save()
        self.async_set_updated_data(self._snapshot())

    async def async_cancel_claim(self, person: str) -> None:
        """Withdraw a person's claim while the window is still open."""
        person = self._normalize_person(person)
        async with self._lock:
            cycle = self._current_cycle()
            if not self._claim_open or cycle is None:
                return
            if person in cycle["claimers"]:
                cycle["claimers"].remove(person)
                if not cycle["claimers"]:
                    # No one left: stop the window so a fresh claim restarts it.
                    self._co_claim_until = None
                    self._cancel_timer()
                self._save()
        self.async_set_updated_data(self._snapshot())

    @callback
    def _on_co_claim_timeout(self, _now: datetime) -> None:
        self.hass.async_create_task(self._async_finalize_current())

    async def _async_finalize_current(self) -> None:
        async with self._lock:
            cycle = self._current_cycle()
            if cycle is not None and self._claim_open:
                self._finalize_locked(cycle)
                self._save()
        self.async_set_updated_data(self._snapshot())

    def _finalize_locked(self, cycle: dict) -> None:
        """Finalise the open cycle, distributing credit to its claimers."""
        if cycle["claimers"]:
            cycle["credits"] = distribute_credits(cycle["claimers"])
            cycle["status"] = STATUS_CLAIMED
            cycle["claimed_at"] = dt_util.utcnow().isoformat()
            _LOGGER.info(
                "%s: cycle %s claimed by %s -> %s",
                DOMAIN, cycle["cycle_id"], cycle["claimers"], cycle["credits"],
            )
        self._claim_open = False
        self._current_cycle_id = None
        self._co_claim_until = None
        self._cancel_timer()

    async def _close_open_window(self) -> None:
        """A new run started; finalise existing claimers or leave unclaimed."""
        cycle = self._current_cycle()
        if cycle is None:
            self._claim_open = False
            self._current_cycle_id = None
            self._co_claim_until = None
            self._cancel_timer()
            return
        if cycle["claimers"]:
            self._finalize_locked(cycle)
        else:
            _LOGGER.info("%s: cycle %s left unclaimed (new run)", DOMAIN,
                         cycle["cycle_id"])
            self._claim_open = False
            self._current_cycle_id = None
            self._co_claim_until = None
            self._cancel_timer()
        self._save()

    # ------------------------------------------------------------------
    # Timer helpers
    # ------------------------------------------------------------------
    def _schedule_co_claim_timer(self, when: datetime) -> None:
        self._cancel_timer()
        self._unsub_timer = async_track_point_in_time(
            self.hass, self._on_co_claim_timeout, when
        )

    def _cancel_timer(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def _normalize_person(self, person: str) -> str:
        """Accept either 'person.x' or 'x' and return the configured id."""
        if person in self.persons:
            return person
        for configured in self.persons:
            if person_key(configured) == person or configured == f"person.{person}":
                return configured
        return person

    @staticmethod
    def _period_starts(now_local: datetime) -> dict[str, date]:
        today = now_local.date()
        return {
            "today": today,
            "week": today - timedelta(days=today.weekday()),
            "month": today.replace(day=1),
            "year": today.replace(month=1, day=1),
        }

    def person_stats(self, person: str) -> dict[str, Any]:
        """Aggregate credit statistics for one person across all cycles."""
        now_local = dt_util.now()
        starts = self._period_starts(now_local)
        totals = {
            "credits_total": 0.0,
            "credits_today": 0.0,
            "credits_this_week": 0.0,
            "credits_this_month": 0.0,
            "credits_this_year": 0.0,
            "claims_count_total": 0,
            "last_claim": None,
        }
        for cycle in self.cycles:
            credit = cycle.get("credits", {}).get(person)
            if not credit:
                continue
            totals["credits_total"] += credit
            totals["claims_count_total"] += 1
            claimed_at = cycle.get("claimed_at") or cycle.get("finished_timestamp")
            ts = dt_util.parse_datetime(claimed_at) if claimed_at else None
            if ts is None:
                continue
            local = dt_util.as_local(ts)
            if totals["last_claim"] is None or claimed_at > totals["last_claim"]:
                totals["last_claim"] = claimed_at
            if local.date() >= starts["today"]:
                totals["credits_today"] += credit
            if local.date() >= starts["week"]:
                totals["credits_this_week"] += credit
            if local.date() >= starts["month"]:
                totals["credits_this_month"] += credit
            if local.date() >= starts["year"]:
                totals["credits_this_year"] += credit
        for key in (
            "credits_total", "credits_today", "credits_this_week",
            "credits_this_month", "credits_this_year",
        ):
            totals[key] = round(totals[key], 2)
        return totals

    def get_statistics(
        self, start: datetime | None, end: datetime | None, person: str | None
    ) -> dict[str, Any]:
        """Structured statistics for a time range (service response)."""
        person = self._normalize_person(person) if person else None
        per_person: dict[str, dict[str, Any]] = {}
        timeline: list[dict] = []
        total = 0
        unclaimed = 0
        for cycle in self.cycles:
            ts_raw = cycle.get("finished_timestamp")
            ts = dt_util.parse_datetime(ts_raw) if ts_raw else None
            if ts is None:
                continue
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            total += 1
            if cycle.get("status") != STATUS_CLAIMED:
                unclaimed += 1
            timeline.append(
                {
                    "cycle_id": cycle["cycle_id"],
                    "finished_timestamp": ts_raw,
                    "claimers": cycle.get("claimers", []),
                    "credits": cycle.get("credits", {}),
                    "status": cycle.get("status"),
                }
            )
            for claimer, credit in cycle.get("credits", {}).items():
                if person and claimer != person:
                    continue
                stats = per_person.setdefault(
                    claimer, {"participations": 0, "credits": 0.0}
                )
                stats["participations"] += 1
                stats["credits"] = round(stats["credits"] + credit, 2)

        return {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "total_cycles": total,
            "unclaimed_cycles": unclaimed,
            "per_person": per_person,
            "timeline": timeline,
        }

    async def async_reset_statistics(self, person: str | None) -> None:
        """Reset stored history. With a person, only their credit entries."""
        async with self._lock:
            if person is None:
                self.cycles = []
                self.total_cycles = 0
                self._claim_open = False
                self._current_cycle_id = None
                self._co_claim_until = None
                self._cancel_timer()
            else:
                person = self._normalize_person(person)
                for cycle in self.cycles:
                    if person in cycle.get("credits", {}):
                        cycle["credits"].pop(person, None)
                    if person in cycle.get("claimers", []):
                        cycle["claimers"].remove(person)
            self._save()
        _LOGGER.warning("%s: statistics reset (person=%s)", DOMAIN, person)
        self.async_set_updated_data(self._snapshot())

    # ------------------------------------------------------------------
    # Snapshot / midnight
    # ------------------------------------------------------------------
    @callback
    def _handle_midnight(self, _now: datetime) -> None:
        self.async_set_updated_data(self._snapshot())

    def _snapshot(self) -> dict:
        cycle = self._current_cycle()
        return {
            "total_cycles": self.total_cycles,
            "claim_open": self._claim_open,
            "current_claimers": list(cycle["claimers"]) if cycle else [],
            "claim_open_since": cycle["finished_timestamp"] if cycle else None,
            "co_claim_window_until": (
                self._co_claim_until.isoformat() if self._co_claim_until else None
            ),
            "last_cycle_finished": (
                self.cycles[-1]["finished_timestamp"] if self.cycles else None
            ),
            "last_claim_credits": self._last_claim_credits(),
            "current_cycle_claimed_by": cycle["claimers"] if cycle else [],
        }

    def _last_claim_credits(self) -> dict:
        for cycle in reversed(self.cycles):
            if cycle.get("status") == STATUS_CLAIMED:
                return cycle.get("credits", {})
        return {}
