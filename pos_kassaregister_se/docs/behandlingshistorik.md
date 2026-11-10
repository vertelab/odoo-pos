# Behandlingshistorik — pos_kassaregister_se

Varje version som tillhandahålls dokumenteras här med bedömningen om
ändringen rör en reglerad funktion. Se `versionspolicy.md`.

| Version | Datum | Ändring | Reglerad | Deklaration |
|---|---|---|---|---|
| 18.0.1.0.0 | 2026-10-29 | Första version: registreringsenhet, journalminne med SHA-256-kedja, DB-skydd | Ja | — |
| 18.0.1.1.0 | 2026-10-29 | Sessionsgrind, övningsläge, kontrollenhetskontroll | Ja | — |
| 18.0.1.2.0 | 2026-10-30 | Dagrapporter X och Z, egen Z-serie per enhet | Ja | — |
| 18.0.1.3.0 | 2026-11-01 | Kvittoutskrift (fält a–m), kopia-spärr, spärrar mot otillåtna funktioner | Ja | — |
| 18.0.1.4.0 | 2026-11-02 | Journalminnets händelser: parkering, kassalåda, växelkassa, prisförfrågan, clear, klocka | Ja | — |
| 18.0.1.5.0 | 2026-11-02 | XML-export enligt SKVFS 2021:16 med XSD-validering, exportwizard | Ja | *väntar* |

---

## Detaljer per version

### 18.0.1.4.0 — 2026-11-02

**Reglerad:** Ja — journalminnets innehåll utökas med elva händelsetyper.

**Vad som ändrades.** De händelser som inte producerar någon order kan bara
fångas där de inträffar. Nu loggas de:

- `ParkeraRegistreradArtikel`, `OppnaParkering`, `RaderaParkeradArtikel`,
  `AndraParkeradArtikel` (4 kap. 5 §)
- `OppnaKassaladaVidNollforsaljning` (4 kap. 4 §)
- `ForandraVaxelkassa` vid start, ändring och stängning (4 kap. 6 §)
- `StallaPrisforfragan`, `AnvandaClear` (4 kap. 9 §)
- `StallaOmKlockan` med gammal tid, ny tid och differens (4 kap. 10 §)

**Varför det spelar roll.** Öppnings- och stängningsväxelkassan är
obligatoriska siffror i Z-dagrapporten. Utan dem blir rapporten ofullständig
och en kontrollant kan inte stämma av kassan.

**Verifiering.** 12 nya tester. Kedjan verifieras hålla efter samtliga nya
händelsetyper.

### 18.0.1.5.0 — 2026-11-02

**Reglerad:** Ja — ny exportfunktion enligt SKVFS 2021:16.

**Vad som ändrades.** Journalminnet kan exporteras till XML i det format
Skatteverket föreskriver. Elementnamnen är hämtade ordagrant ur
Skatteverkets schema — de är normerande, och ett felstavat namn ger en fil
som avvisas.

**Varför det spelar roll.** Utan exporten kan en kontrollant inte läsa in
registreringarna i sitt eget kontrollprogram. Exporten är ett krav, inte en
bekvämlighet.

**Ett fynd under arbetet.** Kontrollenhetens tillverkningsnummer måste vara
exakt 17 tecken enligt schemat. Värdet valideras nu vid inmatning, så felet
upptäcks när det görs — inte vid export.

**Verifiering.** 22 nya tester, inklusive validering mot Skatteverkets XSD.
En fil som inte validerar levereras aldrig.

---

## Öppna punkter

| Punkt | Status |
|---|---|
| Inskickning av deklaration för 18.0.1.5.0 | **Väntar — deadline 2026-12-18** |
| Manuell genomgång av 54 krav mot körande modul | Pågår |
| Blackbox-modul mot kontrollserver (9.1–9.4) | Ej påbörjad, separat deklaration |
