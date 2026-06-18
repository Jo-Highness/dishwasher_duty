---
service: dishwasher_duty
typ: requirements
version: 1.1
status: current
stand: 2026-06-18
quellen: [MDs/dishwasher_duty.md (Ursprungsauftrag), README.md, custom_components/dishwasher_duty]
---

# Anforderungen: Dishwasher Duty (HA Custom Integration)

> Code-unabhängige Soll-Beschreibung für eine Neuentwicklung von Grund auf (WAS/WARUM).

## 1. Zweck & Kontext
HACS-installierbare Home-Assistant-Integration (Domain `dishwasher_duty`), die verfolgt, **wer die
Spülmaschine ausräumt**, dafür (ggf. anteilige) **Gutschriften** an Personen vergibt und **Statistiken**
führt. Quelle ist ein vorhandener Sensor (z. B. Home-Connect „Operation state"), der nach Programmende
auf „Finished" wechselt.
- **Nutzer:** HA-Haushalt; Personen claimen das Ausräumen.
- **Use-Cases:** Zyklus erkennen; claimen (einzeln/gemeinsam); Gutschriften/Statistik auswerten.

## 2. Geltungsbereich
**In Scope:** Zyklus-Erkennung aus Quell-Sensor, Claim-Logik (inkl. gemeinsames Ausräumen mit anteiliger
Gutschrift), Entitäten/Services, persistente Historie + Zeitraum-Statistik.
**Out of Scope:** direkte Gerätesteuerung der Spülmaschine, Belohnungs-/Bezahllogik.

## 3. Funktionale Anforderungen
- **FR-1 Konfiguration (nur UI):** Quell-Sensor wählen; „Finished"- und „Running"-Wert frei konfigurierbar
  (Defaults passend zu Home Connect); berechtigte Personen (`person`, mehrfach); „gemeinsames Ausräumen"
  (Schalter, Default an) + Co-Claim-Fenster in Sekunden (Default 90).
- **FR-2 Zyklus-Erkennung:** ein offener Zyklus entsteht **nur** beim gültigen Übergang **Running → Finished**;
  unavailable/unknown/Finished→Finished zählen nicht. Overall-Counter +1 pro gültigem Zyklus.
- **FR-3 Claim-Logik:** claimbar nur solange Maschine auf Finished (claim_open) und Zyklus nicht finalisiert.
  Gemeinsam: erster Claim öffnet Co-Claim-Fenster; nach Ablauf Gutschrift 1,0 anteilig auf alle Claimer
  (1→1,0; 2→je 0,5; 3→je ~0,3; Summe ≈1). Eine Person pro Zyklus nur einmal. Ohne „gemeinsam": erster Claim
  finalisiert sofort (1,0).
- **FR-4 Entitäten:** `sensor.dishwasher_duty_total_cycles` (total_increasing, Attribute last_cycle_finished/
  current_cycle_claimed_by/last_claim_credits); `binary_sensor.dishwasher_duty_claimable` (Attribute
  claim_open_since/co_claim_window_until/current_claimers); je Person `sensor.dishwasher_duty_<person>`
  (credits_total/today/this_week/this_month/this_year, claims_count_total, last_claim); optional Claim-Buttons.
- **FR-5 Services:** `claim(person)`, `claim_multiple(persons)`, `cancel_claim(person)`,
  `get_statistics(start, end[, person])` (supports_response), `reset_statistics([person])`.
- **FR-6 Statistik:** jeder Zyklus als Datensatz (cycle_id, finished_ts, claimers, credits/Person, claimed_at,
  Status); Zeitraum-Auswertung je Person + Gesamt-/Unclaimed-Zahlen + chronologische Liste.

## 4. Nicht-funktionale Anforderungen
- **NFR-1 Async/Non-Blocking; HACS/HA-konform** (manifest/hacs.json, nicht-deprecated APIs, hassfest).
- **NFR-2 Persistenz:** Historie + offener Zyklus überleben HA-Neustart (Store).
- **NFR-3 Robustheit/Concurrency:** Race-Conditions (Events, Co-Claim-Timer, parallele Claims) via
  `asyncio.Lock` je Zyklus; Idempotenz pro Zyklus/Person; Debounce gegen Sensor-Prellen.
- **NFR-4 Recorder-Kompatibilität:** Per-Person-Sensoren für Long-Term-Statistics/Verlaufsdiagramme geeignet.
- **NFR-5 Mehrsprachig:** DE, EN, ES, NO, EL, JA, FR.

## 5. Externe Schnittstellen & Verträge
- **Eingang:** Zustand des Quell-Sensors (Running/Finished). **HA-Entitäten/Services** s. FR-4/FR-5
  (`services.yaml` mit Selektoren). **Service-Response** für `get_statistics`.

## 6. Datenmodell
- **Konfig:** source_sensor, finished_value, running_value, persons[], allow_co_claim, co_claim_window_s.
- **Zyklus-Datensatz (Store):** cycle_id, finished_timestamp, claimers[], credits{person→float}, claimed_at, status.

## 7. Integrationen & Abhängigkeiten
- Home Assistant (person, beliebiger Quell-Sensor wie Home Connect), Recorder, HACS. Keine externen Server.

## 8. Constraints & Rahmenbedingungen
- **C-1:** reine UI-Konfiguration. **C-2:** nur gültiger Running→Finished-Übergang zählt.
- **C-3:** Gutschriftssumme je Zyklus ≈1,0. **C-4:** HA-Zeitzone für Perioden-Grenzen.

## 9. Designentscheidungen (Rationale)
- **Overall-Counter unabhängig vom Claim:** Zyklen werden gezählt, auch wenn niemand claimt (Transparenz).
- **Co-Claim-Fenster:** faire anteilige Verteilung bei gemeinsamem Ausräumen.
- **Store-basierte Historie:** Langzeitstatistik + Wiederherstellung nach Neustart.

## 10. Akzeptanzkriterien
- **A-1:** unavailable→Finished erzeugt KEINEN Zyklus; Running→Finished erhöht den Counter um genau 1.
- **A-2:** zwei Claimer im Fenster ⇒ je 0,5; Summe = 1,0.
- **A-3:** Wechsel auf Running schließt ein offenes Fenster; unclaimter Zyklus bleibt unzugewiesen, zählt aber.
- **A-4:** HA-Neustart bei offenem Fenster stellt Zyklus/Claimer/Restzeit wieder her.
- **A-5:** `get_statistics` liefert korrekte Zeitraum-Auswertung; `reset_statistics` löscht nicht die kumulierten
  Gesamtwerte ungewollt.

## 11. Annahmen & offene Punkte
- Quell-Sensor bildet Programmzustand ab; Werte je Gerät/Sprache via Konfig anpassbar.

## 12. Änderungshistorie
| Version | Datum | Änderung |
|---|---|---|
| 1.0 | 2026-05 | Erstfassung = Ursprungsauftrag (MDs/dishwasher_duty.md), Code v1.0.x |
| 1.1 | 2026-06-18 | Als Clean-Room-requirements-Doc strukturiert (Stand Code v1.0.1) |
