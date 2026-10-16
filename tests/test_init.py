"""Setup/unload, services, multi-entry, restart, repairs and diagnostics."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.dishwasher_duty.const import (
    CONF_PERSONS,
    DOMAIN,
    SERVICE_CANCEL_CLAIM,
    SERVICE_CLAIM,
    SERVICE_CLAIM_MULTIPLE,
    SERVICE_GET_STATISTICS,
    SERVICE_RESET_STATISTICS,
)
from custom_components.dishwasher_duty.coordinator import DishwasherDutyCoordinator
from custom_components.dishwasher_duty.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import PERSONS, SENSOR, build_data, setup_integration

OTHER_SENSOR = "sensor.kitchen_dishwasher_operation_state"


async def _run_cycle(hass, sensor: str = SENSOR) -> None:
    hass.states.async_set(sensor, "run")
    await hass.async_block_till_done()
    hass.states.async_set(sensor, "finished")
    await hass.async_block_till_done()


# --------------------------------------------------------------------------
# Setup / entities
# --------------------------------------------------------------------------
async def test_setup_creates_entities_and_services(hass):
    entry = await setup_integration(hass, allow_co_claim=False)
    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, DishwasherDutyCoordinator)

    # Entity ids are unchanged from 1.0.x (now derived from translated names).
    total = hass.states.get("sensor.dishwasher_duty_total_cycles")
    assert total is not None
    assert total.attributes["friendly_name"] == "Dishwasher Duty Total cycles"
    claimable = hass.states.get("binary_sensor.dishwasher_duty_claimable")
    assert claimable.attributes["friendly_name"] == "Dishwasher Duty Claimable"
    alice = hass.states.get("sensor.dishwasher_duty_alice")
    assert alice.attributes["friendly_name"] == "Dishwasher Duty Alice"
    assert alice.attributes["unit_of_measurement"] == "credits"
    button = hass.states.get("button.dishwasher_duty_claim_alice")
    assert button.attributes["friendly_name"] == "Dishwasher Duty Claim Alice"

    registry = er.async_get(hass)
    assert (
        registry.async_get("sensor.dishwasher_duty_alice").unique_id
        == f"{entry.entry_id}_person_alice"
    )
    assert (
        registry.async_get("button.dishwasher_duty_claim_alice").unique_id
        == f"{entry.entry_id}_claim_alice"
    )

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.entry_type is dr.DeviceEntryType.SERVICE
    assert device.name == "Dishwasher Duty"

    for service in (
        SERVICE_CLAIM,
        SERVICE_CLAIM_MULTIPLE,
        SERVICE_CANCEL_CLAIM,
        SERVICE_GET_STATISTICS,
        SERVICE_RESET_STATISTICS,
    ):
        assert hass.services.has_service(DOMAIN, service)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    # Actions are registered in async_setup and stay available.
    assert hass.services.has_service(DOMAIN, SERVICE_CLAIM)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, SERVICE_CLAIM, {"person": "person.alice"}, blocking=True
        )
    assert err.value.translation_key == "not_configured"


async def test_existing_entity_ids_are_kept(hass):
    """Registry entries created by 1.0.x keep their entity ids."""
    data = build_data()
    entry = MockConfigEntry(domain=DOMAIN, title="Dishwasher Duty", data=data, unique_id=SENSOR)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_person_alice",
        config_entry=entry,
        suggested_object_id="my_custom_alice",
    )
    await setup_integration(hass, entry=entry)
    assert hass.states.get("sensor.my_custom_alice") is not None


async def test_claim_service_end_to_end(hass):
    entry = await setup_integration(hass, allow_co_claim=False)
    coordinator = entry.runtime_data

    # Drive the real source sensor through run -> finished (lowercase, HA 2025.1+).
    await _run_cycle(hass)
    assert coordinator.total_cycles == 1
    assert hass.states.get("binary_sensor.dishwasher_duty_claimable").state == "on"

    await hass.services.async_call(DOMAIN, SERVICE_CLAIM, {"person": "person.alice"}, blocking=True)
    await hass.async_block_till_done()

    assert coordinator.person_stats("person.alice")["credits_total"] == 1.0
    assert hass.states.get("sensor.dishwasher_duty_alice").state == "1.0"
    assert hass.states.get("binary_sensor.dishwasher_duty_claimable").state == "off"

    response = await hass.services.async_call(
        DOMAIN, SERVICE_GET_STATISTICS, {}, blocking=True, return_response=True
    )
    assert response["total_cycles"] == 1
    assert response["unclaimed_cycles"] == 0


async def test_button_press_claims(hass):
    entry = await setup_integration(hass, allow_co_claim=False)
    await _run_cycle(hass)
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.dishwasher_duty_claim_bob"}, blocking=True
    )
    assert entry.runtime_data.person_stats("person.bob")["credits_total"] == 1.0


async def test_cancel_claim_service_without_open_window(hass):
    await setup_integration(hass)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, SERVICE_CANCEL_CLAIM, {"person": "person.alice"}, blocking=True
        )
    assert err.value.translation_key == "no_open_cycle"


async def test_cancel_claim_service_unknown_person(hass):
    await setup_integration(hass)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, SERVICE_CANCEL_CLAIM, {"person": "person.dave"}, blocking=True
        )
    assert err.value.translation_key == "unknown_person"


async def test_reset_statistics_service(hass):
    entry = await setup_integration(hass, allow_co_claim=False)
    await _run_cycle(hass)
    await hass.services.async_call(DOMAIN, SERVICE_CLAIM, {"person": "alice"}, blocking=True)
    await hass.services.async_call(
        DOMAIN, SERVICE_RESET_STATISTICS, {"person": "person.alice"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.dishwasher_duty_alice").state == "0.0"
    assert entry.runtime_data.total_cycles == 1
    await hass.services.async_call(DOMAIN, SERVICE_RESET_STATISTICS, {}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.dishwasher_duty_total_cycles").state == "0"


# --------------------------------------------------------------------------
# Source sensor going unavailable mid-run (real state events)
# --------------------------------------------------------------------------
async def test_unavailable_mid_run_end_to_end(hass):
    entry = await setup_integration(hass)
    for state in ("run", "unavailable", "finished"):
        hass.states.async_set(SENSOR, state)
        await hass.async_block_till_done()
    assert entry.runtime_data.total_cycles == 1


async def test_last_state_survives_restart_with_unavailable(hass):
    """run -> (HA restart, sensor unavailable) -> finished still counts."""
    entry = await setup_integration(hass)
    hass.states.async_set(SENSOR, "run")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    hass.states.async_set(SENSOR, "unavailable")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(SENSOR, "finished")
    await hass.async_block_till_done()
    assert entry.runtime_data.total_cycles == 1


# --------------------------------------------------------------------------
# Co-claim timer
# --------------------------------------------------------------------------
async def test_co_claim_window_expires(hass, freezer):
    entry = await setup_integration(hass, co_claim_window=90)
    coordinator = entry.runtime_data
    await _run_cycle(hass)
    await hass.services.async_call(DOMAIN, SERVICE_CLAIM, {"person": "person.alice"}, blocking=True)
    freezer.tick(30)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    await hass.services.async_call(DOMAIN, SERVICE_CLAIM, {"person": "person.bob"}, blocking=True)
    assert coordinator.claim_open is True

    freezer.tick(61)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert coordinator.claim_open is False
    assert coordinator.cycles[-1]["credits"] == {"person.alice": 0.5, "person.bob": 0.5}
    assert hass.states.get("binary_sensor.dishwasher_duty_claimable").state == "off"


def _stored(entry_id: str, until: str, claimers: list[str]) -> dict:
    return {
        "version": 1,
        "key": f"{DOMAIN}.{entry_id}",
        "data": {
            "total_cycles": 1,
            "cycles": [
                {
                    "cycle_id": "c1",
                    "finished_timestamp": "2026-05-15T10:00:00+00:00",
                    "claimers": claimers,
                    "credits": {},
                    "claimed_at": None,
                    "status": "unclaimed",
                }
            ],
            "last_state": "Finished",
            "claim_open": True,
            "current_cycle_id": "c1",
            "co_claim_until": until,
        },
    }


async def test_restart_with_expired_window_finalises(hass, hass_storage):
    entry = MockConfigEntry(
        domain=DOMAIN, title="Dishwasher Duty", data=build_data(), unique_id=SENSOR
    )
    entry.add_to_hass(hass)
    past = (dt_util.utcnow() - timedelta(minutes=5)).isoformat()
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = _stored(entry.entry_id, past, ["person.alice"])

    await setup_integration(hass, entry=entry)
    coordinator = entry.runtime_data
    assert coordinator.claim_open is False
    assert coordinator.cycles[-1]["credits"] == {"person.alice": 1.0}
    assert hass.states.get("sensor.dishwasher_duty_alice").state == "1.0"


async def test_restart_with_running_window_rearms_timer(hass, hass_storage, freezer):
    entry = MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR)
    entry.add_to_hass(hass)
    future = (dt_util.utcnow() + timedelta(seconds=40)).isoformat()
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = _stored(entry.entry_id, future, ["person.bob"])

    await setup_integration(hass, entry=entry)
    coordinator = entry.runtime_data
    assert coordinator.claim_open is True

    freezer.tick(41)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.claim_open is False
    assert coordinator.cycles[-1]["credits"] == {"person.bob": 1.0}


# --------------------------------------------------------------------------
# Options reload + orphan cleanup
# --------------------------------------------------------------------------
async def test_options_change_reloads_and_removes_orphans(hass):
    entry = await setup_integration(hass)
    old = entry.runtime_data
    registry = er.async_get(hass)
    assert registry.async_get("sensor.dishwasher_duty_carol") is not None

    hass.config_entries.async_update_entry(
        entry, options={**build_data(), CONF_PERSONS: ["person.alice", "person.bob"]}
    )
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not old
    assert entry.runtime_data.persons == ["person.alice", "person.bob"]
    assert registry.async_get("sensor.dishwasher_duty_carol") is None
    assert registry.async_get("button.dishwasher_duty_claim_carol") is None
    assert hass.states.get("sensor.dishwasher_duty_carol") is None
    assert registry.async_get("sensor.dishwasher_duty_alice") is not None


# --------------------------------------------------------------------------
# Multiple dishwashers
# --------------------------------------------------------------------------
async def _two_entries(hass):
    first = await setup_integration(hass, allow_co_claim=False)
    data = build_data(
        source_sensor=OTHER_SENSOR, persons=["person.alice", "person.dave"], allow_co_claim=False
    )
    second = MockConfigEntry(
        domain=DOMAIN,
        title="Dishwasher Duty (Kitchen)",
        data=data,
        unique_id=OTHER_SENSOR,
        version=1,
        minor_version=2,
    )
    await setup_integration(hass, entry=second)
    return first, second


async def test_multiple_entries_have_separate_entities(hass):
    first, second = await _two_entries(hass)
    assert hass.states.get("sensor.dishwasher_duty_total_cycles") is not None
    assert hass.states.get("sensor.dishwasher_duty_kitchen_total_cycles") is not None
    assert hass.states.get("button.dishwasher_duty_kitchen_claim_dave") is not None
    assert hass.states.get("sensor.dishwasher_duty_kitchen_alice") is not None

    await _run_cycle(hass, OTHER_SENSOR)
    assert first.runtime_data.total_cycles == 0
    assert second.runtime_data.total_cycles == 1

    # dave only exists on the second dishwasher -> routed there.
    await hass.services.async_call(DOMAIN, SERVICE_CLAIM, {"person": "person.dave"}, blocking=True)
    assert second.runtime_data.person_stats("person.dave")["credits_total"] == 1.0


async def test_multiple_entries_config_entry_id(hass):
    first, second = await _two_entries(hass)
    await _run_cycle(hass)
    await _run_cycle(hass, OTHER_SENSOR)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLAIM,
        {"person": "person.alice", "config_entry_id": second.entry_id},
        blocking=True,
    )
    assert second.runtime_data.person_stats("person.alice")["credits_total"] == 1.0
    assert first.runtime_data.person_stats("person.alice")["credits_total"] == 0.0

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, SERVICE_GET_STATISTICS, {}, blocking=True, return_response=True
        )
    assert err.value.translation_key == "multiple_entries"

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_STATISTICS,
        {"config_entry_id": second.entry_id},
        blocking=True,
        return_response=True,
    )
    assert response["per_person"] == {"person.alice": {"participations": 1, "credits": 1.0}}

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_STATISTICS,
            {"config_entry_id": "nope"},
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == "entry_not_found"


# --------------------------------------------------------------------------
# Migration
# --------------------------------------------------------------------------
async def test_migration_sets_unique_id(hass):
    entry = MockConfigEntry(domain=DOMAIN, title="Dishwasher Duty", data=build_data(), version=1)
    await setup_integration(hass, entry=entry)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id == SENSOR
    assert entry.minor_version == 2
    assert hass.states.get("sensor.dishwasher_duty_total_cycles") is not None


async def test_migration_skips_conflicting_unique_id(hass):
    MockConfigEntry(domain=DOMAIN, data=build_data(), unique_id=SENSOR).add_to_hass(hass)
    entry = MockConfigEntry(domain=DOMAIN, title="Copy", data=build_data(), version=1)
    await setup_integration(hass, entry=entry)
    assert entry.unique_id is None
    assert entry.minor_version == 2


# --------------------------------------------------------------------------
# Repairs
# --------------------------------------------------------------------------
async def test_repair_issue_when_source_sensor_missing(hass):
    entry = await setup_integration(hass, sensor_state=None)
    issue_id = f"source_sensor_missing_{entry.entry_id}"
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, issue_id) is not None

    hass.states.async_set(SENSOR, "ready")
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, issue_id) is None


async def test_no_repair_issue_for_registered_but_unloaded_sensor(hass):
    er.async_get(hass).async_get_or_create(
        "sensor", "home_connect", "op_state", suggested_object_id="dishwasher_operation_state"
    )
    entry = await setup_integration(hass, sensor_state=None)
    issue_id = f"source_sensor_missing_{entry.entry_id}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_repair_issue_removed_with_entry(hass):
    entry = await setup_integration(hass, sensor_state=None)
    issue_id = f"source_sensor_missing_{entry.entry_id}"
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------
async def test_diagnostics_redacts_persons(hass):
    entry = await setup_integration(hass, allow_co_claim=False)
    await _run_cycle(hass)
    await hass.services.async_call(DOMAIN, SERVICE_CLAIM, {"person": "person.bob"}, blocking=True)

    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = repr(diag)
    for person in PERSONS:
        assert person not in text
    assert diag["entry"]["data"][CONF_PERSONS] == "**REDACTED**"
    assert diag["entry"]["person_count"] == 3
    assert diag["state"]["total_cycles"] == 1
    assert diag["recent_cycles"][-1]["credits"] == {"person_2": 1.0}
    assert diag["source_sensor"]["state"] == "finished"
