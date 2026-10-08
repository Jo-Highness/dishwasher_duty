> 🇬🇧 English (this page) · 🇩🇪 [Deutsch](README.de.md)

<p align="center">
  <img src="icon.png" alt="Dishwasher Duty" width="160" height="160">
</p>

# Dishwasher Duty

**Track who unloads the dishwasher — award fair (optionally shared) credit and keep detailed per-person statistics.**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/validate.yml/badge.svg)](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/validate.yml)
[![Tests](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/test.yml/badge.svg)](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Jo-Highness/dishwasher_duty)](https://github.com/Jo-Highness/dishwasher_duty/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11%2B-41BDF5.svg)](https://www.home-assistant.io/)

---

## Why this exists

Nobody remembers whose turn it was to empty the dishwasher — and "I did it last time" is impossible
to prove. **Dishwasher Duty** settles the argument with data. It watches a **source sensor** (for
example the *Operation state* sensor of the **Home Connect** integration) for the moment the machine
finishes a cycle. That opens a **claimable cycle**: whoever unloaded it taps their button (or calls a
service) and earns the credit. If two or three people empty it together, the **1.0 credit per cycle**
is split fairly among them. Over time you get per-person statistics (total, today, week, month, year)
and a running total-cycles counter — perfect for a family chore leaderboard.

## Features

- **Robust cycle detection:** only a genuine `Running → Finished` transition counts (prevents
  double-counting on `unavailable → Finished`, glitches, restarts).
- **Co-claiming:** a configurable time window (default 90 s) during which additional people can join
  the same cycle; the credit is shared fairly (1 person = 1.0; 2 = 0.5 each; 3 = 0.34/0.33/0.33 →
  always sums to 1.0).
- **Persistence:** the full cycle history survives restarts (including an open claim window with its
  remaining time).
- **Statistics:** accumulated credits per person plus today/week/month/year; Recorder /
  long-term-statistics compatible for history charts.
- **Services & buttons** for convenient claiming, correcting and reporting.
- Translated into **German, English, Spanish, French, Greek, Japanese, Norwegian Bokmål**.

## Screenshots

> Captured from a demo Home Assistant with fictional data.

| Setup (config flow) | Entities card in use |
|:---:|:---:|
| ![The UI setup form](images/config-flow.png) | ![Claimable, total cycles and per-person credits](images/dashboard.png) |

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Jo-Highness&repository=dishwasher_duty&category=integration)

1. Click the button above, or in HACS go to ⋮ → *Custom repositories* and add this repository with
   category **Integration**.
2. Download *Dishwasher Duty* and restart Home Assistant.
3. Go to *Settings → Devices & Services → Add Integration → "Dishwasher Duty"*.

### Manual

Copy the folder `custom_components/dishwasher_duty/` into `<config>/custom_components/` and restart
Home Assistant. Then add the integration from *Settings → Devices & Services*.

## Configuration

All settings are chosen in the config flow and can be changed later via the integration's **Options**.

| Field | Meaning |
|---|---|
| **Source sensor** (`source_sensor`) | A `sensor` entity, e.g. `sensor.dishwasher_operation_state` (Home Connect) |
| **Finished value** (`finished_value`) | State value meaning "finished" (default `Finished` — **check your sensor!**) |
| **Running value** (`running_value`) | State value meaning "running" (default `Run`) |
| **Persons** (`persons`) | Multi-select of one or more `person` entities |
| **Co-claiming** (`allow_co_claim`) | On/off (default on) |
| **Co-claim window** (`co_claim_window`) | Seconds, 5–600 (default 90) |
| **Debounce** (`debounce_seconds`) | Seconds, 0–120 (default 0 = off) |

> **Important:** the "finished"/"running" value depends on your device and HA version (e.g.
> `Finished`/`Run`, or lowercased `finished`/`run`). Check in *Developer Tools → States* which state
> your sensor actually reports, and enter that value.

## Entities

All entities live under a single device named **Dishwasher Duty**.

| Entity | Meaning |
|---|---|
| `binary_sensor.dishwasher_duty_claimable` | `on` while the current cycle can still be claimed |
| `sensor.dishwasher_duty_total_cycles` | Total number of finished cycles (`total_increasing`) |
| `sensor.dishwasher_duty_<person>` | Accumulated credits per person, unit `credits` (`total_increasing`, + period attributes) |
| `button.dishwasher_duty_claim_<person>` | "I unloaded it" button, one per person |

