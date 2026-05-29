# Dishwasher Duty – User Guide (English)

Dishwasher Duty remembers **who unloads the dishwasher** and keeps statistics.

## 1. How it works
It watches a sensor of your dishwasher (e.g. Home Connect "Operation state"). When it goes
**Running → Finished**, a claimable cycle opens. Whoever unloads presses their button (or calls a
service) and gets a credit of **1.0**. If several people share the work, the 1.0 is split fairly.

## 2. Installation
- **HACS:** ⋮ → *Custom repositories* → add this repo as **Integration**, download, restart HA.
- **Manual:** copy `custom_components/dishwasher_duty/` into `<config>/custom_components/`, restart.
- Then *Settings → Devices & Services → Add integration → "Dishwasher Duty"*.

## 3. Setup
- **Source sensor:** your machine's operation-state sensor.
- **"Finished"/"Running" value:** the state text for finished/running. **Important:** check under
  *Developer Tools → States* what your sensor actually reports (e.g. `Finished`/`Run` or lowercase
  `finished`/`run`) and enter it.
- **Eligible persons:** the `person` entities who unload.
- **Shared unloading** (default on) + **co-claim window** (default 90 s): the time after the first
  press during which others can join the same cycle.

## 4. Daily use
- After unloading, press your **button**: `button.dishwasher_duty_claim_<name>`.
- Shared it? Everyone presses their button within the window — the 1.0 is split.
- Pressed by mistake? Use `dishwasher_duty.cancel_claim` while the window is open.

## 5. Entities
- `binary_sensor.dishwasher_duty_claimable` – "on" while claimable.
- `sensor.dishwasher_duty_total_cycles` – number of finished cycles.
- `sensor.dishwasher_duty_<name>` – credits per person (attributes: today/week/month/year).

## 6. Getting statistics
```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```
Returns total cycles, unclaimed cycles, per-person (participations + credits) and a
chronological list.

## 7. Notes
- `unavailable`/`unknown` (e.g. device reboot) never count as running/finished.
- Pressing repeatedly is harmless (one contribution per person/cycle).
- `dishwasher_duty.reset_statistics` clears history (all or per person) — use with care.
