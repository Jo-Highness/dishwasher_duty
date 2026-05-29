"""Full setup/unload and end-to-end service test."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dishwasher_duty.const import (
    DOMAIN,
    SERVICE_CANCEL_CLAIM,
    SERVICE_CLAIM,
    SERVICE_CLAIM_MULTIPLE,
    SERVICE_GET_STATISTICS,
    SERVICE_RESET_STATISTICS,
)

from .conftest import SENSOR, build_data


async def test_setup_creates_entities_and_services(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=build_data(allow_co_claim=False))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.dishwasher_duty_total_cycles") is not None
    assert hass.states.get("binary_sensor.dishwasher_duty_claimable") is not None
    assert hass.states.get("sensor.dishwasher_duty_alice") is not None
    assert hass.states.get("button.dishwasher_duty_claim_alice") is not None

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
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_claim_service_end_to_end(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=build_data(allow_co_claim=False))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Drive the real source sensor through Running -> Finished.
    hass.states.async_set(SENSOR, "Run")
    await hass.async_block_till_done()
    hass.states.async_set(SENSOR, "Finished")
    await hass.async_block_till_done()
    assert coordinator.total_cycles == 1

    # Claim via the service (co-claim disabled -> immediate finalise).
    await hass.services.async_call(
        DOMAIN, SERVICE_CLAIM, {"person": "person.alice"}, blocking=True
    )
    await hass.async_block_till_done()

    assert coordinator.person_stats("person.alice")["credits_total"] == 1.0

    # get_statistics returns a response.
    response = await hass.services.async_call(
        DOMAIN, SERVICE_GET_STATISTICS, {}, blocking=True, return_response=True
    )
    assert response["total_cycles"] == 1
    assert response["unclaimed_cycles"] == 0

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
