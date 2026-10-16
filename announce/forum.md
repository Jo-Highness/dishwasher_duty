# Dishwasher Duty — a local dishwasher-unload credit tracker

Sharing a small custom integration I built to settle a recurring household question: *who actually unloaded the dishwasher?*

**Dishwasher Duty** watches a dishwasher **state sensor** for a configured "finished" value. When a cycle finishes, a claim opens, and a household member claims the credit — either with their per-person button or the `dishwasher_duty.claim` service. It keeps per-person credit statistics and a running count of completed cycles. Everything runs locally; there is no cloud component.

![Screenshot: Dishwasher Duty entities in the dashboard](images/dashboard.png)
<!-- INSERT: a dashboard screenshot showing the Claimable binary sensor, Total Cycles sensor, and the per-person credit sensors + claim buttons. ~1200px wide. -->

## What it does

- Watches a source **state sensor** for a "finished" value; when the cycle finishes, a claim opens.
- A household member claims the credit via a **per-person button** or the `claim` service.
- Optional **co-claiming**: several people can share the credit for one cycle within a configurable time window (e.g. two people emptied it together).
- Keeps per-person credit statistics: **total / today / week / month / year**.
- Keeps a **total-cycles** counter.
- Fully local — no cloud, no account.

![GIF: claiming a finished cycle](images/claim-flow.gif)
<!-- INSERT: short GIF — dishwasher finishes -> Claimable turns on -> person presses claim button -> their credit increments. Keep under ~5 MB. -->

## Setup

Setup is UI-first through a config flow. You pick:

- the **source state sensor** and its **finished** / **running** values,
- the participating **`person` entities**,
- the **co-claim window** and a **debounce** interval.

### Entities created

- **Claimable** — a binary sensor that is on while a finished cycle is waiting to be claimed.
- **Total Cycles** — a sensor counting completed cycles.
- Per person: a **credits** sensor and a **claim** button.

### Services

- `dishwasher_duty.claim`
- `dishwasher_duty.claim_multiple`
- `dishwasher_duty.cancel_claim`
- `dishwasher_duty.get_statistics`
- `dishwasher_duty.reset_statistics`

![Screenshot: config flow](images/config-flow.png)
<!-- INSERT: config-flow screenshot showing sensor + finished/running value selection and the person picker. -->

## Install

Via **HACS**. For now add it as a **custom repository** (`Jo-Highness/dishwasher_duty`, type *Integration*); once/if it is accepted into the default HACS store it will be available there directly. After installing, add the integration from **Settings → Devices & Services** and follow the config flow.

## Honest limitations

- It **depends on you already having a dishwasher state sensor** that reports a distinguishable "finished" value. Many dishwashers don't expose this directly — you may need to derive it from a power/state helper first. This integration does not do that detection for you.
- It is a **bookkeeping / credit tool, not an appliance controller**. It does not start, stop, or otherwise control the dishwasher.
- Credit accounting is **per the configured `person` entities** — only those people can hold credit.

## Details

- Version **1.1.0**
- Minimum Home Assistant: **2025.2**
- Licence: **MIT**
- UI translated into **7 languages**: DE, EN, ES, FR, EL, JA, NB

Feedback and issues are welcome on the repository. Thanks for reading.
