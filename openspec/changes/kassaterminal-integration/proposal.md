# Change: Kassaterminal-integration

**Status:** Blockerad — väntar på beslut
**Skapad:** 2026-11-02
**Ägare:** Beställare (beslut 1–3), utvecklare (beslut 4)

---

## Why

Kassaregistrets backend-yta för journalminneshändelser är klar och testad
(104 tester, 0 fel), men **inget gränssnitt anropar den**. Metoderna
`log_cash_drawer_opening`, `log_cash_float_change`, `log_price_inquiry`,
`log_clear`, `log_clock_adjustment` och `action_park*` är oåtkomliga för
en kassör.

Det innebär att registret i praktiken inte kan användas som kassaregister
än: en kassör kan inte öppna lådan utan försäljning, fylla på växelkassa
eller parkera en artikel på ett spårbart sätt.

Arbetet kan **inte** påbörjas förrän det är känt vilken kassaterminal som
ska användas. Att bygga gränssnittet först vore att låsa sig vid en
gissning om hårdvara.

## What Changes

Inget än. Detta är en förberedd change som beskriver vad som ska göras när
blockeraren är löst.

## Beslutsordning — måste lösas i ordning

| # | Fråga | Avgörs av | Blockerar |
|---|---|---|---|
| 1 | **Vilken** terminal — tillverkare, modell, firmware? | Beställare | 2, 3, 4 |
| 2 | **Kan** den integreras — API, SDK, dokumenterad yta? | Utvecklare | 3, 4 |
| 3 | **Får** den anslutas — certifiering, leverantörens tillstånd, ansvarsfördelning? | Beställare + juridik | 4 |
| 4 | **Vem** ansvarar för kontrollkoden — terminalen eller kontrollsystemet? | Beställare + juridik | Modellval |

Beslut 4 avgör vilken av två integrationsmodeller som gäller:

- **Modell A** — terminalen är kontrollenhet. Odoo är registret.
  Drivrutinen överskrider `_blackbox_transport()`.
- **Modell B** — terminalen är ett certifierat kontrollsystem. Odoo blir
  bokförings- och rapporteringssystem. **Tillverkardeklarationen gäller då
  terminalens tillverkare, inte Vertel.** Detta måste klargöras juridiskt.

## Impact

### Berörda specifikationer
- `specs/kassaregister` — nytt krav: gränssnitt för journalminneshändelser

### Berörda moduler
- `pos_kassaregister_se` — ny `static/src/` med OWL-komponenter
- `pos_kassaregister_se_blackbox` — drivrutin mot vald hårdvara

### Berörd dokumentation
- `docs/tillverkardeklaration.md` — ny version kräver ny deklaration
  enligt `docs/versionspolicy.md`
- `docs/integrationsspecifikation.md` — uppdateras när modell är vald

### Compliance
- Modell A: Vertel deklarerar, 14 dagars inskickningsfrist gäller
- Modell B: terminalens tillverkare deklarerar, Vertel deklarerar inte

## Vad som redan är klart

| Del | Status |
|---|---|
| Backend-metoder för alla händelsetyper | Klar, testad |
| Journalminne med hash-kedja | Klar, testad |
| Kontrollenhetsabstraktion (`_blackbox_transport`) | Klar, testbar utan hårdvara |
| API-dokumentation | `docs/integrationsspecifikation.md` |
| Beslutschecklista | Detta dokument, avsnitt ovan |

## Vad som INTE är klart

| Del | Blockerat av |
|---|---|
| POS-frontend (OWL) | Beslut 1 |
| Fysisk drivrutin | Beslut 1, 2 |
| Certifiering mot vald terminal | Beslut 3 |
| Val av modell A eller B | Beslut 4 |

## Nästa steg

1. Beställare fattar beslut 1.
2. Utvecklare utreder beslut 2 mot vald modell.
3. Beställare + juridik avgör beslut 3 och 4.
4. Först då: `/opsx:apply` på denna change.
