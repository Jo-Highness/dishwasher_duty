# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Jo-Highness/dishwasher_duty/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/Jo-Highness/dishwasher_duty/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Jo-Highness/dishwasher_duty/releases/tag/v1.0.0
