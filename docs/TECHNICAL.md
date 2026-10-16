# Dishwasher Duty — Technical Documentation

Architecture of the `dishwasher_duty` custom integration. For end users see
[`user/`](user).

## 1. Purpose

Track who unloads the dishwasher. A source sensor (e.g. Home Connect's *Operation state*)
transitions *running → finished* (Home Connect: `run` → `finished`) at the end of a programme; that opens a claimable cycle.
Eligible `person` entities claim it; the fixed credit of **1.0 per cycle** is shared among
co-claimers. The full history is persisted and exposed as per-person statistics.

## 2. Components

```
custom_components/dishwasher_duty/
├── __init__.py        # async_setup (5 actions: claim, claim_multiple, cancel_claim,
│                      #   get_statistics[response], reset_statistics), entry setup/unload,
│                      #   migration 1.1 -> 1.2, orphaned-entity cleanup
├── manifest.json      # config_flow, iot_class=calculated, after_dependencies=[person]
├── const.py           # keys, defaults, status constants
├── config_flow.py     # two-step config flow (sensor -> settings) + mirrored options flow
├── diagnostics.py     # config-entry diagnostics (persons pseudonymised)
├── coordinator.py     # DishwasherDutyCoordinator: state machine + claim engine
├── entity.py          # CoordinatorEntity base (has_entity_name) + service DeviceInfo
├── sensor.py          # total_cycles + per-person credit sensors
├── binary_sensor.py   # claimable
├── button.py          # per-person claim buttons
├── icons.json         # entity + action icons
├── services.yaml      # action descriptions + selectors
├── strings.json       # base (English) UI strings
└── translations/      # de, en, es, fr, nb, el, ja
```

One config entry == one dishwasher; the entry's `unique_id` is the source sensor's entity id,
so a sensor cannot be added twice (entries from 1.0.x get it in the 1.1 -> 1.2 migration). The
coordinator (`DataUpdateCoordinator[dict]`, `config_entry=entry`, no polling — event driven via
`async_set_updated_data`; `_async_update_data` just returns the snapshot) is stored in
`entry.runtime_data` and owns all state. `_async_setup` (run by the first refresh) restores the
store and starts the listeners; the base class calls `async_shutdown` on unload, which persists
the state.

Entities use `has_entity_name` + `translation_key`; the device is named after the entry title
("Dishwasher Duty" for the first entry), so generated entity ids stay
`sensor.dishwasher_duty_total_cycles`, `sensor.dishwasher_duty_<slug>` etc. Per-person entities
whose person was removed are deleted from the entity registry on setup.

## 3. State machine (cycle detection)

`async_track_state_change_event` on the source sensor feeds `_process_state_locked(new)`:

- States in `IGNORED_STATES` (`unavailable`, `unknown`, …) are dropped and do **not** replace
  `_last_state`. A cycle opens **only** when `_last_state` matches `running_value` and the new
  state matches `finished_value`. Matching is case-insensitive (`casefold`). This counts
  `run → unavailable → finished` once (also across restarts — `_last_state` is persisted) and
  rejects `unavailable → finished` without a run and `finished → finished`.
- On a valid transition `_register_finished_cycle()`:
  - appends a cycle record to `cycles` (so even unclaimed cycles are counted in stats),
  - increments `total_cycles` by exactly 1,
  - sets `claim_open = True`, remembers `current_cycle_id`.
- A new run (`new == running_value`) while a window is open **closes** it: existing claimers are
  finalised, otherwise the cycle stays `unclaimed`. Leaving `finished` to `unavailable`/`ready`
  does **not** close the window (you can still claim after "Ready").
- Optional `debounce_seconds` rejects a second finished transition within the window.

All mutating paths hold a single `asyncio.Lock` (events, claims, the co-claim timer, reset).

## 4. Claim engine

`async_claim_multiple(persons)` (used by `claim`, the buttons and `claim_multiple`):

- Validates each person against the configured list. Persons can be given as entity id, slug or
  display name (`_normalize_person`). Errors are `ServiceValidationError`s with
  `translation_domain`/`translation_key` (see `exceptions` in `strings.json`).
- Idempotent: a person already in `claimers` is ignored (one contribution per person/cycle).
- **Co-claim enabled:** the first claim arms a `co_claim_window`-second timer
  (`async_track_point_in_time`); further people join until it fires, then `_finalize_locked`.
- **Co-claim disabled:** the first claim finalises immediately; later claims are ignored.
- `cancel_claim` removes a person while the window is open; if none remain the window timer is
  cancelled so a fresh first-claim restarts it. Without an open window it raises `no_open_cycle`.
- Timer callbacks and state events run as entry-bound tasks (`entry.async_create_task`), so they
  are cancelled on unload.
- `reset_statistics(person)` removes that person's credits/claims; a finalised cycle without any
  remaining claimer becomes `unclaimed` again.

`distribute_credits(claimers)` splits 1.0 to 2 decimals with exact sum: `base = ⌊100/n⌋` cents
each, the leftover cents go to the earliest claimers (n=3 → 0.34/0.33/0.33 = 1.00).

## 5. Persistence

`homeassistant.helpers.storage.Store` (`dishwasher_duty.<entry_id>`) holds `total_cycles`, the
full `cycles` history (each: `cycle_id`, `finished_timestamp`, `claimers`, `credits`,
`claimed_at`, `status`), `last_state`, and the open-window state (`claim_open`,
`current_cycle_id`, `co_claim_until`). On startup `_async_setup` restores everything and, if a
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

## 7. Actions and multiple entries

Actions are registered once in `async_setup` (`CONFIG_SCHEMA = config_entry_only_config_schema`)
and resolve the entry at call time. Every action accepts an optional `config_entry_id`. Without
it, `claim`/`claim_multiple`/`cancel_claim` go to the entries that know the person,
`reset_statistics` affects all loaded entries, and `get_statistics` raises `multiple_entries` when
more than one entry is loaded.

## 8. Repairs and diagnostics

If the source sensor has no state **and** is not in the entity registry, a non-fixable repair
issue `source_sensor_missing_<entry_id>` is created; it is deleted as soon as the sensor reports a
state again or the entry is removed. A sensor that is registered but not yet loaded (e.g. while
Home Connect starts) does not raise the issue. `diagnostics.py` returns config, source-sensor
state/options and the last 10 cycles with person ids replaced by `person_<n>`.

## 9. Validation

`config_flow` requires at least one person, non-empty running/finished values and that they
differ (case-insensitively). The value fields are `SelectSelector`s filled from the source
sensor's `options` attribute with `custom_value` allowed. `manifest.json`:
`config_flow: true`, `iot_class: "calculated"`, `integration_type: "service"`,
`after_dependencies: ["person"]`. Norwegian uses the canonical HA code `nb`.
