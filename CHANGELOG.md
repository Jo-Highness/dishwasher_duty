# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-10-16

> **Note:** the minimum Home Assistant version is now **2025.2.0**. Entity IDs, unique IDs,
> action names/fields and the stored history are unchanged.

### Added
- Support for **several dishwashers**: each source sensor can be added once (unique ID per
  source sensor, duplicate setups are aborted). Existing entries get their unique ID through a
  config-entry migration (1.1 → 1.2).
- Optional `config_entry_id` field for all actions to select a dishwasher.
- The "running"/"finished" values are now drop-downs filled from the source sensor's list of
  states (`options` attribute); custom values are still allowed.
- Help texts (`data_description`) for every setup field, in all seven languages.
- Repair issue when the source sensor no longer exists.
- Diagnostics download (person entity IDs are pseudonymised).
- Translated entity names and action errors; `icons.json`.

### Changed
- State values are compared **case-insensitively**; new defaults are the lowercase Home
  Connect values `run` / `finished` (reported since HA 2025.1). Existing entries with
  `Run` / `Finished` keep working.
- Setup and options are split into two steps (source sensor → settings); the options flow stores
  exactly what was submitted.
- Entities use `has_entity_name` with translation keys; the device is a service device named
  after the entry. Generated entity IDs are unchanged. The cycle counter's friendly name is now
  "… Total cycles".
- `get_statistics` raises an error instead of silently using the first entry when several
  dishwashers are set up and no `config_entry_id` is given.
- Modernised internals: `entry.runtime_data`, actions registered in `async_setup`,
  `Platform` enum, `AddConfigEntryEntitiesCallback`, entry-bound tasks, coordinator
  `_async_setup` / `_async_update_data`, options flow without custom `__init__`.
- Minimum Home Assistant version raised to **2025.2.0**.

### Fixed
- A programme that went *run → unavailable → finished* (e.g. Wi-Fi dropout or a Home Assistant
  restart) was not counted, because `unavailable` replaced the remembered "running" state.
  `unavailable` / `unknown` are now ignored.
- `reset_statistics` with a person left cycles they claimed alone as "claimed" without any
  claimer; such cycles are now unclaimed again.
- `cancel_claim` without an open cycle did nothing silently; it now returns an error.
- Sensors and buttons of persons removed from the configuration stayed behind as orphaned
  entities; they are now removed.
- `current_cycle_claimed_by` could differ from `current_claimers`; both now come from the same
  snapshot.

### Documentation
- README rewritten with a quick start (including a test via Developer tools), correct state
  values (`run`/`finished`), the actual credit rounding (rounded down, leftovers to the first
  claimers), the new `unavailable` behaviour, modern automation syntax and all screenshots.
- README.de is now a complete German version instead of German plus an English summary.
- Actions accept entity ID, slug **or display name** – now documented.

### CI
- Tests install pinned dependencies from `requirements_test.txt` and report coverage;
  duplicate ruff run removed; Dependabot watches pip dependencies; ruff targets Python 3.13.

## [1.0.3] - 2026-10-09

> **Note:** this patch release raises the minimum Home Assistant version to **2024.11.0** (see Fixed). Older versions could not set up the integration anyway.

### Fixed

- `hacs.json` declared Home Assistant 2024.1.0 as minimum, but the integration uses
  `ConfigFlowResult` (2024.4) and `DataUpdateCoordinator(config_entry=...)` (2024.11) and
  fails to set up on older versions. Minimum raised to **2024.11.0** (README badge updated).
- The coordinator's `async_shutdown` now also runs the base-class shutdown.

## [1.0.2] - 2026-08-21

### Added
- Continuous Integration: `Validate` workflow (HACS + hassfest) and `Test`
  workflow (ruff lint + format check, pytest).
- `ruff` configuration for linting and formatting.
- Config-flow test to guard the setup UI.
- Repository meta files: `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, issue templates, pull request template,
  Dependabot config, and Release Drafter config/workflow.

### Changed
- Sorted `manifest.json` keys to satisfy hassfest.
- Added README screenshots (config flow, entities card) from a demo instance.

### Fixed
- The `claim` / `cancel_claim` / `reset_statistics` services now accept a
  person's **display name** and a case-insensitive **slug**, as the service
  fields document ("Name (or slug)"). Previously only the exact `person.<id>`
  entity id or its exact-case slug matched, so calling `claim` with a name like
  `Mia` failed with "not an authorised person" (HTTP 500). Covered by tests.

## [1.0.1] - 2026-05-31

### Added
- Ship local brand images via the `brand/` directory (served through the
  Home Assistant 2026.3+ brand proxy API), so no `home-assistant/brands`
  pull request is required.
- Integration icon (SVG plus 256/512 PNG) embedded in the README.

## [1.0.0] - 2026-05-29

### Added
- Initial HACS custom integration "Dishwasher Duty": track who unloads the
  dishwasher, award credits, and expose statistics.
- Test suite and documentation.

[Unreleased]: https://github.com/Jo-Highness/dishwasher_duty/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Jo-Highness/dishwasher_duty/compare/v1.0.3...v1.1.0
[1.0.3]: https://github.com/Jo-Highness/dishwasher_duty/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/Jo-Highness/dishwasher_duty/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Jo-Highness/dishwasher_duty/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Jo-Highness/dishwasher_duty/releases/tag/v1.0.0
