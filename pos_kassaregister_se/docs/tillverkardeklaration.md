# Tillverkardeklaration — pos_kassaregister_se

**Utfärdad av:** Vertel Sverige AB
**Gäller version:** 18.0.1.6.0
**Datum:** 2026-11-02
**Regelverk:** SKVFS 2021:17 (kassaregister), SKVFS 2021:16 (standardexport)

---

## 1. Deklaration

Vertel Sverige AB deklarerar härmed att kassaregisterprogrammet
`pos_kassaregister_se` version 18.0.1.6.0 är testat enligt de metoder som
anges i detta dokument och i det medföljande testprotokollet, samt att
programmet överensstämmer med Skatteverkets föreskrifter om kassaregister
(SKVFS 2021:17) och om standardexport av data från journalminne
(SKVFS 2021:16).

Programmet är avsett att användas tillsammans med Odoo 18 och modulen
`point_of_sale`.

## 2. Reglerade funktioner

Följande funktioner är reglerade enligt SKVFS 2021:17 och omfattas av
denna deklaration:

| Funktion | Kapitel | Implementering |
|---|---|---|
| Journalminne | 4 kap. | `pos.journal.entry`, append-only tabell med SHA-256-kedja |
| Kvittoutskrift | 7 kap. | `pos.receipt` + QWeb-mall `receipt_kassaregister.xml` |
| Dagrapporter (X och Z) | 7 kap. 3 § | `pos.report.x`, `pos.report.z` |
| Kontrollenhet | 7 kap. 1 § | `_control_unit_sign()` — överridbar drivrutinshook |
| Spärrar mot ändring | 6 kap. | `write()`/`unlink()`-spärrar på `pos.order` och `pos.order.line` |
| Export av journalminne | SKVFS 2021:16 | `pos.journal.export` + XSD-validering |
| Övningsläge | 7 kap. | `pos.session.is_training`, kvitton märkta "övning" |

## 3. Testmetod

Programmet testas på tre nivåer:

1. **Automatiska enhetstester** — 104 tester i Odoo:s testramverk, körda
   mot en testdatabas. Varje test motsvarar ett krav eller ett scenario i
   specifikationen. Samtliga tester är godkända vid deklarationsdatum.

2. **Schema-validering** — den genererade XML-exporten valideras mot
   Skatteverkets publicerade XSD
   (`ExportAvDataFranJournalminneEnligtSKVFS202116-2021-12-08.xsd`).
   En fil som inte validerar levereras aldrig.

3. **Manuell genomgång** — samtliga 54 krav i kravdokumentet
   (PRD "GreenGate Online / Kassaregister", version 1.1) gås igenom mot
   den körande modulen. Resultatet redovisas i `testprotokoll.md`.

## 4. Kända begränsningar

- **Kontrollenhet.** Modulen innehåller en abstraktion för kontrollenhet
  (`_control_unit_sign()`). En fysisk eller certifierad kontrollenhet
  kräver en drivrutinsmodul som överskriver metoden. Utan
  `control_unit_serial` på registreringsenheten vägrar modulen att
  producera kvitton och att exportera — den gissar aldrig.
- **Kontrollenhetens tillverkningsnummer** måste vara exakt 17 tecken
  enligt exportschemat. Värdet valideras vid inmatning.
- **Kassaterminalens gränssnitt är inte byggt.** Journalminnets
  händelsemetoder (kassalåda, växelkassa, prisförfrågan, clear,
  klockjustering, parkering) är implementerade och testade men anropas
  inte av något gränssnitt. Arbetet är blockerat i avvaktan på val av
  kassaterminal — se `docs/integrationsspecifikation.md` avsnitt 2 och
  `../../openspec/changes/kassaterminal-integration/`.
- **Organisationsnummer** måste finnas på företaget. Export utan
  organisationsnummer nekas.
- **Blackbox-verifiering** mot Skatteverkets kontrollserver
  (`pos_kassaregister_se_blackbox`) är en separat modul och omfattas inte
  av denna deklaration.

## 5. Versionspolicy

Se `versionspolicy.md`. Varje ändring av en reglerad funktion kräver en ny
tillverkardeklaration och en höjd versionsnummer.

## 6. Behandlingshistorik

Se `behandlingshistorik.md`.

## 7. Inskickning till Skatteverket

Deklaration och utdrag ur testprotokollet sänds till Skatteverket senast
**två veckor** innan versionen tillhandahålls på den svenska marknaden
(SKVFS 2021:17 8 kap.).

| Version | Inskickad | Tidigast tillhandahållande |
|---|---|---|
| 18.0.1.6.0 | *ej inskickad* | *14 dagar efter inskickning* |

**Deadline för första inskickning: 2026-12-18.**

---

*Vertel Sverige AB — org.nr anges i inskickningen.*
