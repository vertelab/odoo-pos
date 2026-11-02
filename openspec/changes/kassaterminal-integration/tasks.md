# Tasks — Kassaterminal-integration

**Status:** Alla uppgifter blockerade. Se `proposal.md` avsnitt
"Beslutsordning".

Regeln: en uppgift får bara bockas av när den är gjord. En uppgift som
väntar på beslut är **inte** avbockad — den är blockerad.

## Fas 0 — Beslut (blockerar allt)

- [ ] 0.1 Beställare: välj terminal (tillverkare, modell, firmware)
- [ ] 0.2 Utvecklare: utred om vald terminal har API/SDK/dokumenterad yta
- [ ] 0.3 Beställare + juridik: klargör certifiering och ansvarsfördelning
- [ ] 0.4 Beställare + juridik: välj modell A (terminalen är kontrollenhet)
      eller modell B (terminalen är kontrollsystem)
- [ ] 0.5 Uppdatera `docs/integrationsspecifikation.md` med valt modell
- [ ] 0.6 Om modell B: klargör juridiskt att Vertels deklaration inte gäller

## Fas 1 — Drivrutin (kräver 0.1–0.4)

- [ ] 1.1 Skapa drivrutinsmodul mot vald terminal
- [ ] 1.2 Överskrid `_blackbox_transport()` mot terminalens API
- [ ] 1.3 Hantera tappad kontakt med terminalen — neka kvitto, gissa aldrig
- [ ] 1.4 Validera att kontrollkodens format matchar exportschenat
- [ ] 1.5 Testa mot fysisk terminal

## Fas 2 — Gränssnitt (kräver 0.1, 0.4)

- [ ] 2.1 Inventera vilka händelser som behöver en knapp, givet terminalens
      fysiska layout (fråga 4 i `design.md`)
- [ ] 2.2 Bygg OWL-komponenter för de händelser som behövs
- [ ] 2.3 Koppla komponenterna till metoderna i
      `docs/integrationsspecifikation.md` avsnitt 3
- [ ] 2.4 Manuell test av varje händelse i kassagränssnittet

## Fas 3 — Compliance (kräver fas 1–2)

- [ ] 3.1 Uppdatera `docs/tillverkardeklaration.md` — ny version
- [ ] 3.2 Kör om testsviten, dokumentera i `docs/testprotokoll.md`
- [ ] 3.3 Skicka deklaration till Skatteverket (deadline 2026-12-18)
- [ ] 3.4 Vänta ut 14-dagarsfristen innan utrullning

## Redan klart (före denna change)

- [x] Backend-metoder för alla händelsetyper
- [x] Journalminne med SHA-256-kedja
- [x] Kontrollenhetsabstraktion, testbar utan hårdvara
- [x] API-dokumentation (`docs/integrationsspecifikation.md`)
- [x] Beslutschecklista (detta dokument + `proposal.md`)

## Anteckning

Fas 0 är inte utvecklingsarbete. Den kan inte bockas av av en utvecklare
och ska inte läggas i en sprint som "teknik". Den väntar på ett
affärsbeslut.
