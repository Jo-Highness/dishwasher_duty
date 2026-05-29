# Dishwasher Duty – Benutzerhandbuch (Deutsch)

Dishwasher Duty merkt sich, **wer die Spülmaschine ausräumt**, und führt darüber Statistik.

## 1. Wie es funktioniert
Die Integration beobachtet einen Sensor deiner Spülmaschine (z. B. Home Connect „Operation
state"). Wenn dieser von **Läuft → Fertig** wechselt, entsteht ein „offener Zyklus". Wer
ausräumt, drückt seinen Knopf (oder nutzt einen Service) und bekommt die Gutschrift **1,0**.
Räumen mehrere gemeinsam aus, wird die 1,0 fair geteilt.

## 2. Installation
- **HACS:** ⋮ → *Benutzerdefinierte Repositories* → dieses Repo als **Integration** hinzufügen,
  herunterladen, HA neu starten.
- **Manuell:** `custom_components/dishwasher_duty/` nach `<config>/custom_components/` kopieren,
  HA neu starten.
- Dann *Einstellungen → Geräte & Dienste → Integration hinzufügen → „Dishwasher Duty"*.

## 3. Einrichtung
- **Quell-Sensor:** der Operation-State-Sensor deiner Maschine.
- **„Fertig"-/„Läuft"-Wert:** der State-Text für fertig/läuft. **Wichtig:** prüfe unter
  *Entwicklerwerkzeuge → Zustände*, welchen Wert dein Sensor wirklich hat (z. B. `Finished`/`Run`
  oder klein `finished`/`run`), und trage ihn ein.
- **Berechtigte Personen:** die `person`-Entitäten, die ausräumen.
- **Gemeinsames Ausräumen** (Default an) + **Co-Claim-Fenster** (Default 90 s): Zeitfenster, in
  dem nach dem ersten Knopfdruck weitere Personen beitreten können.

## 4. Tägliche Nutzung
- Nach dem Ausräumen den eigenen **Knopf** drücken: `button.dishwasher_duty_claim_<name>`.
- Gemeinsam ausgeräumt? Jeder drückt innerhalb des Fensters seinen Knopf – die 1,0 wird geteilt.
- Versehentlich gedrückt? Service `dishwasher_duty.cancel_claim` (solange das Fenster offen ist).

## 5. Entitäten
- `binary_sensor.dishwasher_duty_claimable` – „on", solange claimbar.
- `sensor.dishwasher_duty_total_cycles` – Anzahl aller Fertig-Zyklen.
- `sensor.dishwasher_duty_<name>` – Gutschriften je Person (Attribute: heute/Woche/Monat/Jahr).

## 6. Statistik abrufen
```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```
Ergebnis: Gesamtzyklen, nicht geclaimte Zyklen, pro Person (Beteiligungen + Gutschriften) und
eine chronologische Liste.

## 7. Hinweise
- `unavailable`/`unknown` (z. B. Geräteneustart) zählen nie als Lauf/Fertig.
- Mehrfaches Drücken schadet nicht (1 Beitrag je Person/Zyklus).
- `dishwasher_duty.reset_statistics` löscht Historie (ganz oder pro Person) – mit Bedacht nutzen.
