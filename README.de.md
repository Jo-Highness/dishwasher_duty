> 🇬🇧 [English](README.md) · 🇩🇪 Deutsch (diese Seite)

<p align="center">
  <img src="icon.png" alt="Dishwasher Duty" width="160" height="160">
</p>

# Dishwasher Duty

**Eine Home-Assistant-Integration, die nach jedem beendeten Spülprogramm festhält, wer die
Spülmaschine ausgeräumt hat, die Gutschrift bei gemeinsamem Ausräumen fair aufteilt und
Statistiken pro Person führt.**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/validate.yml/badge.svg)](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/validate.yml)
[![Tests](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/test.yml/badge.svg)](https://github.com/Jo-Highness/dishwasher_duty/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Jo-Highness/dishwasher_duty)](https://github.com/Jo-Highness/dishwasher_duty/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.2%2B-41BDF5.svg)](https://www.home-assistant.io/)

## Schnellstart

Du brauchst einen Sensor, der den Programmstatus deiner Spülmaschine meldet – z. B. den
Sensor *Operation state* (Betriebszustand) der
[Home-Connect](https://www.home-assistant.io/integrations/home_connect/)-Integration – und
mindestens eine `person` in Home Assistant.

1. **Über HACS installieren:**
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Jo-Highness&repository=dishwasher_duty&category=integration)
   – *Dishwasher Duty* herunterladen und Home Assistant neu starten.
2. **Integration hinzufügen:** *Einstellungen → Geräte & Dienste → Integration hinzufügen →
   „Dishwasher Duty"*. Quell-Sensor wählen, danach den „Läuft"- und „Fertig"-Wert (vom Sensor
   vorgeschlagen – bei Home Connect `run` und `finished`) und die Personen, die ausräumen.
3. **Ohne echtes Programm testen:** *Entwicklerwerkzeuge → Zustände* öffnen, den Quell-Sensor
   auswählen, Zustand auf `run` setzen (*Zustand setzen*), danach auf `finished`.
   `binary_sensor.dishwasher_duty_claimable` springt auf **an**.
4. **Claimen:** `button.dishwasher_duty_claim_<person>` drücken (z. B. im Dashboard). Der Sensor
   `sensor.dishwasher_duty_<person>` zeigt jetzt **1,0 credits**.
5. Optional: den Testzyklus mit der Aktion `dishwasher_duty.reset_statistics` wieder entfernen
   (ohne Person wird die **gesamte** Historie gelöscht – direkt nach der Installation unkritisch).

> In den *Entwicklerwerkzeugen* gesetzte Zustände sind nur vorübergehend; der echte Sensor
> überschreibt sie beim nächsten Update.

## Screenshots

