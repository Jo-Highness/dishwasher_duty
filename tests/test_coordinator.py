"""Tests for the Dishwasher Duty coordinator and claim engine."""

from __future__ import annotations

import pytest
from freezegun import freeze_time
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dishwasher_duty.const import DOMAIN
from custom_components.dishwasher_duty.coordinator import (
    DishwasherDutyCoordinator,
    distribute_credits,
)

from .conftest import build_data, feed


# --------------------------------------------------------------------------
# Transition validity / overall counter
# --------------------------------------------------------------------------
async def test_valid_running_to_finished_opens_cycle(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished")
    assert c.total_cycles == 1
    assert c.data["claim_open"] is True


async def test_invalid_transitions_do_not_count(make_coordinator):
    c = await make_coordinator()
    await feed(c, "unavailable", "Finished")  # unavailable -> Finished
    assert c.total_cycles == 0
    await feed(c, "unknown", "Finished")  # unknown -> Finished
    assert c.total_cycles == 0
    # Finished -> Finished must not double count after one valid cycle.
    await feed(c, "Run", "Finished", "Finished")
    assert c.total_cycles == 1


async def test_overall_counter_counts_unclaimed(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished", "Run", "Finished")
    assert c.total_cycles == 2
    assert all(cy["status"] == "unclaimed" for cy in c.cycles)


# --------------------------------------------------------------------------
# Claiming
# --------------------------------------------------------------------------
async def test_single_claim_without_co_claim(make_coordinator):
    c = await make_coordinator(allow_co_claim=False)
    await feed(c, "Run", "Finished")
    await c.async_claim("person.alice")
    # Finalised immediately.
    assert c.data["claim_open"] is False
    assert c.cycles[-1]["credits"] == {"person.alice": 1.0}
    # A later claim is rejected (no open cycle).
    with pytest.raises(ServiceValidationError):
        await c.async_claim("person.bob")


async def test_co_claim_split_two(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished")
    await c.async_claim("person.alice")
    await c.async_claim("person.bob")
    await c._async_finalize_current()
    credits = c.cycles[-1]["credits"]
    assert credits == {"person.alice": 0.5, "person.bob": 0.5}
    assert round(sum(credits.values()), 2) == 1.0


async def test_co_claim_split_three(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished")
    await c.async_claim_multiple(["person.alice", "person.bob", "person.carol"])
    await c._async_finalize_current()
    credits = c.cycles[-1]["credits"]
    assert round(sum(credits.values()), 2) == 1.0
    assert sorted(credits.values()) == [0.33, 0.33, 0.34]


async def test_claim_idempotent_per_person(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished")
    await c.async_claim("person.alice")
    await c.async_claim("person.alice")
    assert c.cycles[-1]["claimers"] == ["person.alice"]
    await c._async_finalize_current()
    assert c.cycles[-1]["credits"] == {"person.alice": 1.0}


async def test_unauthorized_person_rejected(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished")
    with pytest.raises(ServiceValidationError):
        await c.async_claim("person.dave")


async def test_window_closes_on_new_running(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished")
    assert c.data["claim_open"] is True
    await feed(c, "Run")  # a new programme starts
    assert c.data["claim_open"] is False
    assert c.cycles[-1]["status"] == "unclaimed"
    assert c.total_cycles == 1


async def test_cancel_claim_reopens_window(make_coordinator):
    c = await make_coordinator()
    await feed(c, "Run", "Finished")
    await c.async_claim("person.alice")
    await c.async_cancel_claim("person.alice")
    assert c.data["current_claimers"] == []
    assert c.data["claim_open"] is True


def test_distribute_credits_sums_to_one():
    for n in range(1, 6):
        people = [f"person.p{i}" for i in range(n)]
        credits = distribute_credits(people)
        assert round(sum(credits.values()), 2) == 1.0
        assert len(credits) == n


# --------------------------------------------------------------------------
# Persistence over restart
# --------------------------------------------------------------------------
async def test_persistence_open_window_over_restart(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=build_data())
    entry.add_to_hass(hass)

    c1 = DishwasherDutyCoordinator(hass, entry)
    await c1._async_restore()
    await feed(c1, "Run", "Finished")
    await c1.async_claim("person.alice")  # opens co-claim window
    await c1.async_shutdown()  # persists + cancels timer

    # Fresh coordinator, same entry/store -> restore.
    c2 = DishwasherDutyCoordinator(hass, entry)
    await c2._async_restore()
    assert c2.total_cycles == 1
    assert c2._claim_open is True
    assert c2._current_cycle()["claimers"] == ["person.alice"]
    # Finalising after restart still credits the claimer.
    await c2._async_finalize_current()
    assert c2.cycles[-1]["credits"] == {"person.alice": 1.0}


# --------------------------------------------------------------------------
# Statistics over periods
# --------------------------------------------------------------------------
async def test_statistics_periods_and_range(make_coordinator):
    c = await make_coordinator()
    # Inject cycles with controlled timestamps (UTC == local in test tz).
    c.cycles = [
        _cycle("today", "2026-05-15T08:00:00+00:00", {"person.alice": 1.0}),
        _cycle("week", "2026-05-11T09:00:00+00:00", {"person.alice": 0.5}),
        _cycle("month", "2026-05-03T09:00:00+00:00", {"person.alice": 1.0}),
        _cycle("lastyear", "2025-12-20T09:00:00+00:00", {"person.alice": 1.0}),
    ]
    c.total_cycles = len(c.cycles)

    with freeze_time("2026-05-15 12:00:00"):  # a Friday
        stats = c.person_stats("person.alice")
        assert stats["credits_total"] == 3.5
        assert stats["credits_today"] == 1.0
        assert stats["credits_this_week"] == 1.5
        assert stats["credits_this_month"] == 2.5
        assert stats["credits_this_year"] == 2.5
        assert stats["claims_count_total"] == 4

        from homeassistant.util import dt as dt_util

        start = dt_util.parse_datetime("2026-05-01T00:00:00+00:00")
        end = dt_util.parse_datetime("2026-05-31T23:59:59+00:00")
        result = c.get_statistics(start, end, None)
        assert result["total_cycles"] == 3
        assert result["unclaimed_cycles"] == 0
        assert result["per_person"]["person.alice"]["participations"] == 3
        assert result["per_person"]["person.alice"]["credits"] == 2.5
        assert len(result["timeline"]) == 3


def _cycle(cid: str, ts: str, credits: dict) -> dict:
    return {
        "cycle_id": cid,
        "finished_timestamp": ts,
        "claimers": list(credits.keys()),
        "credits": credits,
        "claimed_at": ts,
        "status": "claimed",
    }
