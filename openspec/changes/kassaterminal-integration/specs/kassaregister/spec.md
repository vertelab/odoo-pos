## ADDED Requirements

### Requirement: Gränssnitt för journalminneshändelser
Systemet SHALL låta en kassör registrera kassalådöppning utan försäljning,
växelkasseändring, prisförfrågan, clear, klockjustering och
artikelparkering från kassagränssnittet, så att händelserna hamnar i
journalminnet.

#### Scenario: Lådöppning utan försäljning från gränssnittet
- **GIVEN** en öppen session
- **WHEN** kassören öppnar lådan utan försäljning och anger orsak
- **THEN** skrivs en `OppnaKassaladaVidNollforsaljning`-post med orsaken

#### Scenario: Växelkasseändring från gränssnittet
- **GIVEN** en öppen session med känd växelkassa
- **WHEN** kassören fyller på växelkassan
- **THEN** skrivs en `ForandraVaxelkassa`-post med gammalt och nytt belopp

#### Scenario: Parkering från gränssnittet
- **GIVEN** en pågående försäljning med en rad
- **WHEN** kassören parkerar raden
- **THEN** skrivs en `ParkeraRegistreradArtikel`-post

### Requirement: Kvittosignering via vald kontrollenhet
Systemet SHALL signera kvitton via den kontrollenhet som valts för
driftsättningen, med ett dokumenterat protokoll, och neka kvittot om
enheten inte svarar.

#### Scenario: Kontrollenheten svarar inte
- **GIVEN** en konfigurerad kontrollenhet som inte nås
- **WHEN** ett kvitto ska framställas
- **THEN** kastas `UserError` och kvittot framställs inte
- **AND** ingen kontrollkod gissas

#### Scenario: Kontrollkodens format valideras
- **GIVEN** ett svar från kontrollenheten
- **WHEN** koden tas emot
- **THEN** valideras formatet mot exportschenat innan det lagras

## MODIFIED Requirements

Inga.

## REMOVED Requirements

Inga.

---

**OBS:** Denna delta-spec är förberedd men **inte tillämpad**. Den flyttas
till `specs/kassaregister/spec.md` först när fas 0 i `tasks.md` är avklarad
och implementationen är gjord.
