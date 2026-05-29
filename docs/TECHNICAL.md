# Dishwasher Duty — Technical Documentation

Architecture of the `dishwasher_duty` custom integration. For end users see
[`user/`](user).

## 1. Purpose

Track who unloads the dishwasher. A source sensor (e.g. Home Connect's *Operation state*)
transitions `Running → Finished` at the end of a programme; that opens a claimable cycle.
Eligible `person` entities claim it; the fixed credit of **1.0 per cycle** is shared among
co-claimers. The full history is persisted and exposed as per-person statistics.

## 2. Components

```
custom_components/dishwasher_duty/
├── __init__.py        # setup/unload + 5 services (claim, claim_multiple,
│                      #   cancel_claim, get_statistics[response], reset_statistics)
├── manifest.json      # config_flow, iot_class=calculated, after_dependencies=[person]
├── const.py           # keys, defaults, status constants
├── config_flow.py     # single-step config flow + mirrored options flow
├── coordinator.py     # DishwasherDutyCoordinator: state machine + claim engine
├── entity.py          # CoordinatorEntity base + DeviceInfo
├── sensor.py          # total_cycles + per-person credit sensors
├── binary_sensor.py   # claimable
├── button.py          # per-person claim buttons
├── services.yaml      # service descriptions + selectors
├── strings.json       # base (English) UI strings
└── translations/      # de, en, es, fr, nb, el, ja
```

One config entry == one dishwasher. The coordinator (`DataUpdateCoordinator[dict]`, no polling
— event driven via `async_set_updated_data`) owns all state.

## 3. State machine (cycle detection)

`async_track_state_change_event` on the source sensor feeds `_process_state_locked(new)`:

- The **raw** previous state is kept in `_last_state`. A cycle opens **only** when
  `_last_state == running_value AND new == finished_value`. This deliberately rejects
  `unavailable → Finished`, `unknown → Finished`, `Finished → Finished` (sensor glitches,
  restarts, debouncing of a bouncing sensor).
- On a valid transition `_register_finished_cycle()`:
  - appends a cycle record to `cycles` (so even unclaimed cycles are counted in stats),
  - increments `total_cycles` by exactly 1,
  - sets `claim_open = True`, remembers `current_cycle_id`.
- A new run (`new == running_value`) while a window is open **closes** it: existing claimers are
  finalised, otherwise the cycle stays `unclaimed`. Leaving `Finished` to `unavailable`/`Ready`
  does **not** close the window (you can still claim after "Ready").
- Optional `debounce_seconds` rejects a second finished transition within the window.

All mutating paths hold a single `asyncio.Lock` (events, claims, the co-claim timer, reset).

## 4. Claim engine

`async_claim_multiple(persons)` (used by `claim`, the buttons and `claim_multiple`):

- Validates each person against the configured list (`ServiceValidationError` otherwise).
- Idempotent: a person already in `claimers` is ignored (one contribution per person/cycle).
- **Co-claim enabled:** the first claim arms a `co_claim_window`-second timer
  (`async_track_point_in_time`); further people join until it fires, then `_finalize_locked`.
- **Co-claim disabled:** the first claim finalises immediately; later claims are ignored.
- `cancel_claim` removes a person while the window is open; if none remain the window timer is
  cancelled so a fresh first-claim restarts it.

`distribute_credits(claimers)` splits 1.0 to 2 decimals with exact sum: `base = ⌊100/n⌋` cents
each, the leftover cents go to the earliest claimers (n=3 → 0.34/0.33/0.33 = 1.00).

## 5. Persistence

`homeassistant.helpers.storage.Store` (`dishwasher_duty.<entry_id>`) holds `total_cycles`, the
full `cycles` history (each: `cycle_id`, `finished_timestamp`, `claimers`, `credits`,
`claimed_at`, `status`), `last_state`, and the open-window state (`claim_open`,
`current_cycle_id`, `co_claim_until`). On startup `async_setup` restores everything and, if a
co-claim window was open: finalises it if `co_claim_until` already passed, otherwise re-arms the
timer for the remaining time.

## 6. Statistics & Recorder

Per-person sensors expose `credits_total` as state (`state_class total_increasing`, so HA's
long-term statistics can chart credits over time) plus attributes `credits_today /
credits_this_week / credits_this_month / credits_this_year / claims_count_total / last_claim`.
Period sums are derived from each cycle's `claimed_at` converted to the HA local timezone, with
week = ISO week (Monday). `async_track_time_change` at 00:00 local pushes a refresh so the
period attributes roll over; a midnight rollover never touches `credits_total`.

`get_statistics(start, end, person?)` (a `SupportsResponse.ONLY` service) returns
`total_cycles`, `unclaimed_cycles`, `per_person` (participations + credit sum) and a
chronological `timeline` for the range.

## 7. Validation

`config_flow` requires at least one person and a non-empty finished value. `manifest.json`:
`config_flow: true`, `iot_class: "calculated"`, `integration_type: "service"`,
`after_dependencies: ["person"]`. Norwegian uses the canonical HA code `nb`.
