# Dishwasher Duty – Brukerveiledning (Norsk bokmål)

Dishwasher Duty husker **hvem som tømmer oppvaskmaskinen** og fører statistikk.

## 1. Slik fungerer det
Den overvåker en sensor på oppvaskmaskinen (f.eks. Home Connect «Operation state»). Når den går
fra **Kjører → Ferdig**, åpnes en krevbar syklus. Den som tømmer trykker på knappen sin (eller
kaller en tjeneste) og får en kreditt på **1,0**. Hjelper flere til, deles 1,0 rettferdig.

## 2. Installasjon
- **HACS:** ⋮ → *Egendefinerte arkiver* → legg til dette arkivet som **Integrasjon**, last ned,
  start HA på nytt.
- **Manuelt:** kopier `custom_components/dishwasher_duty/` til `<config>/custom_components/`, start
  på nytt.
- Deretter *Innstillinger → Enheter og tjenester → Legg til integrasjon → «Dishwasher Duty»*.

## 3. Oppsett
- **Kildesensor:** maskinens operasjonstilstand-sensor.
- **«Kjører»-/«Ferdig»-verdi** (andre steg): velg dem fra listen over tilstander sensoren tilbyr,
  eller skriv inn din egen. Home Connect bruker `run` og `finished` (standard). Store/små
  bokstaver spiller ingen rolle. Er du usikker, se *Utviklerverktøy → Tilstander*.
- **Berettigede personer:** `person`-entitetene som tømmer.
- **Delt tømming** (på som standard) + **co-claim-vindu** (90 s).

## 4. Daglig bruk
- Etter tømming, trykk på din **knapp**: `button.dishwasher_duty_claim_<navn>`.
- Delt? Alle trykker på knappen sin innen vinduet — 1,0 deles.
- Trykket ved et uhell? Bruk `dishwasher_duty.cancel_claim` mens vinduet er åpent.

## 5. Entiteter
- `binary_sensor.dishwasher_duty_claimable` – «on» så lenge krevbar.
- `sensor.dishwasher_duty_total_cycles` – antall fullførte sykluser.
- `sensor.dishwasher_duty_<navn>` – kreditter per person (attributter: dag/uke/måned/år).

## 6. Hente statistikk
```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```
Returnerer totale sykluser, ikke-krevde sykluser, per person (deltakelser + kreditter) og en
kronologisk liste.

## 7. Merknader
- `unavailable`/`unknown` ignoreres: *run → unavailable → finished* teller som én syklus;
  *unavailable → finished* uten forutgående kjøring gjør ikke det.
- `dishwasher_duty.cancel_claim` gir en feil hvis ingen syklus er åpen.
- Å trykke flere ganger er ufarlig (ett bidrag per person/syklus).
- `dishwasher_duty.reset_statistics` sletter historikk (alt eller per person) — bruk med omhu.
