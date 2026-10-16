"""Tests for the Dishwasher Duty coordinator and claim engine."""

from __future__ import annotations

from freezegun import freeze_time
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dishwasher_duty.const import (
    CONF_FINISHED_VALUE,
    CONF_RUNNING_VALUE,
    DEFAULT_FINISHED_VALUE,
    DEFAULT_RUNNING_VALUE,
    DOMAIN,
)
from custom_components.dishwasher_duty.coordinator import (
    DishwasherDutyCoordinator,
    distribute_credits,
    states_match,
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


# --------------------------------------------------------------------------
# Person resolution: the services document "Name (or slug)"
# --------------------------------------------------------------------------
async def test_claim_by_slug_case_insensitive(make_coordinator):
    """Claiming with the object-id slug in any case resolves the configured person."""
    c = await make_coordinator(allow_co_claim=False)
    await feed(c, "Run", "Finished")
    await c.async_claim("Alice")  # capitalised slug, not the exact entity id
    assert c.cycles[-1]["credits"] == {"person.alice": 1.0}


async def test_claim_by_display_name(hass, make_coordinator):
    """Claiming with the person's friendly name resolves the configured person."""
    hass.states.async_set("person.alice", "home", {"friendly_name": "Alice Example"})
    c = await make_coordinator(allow_co_claim=False)
    await feed(c, "Run", "Finished")
    await c.async_claim("Alice Example")
    assert c.cycles[-1]["credits"] == {"person.alice": 1.0}


# --------------------------------------------------------------------------
# State values: case-insensitive, lowercase Home Connect values (HA 2025.1+)
# --------------------------------------------------------------------------
async def test_lowercase_states_match_legacy_config(make_coordinator):
    """An entry configured with Run/Finished also matches run/finished."""
    c = await make_coordinator()  # configured "Run" / "Finished"
    await feed(c, "run", "finished")
    assert c.total_cycles == 1


async def test_default_values_are_lowercase(make_coordinator):
    c = await make_coordinator()
    c._config.pop(CONF_FINISHED_VALUE)
    c._config.pop(CONF_RUNNING_VALUE)
    assert (c.running_value, c.finished_value) == (DEFAULT_RUNNING_VALUE, DEFAULT_FINISHED_VALUE)
    assert (DEFAULT_RUNNING_VALUE, DEFAULT_FINISHED_VALUE) == ("run", "finished")
    await feed(c, "Run", "FINISHED")
    assert c.total_cycles == 1


def test_states_match():
    assert states_match("finished", "Finished")
    assert states_match(" Run ", "run")
    assert not states_match(None, "run")
    assert not states_match("running", "run")


# --------------------------------------------------------------------------
# unavailable/unknown during a programme
# --------------------------------------------------------------------------
@pytest.mark.parametrize("glitch", ["unavailable", "unknown"])
async def test_unavailable_mid_run_still_counts(make_coordinator, glitch):
    """run -> unavailable -> finished is one valid cycle (was lost before 1.1)."""
    c = await make_coordinator()
    await feed(c, "run", glitch, "finished")
    assert c.total_cycles == 1
    assert c.last_state == "finished"


async def test_unavailable_is_not_stored_as_last_state(make_coordinator):
    c = await make_coordinator()
    await feed(c, "ready", "unavailable")
    assert c.last_state == "ready"
    # A finished cycle after unavailable must not double count.
    await feed(c, "run", "finished", "unavailable", "finished")
    assert c.total_cycles == 1


async def test_restore_drops_stored_unavailable(hass, hass_storage):
    entry = MockConfigEntry(domain=DOMAIN, data=build_data())
    entry.add_to_hass(hass)
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = {
        "version": 1,
        "key": f"{DOMAIN}.{entry.entry_id}",
        "data": {"total_cycles": 0, "cycles": [], "last_state": "unavailable"},
    }
    c = DishwasherDutyCoordinator(hass, entry)
    await c._async_restore()
    assert c.last_state is None


# --------------------------------------------------------------------------
# Debounce
# --------------------------------------------------------------------------
async def test_debounce_suppresses_rapid_second_cycle(make_coordinator, freezer):
    c = await make_coordinator(debounce_seconds=30)
    freezer.move_to("2026-05-15 12:00:00")
    await feed(c, "run", "finished")
    freezer.tick(10)
    await feed(c, "run", "finished")
    assert c.total_cycles == 1  # second one within 30 s -> ignored
    freezer.tick(31)
    await feed(c, "run", "finished")
    assert c.total_cycles == 2


async def test_debounce_off_counts_every_cycle(make_coordinator):
    c = await make_coordinator(debounce_seconds=0)
    await feed(c, "run", "finished", "run", "finished")
    assert c.total_cycles == 2


# --------------------------------------------------------------------------
# cancel_claim / reset_statistics
# --------------------------------------------------------------------------
async def test_cancel_claim_without_open_window_raises(make_coordinator):
    c = await make_coordinator()
    with pytest.raises(ServiceValidationError) as err:
        await c.async_cancel_claim("person.alice")
    assert err.value.translation_key == "no_open_cycle"


async def test_claim_errors_are_translated(make_coordinator):
    c = await make_coordinator()
    with pytest.raises(ServiceValidationError) as err:
        await c.async_claim("person.alice")
    assert err.value.translation_domain == DOMAIN
    assert err.value.translation_key == "no_open_cycle"
    await feed(c, "run", "finished")
    with pytest.raises(ServiceValidationError) as err:
        await c.async_claim("person.dave")
    assert err.value.translation_key == "person_not_authorised"
    assert err.value.translation_placeholders["person"] == "person.dave"


async def test_reset_all(make_coordinator):
    c = await make_coordinator()
    await feed(c, "run", "finished")
    await c.async_claim("person.alice")
    await c.async_reset_statistics(None)
    assert c.total_cycles == 0
    assert c.cycles == []
    assert c.data["claim_open"] is False
    assert c._unsub_timer is None


async def test_reset_person_unclaims_cycles_only_they_claimed(make_coordinator):
    c = await make_coordinator(allow_co_claim=False)
    await feed(c, "run", "finished")
    await c.async_claim("person.alice")
    await c.async_reset_statistics("person.alice")
    cycle = c.cycles[-1]
    assert cycle["claimers"] == []
    assert cycle["credits"] == {}
    assert cycle["status"] == "unclaimed"
    assert cycle["claimed_at"] is None
    assert c.person_stats("person.alice")["credits_total"] == 0
    assert c.get_statistics(None, None, None)["unclaimed_cycles"] == 1


async def test_reset_person_keeps_co_claimers(make_coordinator):
    c = await make_coordinator()
    await feed(c, "run", "finished")
    await c.async_claim_multiple(["person.alice", "person.bob"])
    await c._async_finalize_current()
    await c.async_reset_statistics("Alice")  # slug works too
    cycle = c.cycles[-1]
    assert cycle["claimers"] == ["person.bob"]
    assert cycle["credits"] == {"person.bob": 0.5}
    assert cycle["status"] == "claimed"


async def test_reset_person_in_open_window(make_coordinator):
    c = await make_coordinator()
    await feed(c, "run", "finished")
    await c.async_claim("person.alice")
    await c.async_reset_statistics("person.alice")
    assert c.data["claim_open"] is True
    assert c.data["current_claimers"] == []
    assert c.data["co_claim_window_until"] is None


# --------------------------------------------------------------------------
# Snapshot
# --------------------------------------------------------------------------
async def test_claimers_attributes_share_one_source(make_coordinator):
    c = await make_coordinator()
    await feed(c, "run", "finished")
    await c.async_claim("person.alice")
    assert c.data["current_claimers"] == ["person.alice"]
    assert c.data["current_cycle_claimed_by"] == c.data["current_claimers"]
    # The snapshot is a copy, not the live list.
    c.cycles[-1]["claimers"].append("person.bob")
    assert c.data["current_cycle_claimed_by"] == ["person.alice"]


def test_distribute_credits_floors():
    """floor(100/n) cents each, leftovers to the first claimers."""
    assert distribute_credits(["a", "b", "c"]) == {"a": 0.34, "b": 0.33, "c": 0.33}
    six = distribute_credits([str(i) for i in range(6)])
    assert list(six.values()) == [0.17, 0.17, 0.17, 0.17, 0.16, 0.16]
