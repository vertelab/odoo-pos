# kassaregister Specification

## Purpose

Svenskt kassaregister i Odoo 18 enligt Skatteverkets föreskrifter
SKVFS 2021:17 (kassaregister) och SKVFS 2021:16 (standardexport av
journalminne). Specifikationen beskriver hur systemet fungerar **idag**,
inte vad som önskas.

Moduler: `pos_kassaregister_se` (registret), `pos_kassaregister_se_blackbox`
(kontrollenhetsbrygga).

## Requirements

### Requirement: Journalminne med obruten hash-kedja
Systemet SHALL lagra varje händelse som ändrar kassaregistrets tillstånd i
ett append-only journalminne med SHA-256-kedja, så att en bruten kedja kan
upptäckas.

#### Scenario: Kedjan håller efter blandade händelser
- **GIVEN** en session med start-, växelkasse-, lådöppnings-, prisförfrågan-
  och clear-händelser
- **WHEN** kedjan verifieras med `_check_chain_unit()`
- **THEN** returneras en tom lista (kedjan är obruten)

#### Scenario: Kedjan upptäcker manipulation
- **GIVEN** ett journalminne där en post ändrats i efterhand
- **WHEN** kedjan verifieras
- **THEN** returneras en lista med den brutna länken och dess sekvensnummer

### Requirement: Öppningsväxelkassa loggas med räknat belopp
Systemet SHALL logga öppningsväxelkassan när kassören räknar kassalådan,
med det faktiskt räknade beloppet — inte med 0.

#### Scenario: Växelkassan loggas vid räkning
- **GIVEN** en nyskapad session i `opening_control`
- **WHEN** kassören anger 1500 kr via `set_opening_control(1500, ...)`
- **THEN** skrivs en `ForandraVaxelkassa`-post med `new_float = 1500`
- **AND** `cash_float_start` sätts till 1500

#### Scenario: Ingen logg innan lådan räknats
- **GIVEN** en nyskapad session
- **WHEN** ingen räkning har gjorts
- **THEN** finns ingen `ForandraVaxelkassa`-post (beloppet är okänt)

#### Scenario: Påfyllning räknar från räknad öppningskassa
- **GIVEN** en session öppnad med 1500 kr
- **WHEN** `log_cash_float_change(2000)` anropas
- **THEN** loggas `old_float = 1500`, `new_float = 2000`, `difference = 500`

### Requirement: Ändringsspärr på registrerad försäljning
Systemet SHALL neka ändring och radering av en registrerad försäljning och
dess rader (6 kap. 1 §).

#### Scenario: Betald order kan inte ändras
- **GIVEN** en order i state `paid`
- **WHEN** ett fält utanför vitlistan skrivs
- **THEN** kastas `UserError`

#### Scenario: Rad i betald order kan inte ändras
- **GIVEN** en orderrad vars order är i state `paid` eller `done`
- **WHEN** `line.write({'qty': 99})` anropas
- **THEN** kastas `UserError`

#### Scenario: Rad i betald order kan inte raderas
- **GIVEN** en orderrad vars order är i state `paid` eller `done`
- **WHEN** `line.unlink()` anropas
- **THEN** kastas `UserError`

### Requirement: Registreringsenhet per kassa
Systemet SHALL koppla varje `pos.config` till exakt en registreringsenhet
med egen kvitto-, X- och Z-serie (4 kap. 2 §).

#### Scenario: Ny kassa får automatiskt en enhet
- **GIVEN** en ny `pos.config`
- **WHEN** posten skapas
- **THEN** sätts `registration_unit_id` till en enhet kopplad till kassan
- **AND** `registration_unit_ready` blir `True`

#### Scenario: Enhet utan kassa nekas
- **GIVEN** ett anrop till `pos.registration.unit.create()` utan `config_id`
- **WHEN** posten skapas
- **THEN** kastas `ValidationError` med hänvisning till 4 kap. 2 §
- **AND** inga sekvenser skapas

#### Scenario: Modellbeteckning måste innehålla SE
- **GIVEN** en enhet vars `model_designation` sätts till `ODOO-18`
- **WHEN** posten skrivs
- **THEN** kastas `ValidationError` med hänvisning till 4 kap. 6 §

### Requirement: Z-dagrapport vid stängning
Systemet SHALL framställa en Z-dagrapport när försäljningsdagen stängs,
med obligatoriska belopp och antal (7 kap. 3 §).

#### Scenario: Lådöppningar räknas i Z-rapporten
- **GIVEN** en session med två `OppnaKassaladaVidNollforsaljning`-poster
- **WHEN** Z-rapporten genereras
- **THEN** är `drawer_open_count` = 2

#### Scenario: Z-rapporten återanvänds inte
- **GIVEN** en session som redan har en Z-rapport
- **WHEN** `_generate_z_report()` anropas igen
- **THEN** returneras den befintliga rapporten oförändrad

#### Scenario: Övningsläge påverkar inte Z-rapporten
- **GIVEN** en session i övningsläge med försäljning
- **WHEN** Z-rapporten genereras
- **THEN** ingår övningsförsäljningen inte i `total_sales`

### Requirement: Kontrollenhet signerar kvitton
Systemet SHALL signera varje kvitto via en kontrollenhet eller ett
kontrollsystem innan kvittot framställs (7 kap. 1 §).

#### Scenario: Kvitto utan kontrollenhet nekas
- **GIVEN** en registreringsenhet utan `control_unit_serial`
- **WHEN** ett kvitto ska framställas
- **THEN** kastas `UserError` — ingen kontrollkod gissas

#### Scenario: Session utan kontrollenhet kan inte öppnas
- **GIVEN** en kassa vars enhet saknar `control_unit_serial`
- **WHEN** en session skapas med bryggmodulen installerad
- **THEN** kastas `UserError` med hänvisning till 4 kap. 9 §

## Kända begränsningar

| Begränsning | Orsak |
|---|---|
| Ingen POS-frontend | Väntar på terminalval — se `changes/kassaterminal-integration/` |
| Ingen fysisk drivrutin | Väntar på terminalval |
| `_blackbox_transport()` härleder koden lokalt | Gör modulen testbar utan hårdvara |
| Blackbox-verifiering utanför deklarationen | Separat modul, eget certifieringsspår |