## Services

| Service | Description |
|---|---|
| `dishwasher_duty.claim` | `person` — claim the current cycle |
| `dishwasher_duty.claim_multiple` | `persons` — claim for several people at once (credit shared equally) |
| `dishwasher_duty.cancel_claim` | `person` — withdraw your own claim while the window is open |
| `dishwasher_duty.get_statistics` | `start`, `end`, `person?` — statistics as a **service response** |
| `dishwasher_duty.reset_statistics` | `person?` — reset history (⚠️ deletes data) |

**Statistics example (with response):**

```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```

`stats` then contains `total_cycles`, `unclaimed_cycles`, `per_person` (participations + sum of
credits) and a chronological `timeline`.

## Automation examples

**1. Remind the household when a cycle is waiting to be claimed**

```yaml
automation:
  - alias: "Dishwasher finished — who's unloading?"
    trigger:
      - platform: state
        entity_id: binary_sensor.dishwasher_duty_claimable
        to: "on"
    action:
      - service: notify.family
        data:
          title: "Dishwasher done 🍽️"
          message: "It's clean! Tap your button in the app once you've unloaded it."
```

**2. Nudge again if nobody has claimed after 30 minutes**

```yaml
automation:
  - alias: "Dishwasher still not claimed"
    trigger:
      - platform: state
        entity_id: binary_sensor.dishwasher_duty_claimable
        to: "on"
        for:
          minutes: 30
    action:
      - service: notify.family
        data:
          message: "The dishwasher is still full 👀 — claim it when you empty it."
```

**Example dashboard**

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Dishwasher
    entities:
      - entity: binary_sensor.dishwasher_duty_claimable
        name: Ready to unload?
      - entity: sensor.dishwasher_duty_total_cycles
        name: Total cycles
  - type: horizontal-stack
    cards:
      - type: button
        name: Luke did it
        entity: button.dishwasher_duty_claim_luke
        tap_action: { action: toggle }
      - type: button
        name: Leo did it
        entity: button.dishwasher_duty_claim_leo
  - type: history-graph
    title: Credits
    entities:
      - sensor.dishwasher_duty_luke
      - sensor.dishwasher_duty_leo
```

## How credit is split (defaults)

- **One credit per cycle = 1.0.** For n claimers: `round(100/n)` cents each, remaining cents go to
  the first claimers → sum is exactly 1.00.
- **Credit timing:** credits are attributed to the moment of the claim (`claimed_at`).
- **The window closes** on the next `Running` (not on `unavailable`/`Ready`), so you can still claim
  after "Ready".
- **Person slug** = the `object_id` of the `person` entity (`person.luke` → `…_luke`).

## Troubleshooting / FAQ

- **Nothing happens when the dishwasher finishes.** The most common cause is a wrong **finished
  value**. Open *Developer Tools → States*, look up your source sensor, run a cycle, and note the
  exact state it shows when done. Enter that value in the integration's Options.
- **`unavailable`/`unknown` are never counted** as a running or finished phase, so a briefly
  unavailable sensor won't create a phantom cycle.
- **A restart won't lose an open window.** After a HA restart, an open claim window is restored
  including its remaining time.
- **Pressing a button twice does nothing extra.** Claiming is idempotent — one contribution per
  person per cycle.
- **My total changed at midnight.** It didn't: a day/week/month/year rollover only resets the
  period attributes (today/week/…), never the running total.

**Enable debug logging** to see the cycle detection and claim logic in your log:

```yaml
logger:
  logs:
    custom_components.dishwasher_duty: debug
```

## Further documentation

- Technical docs (EN): [`docs/TECHNICAL.md`](docs/TECHNICAL.md)
- User docs: [`docs/user/`](docs/user) (de, en, es, fr, nb, el, ja)

## Contributing

Contributions are welcome! Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and open an issue or pull
request on the [issue tracker](https://github.com/Jo-Highness/dishwasher_duty/issues).

## License

Released under the [MIT License](LICENSE).

## Credits

Created and maintained by [@Jo-Highness](https://github.com/Jo-Highness). Built for
[Home Assistant](https://www.home-assistant.io/) and distributed via
[HACS](https://hacs.xyz/).
