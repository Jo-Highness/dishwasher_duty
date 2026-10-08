**Dishwasher Duty — a small local integration that tracks who unloads the dishwasher**

I made a custom integration to settle the "who emptied the dishwasher?" question at home.

It watches a dishwasher **state sensor** for a configured "finished" value. When a cycle finishes, a claim opens and someone claims the credit — via a per-person button or the `claim` service. Optional **co-claiming** lets several people share credit for one cycle within a time window. It keeps per-person stats (total / today / week / month / year) and a total-cycles counter. Fully local, no cloud.

![Screenshot: entities on a dashboard](images/overview.png)
<!-- INSERT: one clean dashboard screenshot (Claimable sensor + per-person credits/buttons). -->

**Setup** is UI-first (config flow): pick the source sensor + finished/running values, the `person` entities, the co-claim window and debounce. You get a "Claimable" binary sensor, a Total Cycles sensor, and a credits sensor + claim button per person. Services: `claim`, `claim_multiple`, `cancel_claim`, `get_statistics`, `reset_statistics`.

**Honest limitations:**

- You need to already have a dishwasher **state sensor** that reports a distinguishable "finished" value. Many dishwashers need a separate power/state helper first — this doesn't detect that for you.
- It's a bookkeeping/credit tool, **not an appliance controller**.
- Credit is tracked only for the configured persons.

**Details:** v1.0.1, min HA 2024.11, MIT, UI in 7 languages (DE/EN/ES/FR/EL/JA/NB). Install via HACS as a custom repository (`Jo-Highness/dishwasher_duty`); default store once accepted.

Feedback welcome.
