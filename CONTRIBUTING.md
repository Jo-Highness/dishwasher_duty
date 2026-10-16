# Contributing to Dishwasher Duty

Thanks for your interest in improving Dishwasher Duty! This is a custom
[Home Assistant](https://www.home-assistant.io/) integration distributed via
[HACS](https://hacs.xyz/). Contributions of all kinds are welcome.

## Repository layout

```
.
├── custom_components/dishwasher_duty/   # The integration source code
│   ├── __init__.py                      # Setup / unload
│   ├── manifest.json                    # Integration manifest
│   ├── config_flow.py                   # UI config & options flow
│   ├── coordinator.py                   # Cycle/credit state machine
│   ├── const.py                         # Constants
│   ├── binary_sensor.py / sensor.py / button.py
│   ├── entity.py
│   ├── services.yaml                    # Service definitions
│   ├── strings.json / translations/     # UI strings (i18n)
│   └── brand/                           # Local brand images (HA 2026.3+)
├── tests/                               # pytest test suite
├── CHANGELOG.md
└── README.md / README.de.md
```

## Development setup

Requires Python 3.13 (matching current Home Assistant).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install ruff -r requirements_test.txt
```

## Linting and formatting

This project uses [ruff](https://docs.astral.sh/ruff/) for both linting and
formatting. Run before committing:

```bash
ruff check .
ruff format --check .
```

Auto-fix where possible:

```bash
ruff check --fix .
ruff format .
```

## Running tests

```bash
pytest --cov=custom_components.dishwasher_duty --cov-report=term-missing
```

## Commit messages

Please use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add per-person weekly credit sensor
fix: ignore unavailable source-sensor states
docs: clarify finished/running value configuration
```

Common types: `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `refactor`.
These types drive automatic release notes and version bumps.

## Pull request process

1. Fork the repository and create a feature branch off `main`.
2. Make your change, keeping it focused and small.
3. Ensure `ruff check .`, `ruff format --check .`, and `pytest` all pass.
4. Update `CHANGELOG.md` (under `## [Unreleased]`) and the documentation
   (`README.md` and `README.de.md`) when behaviour changes.
5. Open a pull request against `main` and fill in the PR template.

A maintainer (@Jo-Highness) will review your PR. Thanks for contributing!