> Aufgenommen in einer Demo-Instanz mit fiktiven Daten (Version 1.0.x – das
> Einrichtungsformular ist inzwischen zweistufig, siehe [Einrichtung](#einrichtung)).

| Entitäten-Karte | Integrationsseite |
|:---:|:---:|
| ![Claimbar, Zyklen gesamt, Gutschriften je Person und ein Claim-Knopf](images/dashboard.png) | ![Die Integration mit einem Dienst-Gerät](images/entities.png) |

| Einrichtungsformular (1.0.x) |
|:---:|
| ![Das Einrichtungsformular](images/config-flow.png) |

## So funktioniert es

Die Integration beobachtet den **Quell-Sensor**. Wechselt sein Zustand vom „Läuft"- auf den
„Fertig"-Wert, entsteht ein **offener Zyklus**. Wer die Maschine ausräumt, drückt seinen Knopf
(oder ruft eine Aktion auf) und erhält die Gutschrift für diesen Zyklus: **1,0 pro Zyklus**. Ist
gemeinsames Ausräumen (Co-Claim) aktiv, können weitere Personen innerhalb eines Zeitfensters nach
dem ersten Claim beitreten; die 1,0 wird dann geteilt.

- **Zyklus-Erkennung:** Nur ein Wechsel *läuft → fertig* zählt. `finished → finished` oder
  `unavailable → finished` (ohne vorherigen Lauf) zählen nicht.
- **`unavailable`/`unknown` werden ignoriert:** Fällt der Sensor während eines Programms kurz aus
  (*run → unavailable → finished*), zählt der Zyklus trotzdem – auch über einen Neustart von Home
  Assistant hinweg.
- **Groß-/Kleinschreibung egal:** `Run`, `run` und `RUN` sind derselbe Wert.
- **Persistenz:** Zyklus-Historie und ein offenes Claim-Fenster (mit Restzeit) überstehen
  Neustarts.
- **Statistik:** Gutschriften je Person gesamt sowie für heute/Woche/Monat/Jahr; die Sensoren
  haben `state_class: total_increasing` und funktionieren daher mit Verlaufsdiagrammen und
  Langzeitstatistik.
- **Mehrere Spülmaschinen:** Jede Spülmaschine ist ein eigener Eintrag mit eigenen Entitäten.
- Oberfläche übersetzt in Deutsch, Englisch, Spanisch, Französisch, Griechisch, Japanisch und
  Norwegisch (Bokmål).

## Installation

### HACS (empfohlen)

1. HACS-Knopf im [Schnellstart](#schnellstart) anklicken oder in HACS ⋮ →
   *Benutzerdefinierte Repositories* → `https://github.com/Jo-Highness/dishwasher_duty` mit Typ
   **Integration** hinzufügen.
2. *Dishwasher Duty* herunterladen und Home Assistant neu starten.

### Manuell

`custom_components/dishwasher_duty/` nach `<config>/custom_components/` kopieren und Home
Assistant neu starten.

## Einrichtung

Die Einrichtung hat zwei Schritte; beide lassen sich später über **Konfigurieren** am Eintrag
ändern.

**Schritt 1 – Quell-Sensor**

| Feld | Bedeutung |
|---|---|
| **Quell-Sensor** (`source_sensor`) | Eine `sensor`-Entität mit dem Programmstatus, z. B. `sensor.dishwasher_operation_state` (Home Connect). Jeder Sensor kann nur von einem Eintrag verwendet werden. |

**Schritt 2 – Zustände, Personen, gemeinsames Ausräumen**

| Feld | Bedeutung |
|---|---|
| **„Läuft"-Statuswert** (`running_value`) | Zustand, während ein Programm läuft. Standard `run`. |
| **„Fertig"-Statuswert** (`finished_value`) | Zustand am Programmende. Standard `finished`. |
| **Berechtigte Personen** (`persons`) | Eine oder mehrere `person`-Entitäten. Jede bekommt einen Claim-Knopf und einen Gutschrift-Sensor. |
| **Gemeinsames Ausräumen erlauben** (`allow_co_claim`) | An (Standard): Nach dem ersten Claim können weitere beitreten. Aus: Der erste Claim erhält sofort die volle Gutschrift. |
| **Co-Claim-Fenster** (`co_claim_window`) | Sekunden nach dem ersten Claim, in denen weitere beitreten können, 5–600 (Standard 90). |
| **Entprellung** (`debounce_seconds`) | Einen weiteren Fertig-Zyklus innerhalb so vieler Sekunden nach dem vorigen ignorieren, 0–120 (Standard 0 = aus). |

Die beiden Statusfelder sind Auswahllisten mit den möglichen Zuständen des Sensors (Attribut
`options`). Hat dein Sensor keine solche Liste oder brauchst du einen anderen Wert, tippe ihn
einfach ein. Groß-/Kleinschreibung spielt keine Rolle.

> **Home Connect:** Seit Home Assistant 2025.1 meldet der Sensor *Operation state* klein
> geschriebene Werte wie `run` und `finished`. Einträge mit den alten Standardwerten
> `Run`/`Finished` funktionieren weiter, weil ohne Beachtung der Groß-/Kleinschreibung
> verglichen wird.

## Entitäten

Alle Entitäten gehören zu einem Dienst-Gerät pro Spülmaschine, benannt nach dem Eintrag
(**Dishwasher Duty** beim ersten).

| Entität | Bedeutung |
|---|---|
| `binary_sensor.dishwasher_duty_claimable` | `on`, solange der aktuelle Zyklus claimbar ist. Attribute: `claim_open_since`, `co_claim_window_until`, `current_claimers` |
| `sensor.dishwasher_duty_total_cycles` | Anzahl beendeter Zyklen, geclaimt oder nicht. Attribute: `last_cycle_finished`, `current_cycle_claimed_by`, `last_claim_credits` |
| `sensor.dishwasher_duty_<person>` | Gutschriften einer Person, Einheit `credits`. Attribute: `credits_total`, `credits_today`, `credits_this_week`, `credits_this_month`, `credits_this_year`, `claims_count_total`, `last_claim`, `person` |
| `button.dishwasher_duty_claim_<person>` | „Ich habe ausgeräumt" – claimt den offenen Zyklus für diese Person |

`<person>` ist die Objekt-ID der `person`-Entität (`person.mia` → `…_mia`). Eine zweite
Spülmaschine erhält ein eigenes Präfix, z. B.
`sensor.dishwasher_duty_kitchen_dishwasher_total_cycles`.

Wird eine Person aus der Konfiguration entfernt, werden auch ihr Sensor und ihr Knopf entfernt.

## Aktionen (Services)

Überall, wo eine Person erwartet wird, kannst du die Entitäts-ID (`person.mia`), die Objekt-ID
(`mia`) oder den Anzeigenamen (`Mia`) angeben – ohne Beachtung der Groß-/Kleinschreibung.

| Aktion | Felder | Beschreibung |
|---|---|---|
| `dishwasher_duty.claim` | `person` | Offenen Zyklus für eine Person claimen. |
| `dishwasher_duty.claim_multiple` | `persons` | Für mehrere Personen auf einmal claimen (gleichmäßig geteilt). |
| `dishwasher_duty.cancel_claim` | `person` | Claim zurückziehen, solange das Fenster offen ist. Meldet einen Fehler, wenn kein Zyklus offen ist. |
| `dishwasher_duty.get_statistics` | `start`, `end`, `person` (alle optional) | Statistik als **Aktions-Antwort**. |
| `dishwasher_duty.reset_statistics` | `person` (optional) | ⚠️ Löscht Historie: alles oder nur Claims und Gutschriften dieser Person. |

Jede Aktion hat zusätzlich ein optionales Feld **`config_entry_id`**, um eine Spülmaschine
auszuwählen. Ohne dieses Feld gehen Claims an die Spülmaschine(n), bei denen die Person
konfiguriert ist, und `reset_statistics` wirkt auf alle Spülmaschinen. `get_statistics` braucht
das Feld, sobald mehr als eine Spülmaschine eingerichtet ist.

**Statistik-Beispiel:**

```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```

`stats` enthält `start`, `end`, `total_cycles`, `unclaimed_cycles`, `per_person`
(`participations` und Summe der `credits` je Person) und eine chronologische `timeline` der
Zyklen.

## Automationsbeispiele

**1. Haushalt benachrichtigen, wenn ein Zyklus auf einen Claim wartet**

```yaml
alias: "Spülmaschine fertig – wer räumt aus?"
triggers:
  - trigger: state
    entity_id: binary_sensor.dishwasher_duty_claimable
    to: "on"
actions:
  - action: notify.family
    data:
      title: "Spülmaschine fertig 🍽️"
      message: "Alles sauber! Drück deinen Knopf, wenn du ausgeräumt hast."
```

**2. Erneut erinnern, wenn nach 30 Minuten niemand geclaimt hat**

```yaml
alias: "Spülmaschine noch nicht geclaimt"
triggers:
  - trigger: state
    entity_id: binary_sensor.dishwasher_duty_claimable
    to: "on"
    for:
      minutes: 30
actions:
  - action: notify.family
    data:
      message: "Die Spülmaschine ist immer noch voll 👀 – bitte nach dem Ausräumen claimen."
```

`notify.family` ist ein Platzhalter – verwende eine deiner eigenen Notify-Aktionen.

**Beispiel-Dashboard**

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Spülmaschine
    entities:
      - entity: binary_sensor.dishwasher_duty_claimable
        name: Ausräumen offen?
      - entity: sensor.dishwasher_duty_total_cycles
        name: Zyklen gesamt
      - entity: button.dishwasher_duty_claim_mia
        name: Mia war's
      - entity: button.dishwasher_duty_claim_ben
        name: Ben war's
  - type: history-graph
    title: Gutschriften
    entities:
      - sensor.dishwasher_duty_mia
      - sensor.dishwasher_duty_ben
```

## So wird geteilt

- **Eine Gutschrift pro Zyklus = 1,0.** Bei n Claimern bekommt jeder ⌊100/n⌋ Hundertstel
  (abgerundet); die übrigen Hundertstel gehen an die ersten Claimer, die Summe ist also immer
  genau 1,00 (3 Personen → 0,34 / 0,33 / 0,33).
- **Zeitpunkt:** Gutschriften zählen zum Zeitpunkt, an dem der Zyklus abgeschlossen wurde
  (`claimed_at`).
- **Das Fenster schließt**, wenn das nächste Programm startet („Läuft"-Wert), nicht bei
  `ready`/`unavailable` – du kannst also auch nach dem Ausschalten noch claimen. Gab es Claims,
  wird der Zyklus abgeschlossen; sonst bleibt er ungeclaimt, zählt aber trotzdem.

## Fehlersuche / FAQ

- **Beim Programmende passiert nichts.** Statuswerte prüfen: *Entwicklerwerkzeuge → Zustände*
  öffnen, den Quell-Sensor während und nach einem Programm ansehen und mit den Werten in den
  Optionen des Eintrags vergleichen. Groß-/Kleinschreibung ist egal.
- **Der Sensor war zwischendurch `unavailable`.** `unavailable` und `unknown` werden ignoriert und
  ersetzen nicht den letzten echten Zustand. *run → unavailable → finished* zählt als ein Zyklus;
  *unavailable → finished* ohne vorherigen Lauf nicht.
- **Eine Reparaturmeldung sagt, der Quell-Sensor fehlt.** Die Entität existiert nicht mehr (z. B.
  umbenannt oder Gerät neu hinzugefügt). In den Optionen des Eintrags den neuen Sensor wählen. Die
  Meldung verschwindet, sobald der Sensor wieder existiert.
- **Ein Neustart verliert kein offenes Fenster.** Es wird mit Restzeit wiederhergestellt; ist es
  während des Neustarts abgelaufen, wird der Zyklus sofort abgeschlossen.
- **Doppelt drücken bringt nichts extra.** Ein Beitrag je Person und Zyklus.
- **`cancel_claim` meldet einen Fehler.** Gerade ist kein Zyklus offen.
- **Um Mitternacht haben sich Werte geändert.** Nur heute/Woche/Monat/Jahr werden zurückgesetzt;
  die Gesamtsumme ändert sich um Mitternacht nie.

**Debug-Logging:**

```yaml
logger:
  logs:
    custom_components.dishwasher_duty: debug
```

**Diagnose:** *Einstellungen → Geräte & Dienste → Dishwasher Duty → ⋮ → Diagnosedaten
herunterladen* (Personen-IDs werden durch Platzhalter ersetzt).

## Upgrade auf 1.1.0

- Mindestversion von Home Assistant ist jetzt **2025.2**.
- Entitäts-IDs, Unique-IDs, Aktionsnamen/-felder und die gespeicherte Historie bleiben gleich.
  Entitätsnamen sind jetzt übersetzt; selbst umbenannte Entitäts-IDs bleiben erhalten.
- Der Anzeigename des Zyklenzählers ändert sich von „… Total Cycles" zu „… Total cycles"
  (bzw. übersetzt, z. B. „… Zyklen gesamt").
- `cancel_claim` ohne offenen Zyklus meldet jetzt einen Fehler statt still nichts zu tun.
- `get_statistics` braucht `config_entry_id`, wenn mehr als eine Spülmaschine eingerichtet ist.

## Weiterführende Doku

- Technische Doku (EN): [`docs/TECHNICAL.md`](docs/TECHNICAL.md)
- Benutzerhandbücher: [`docs/user/`](docs/user) (de, en, es, fr, nb, el, ja)
- Änderungen: [`CHANGELOG.md`](CHANGELOG.md)

## Mitwirken

Beiträge sind willkommen! Bitte [`CONTRIBUTING.md`](CONTRIBUTING.md) lesen und ein Issue oder
einen Pull Request im [Issue-Tracker](https://github.com/Jo-Highness/dishwasher_duty/issues)
öffnen.

## Lizenz

Veröffentlicht unter der [MIT-Lizenz](LICENSE).
