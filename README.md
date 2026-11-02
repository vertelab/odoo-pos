# odoo-pos

Point of Sale-tillägg för Odoo 18, utvecklade av Vertel Sverige AB.

## Moduler

| Modul | Syfte | Status |
|---|---|---|
| `pos_kassaregister_se` | Svenskt kassaregister enligt SKVFS 2021:17 | Under deklarationsberedning |
| `pos_kassaregister_se_blackbox` | Kontrollenhetsbrygga (drivrutin) | Abstraktion klar, hårdvara ej vald |
| `pos_cash_ticket` | Kontantkvitto | — |
| `pos_fcu` | — | — |
| `pos_known_partner` | Känd kund i kassan | — |
| `pos_partner` | Kundkoppling | — |
| `pos_session_memcached` | Sessionscache | — |
| `pos_available_in_pos_variant` | Variantval i kassan | — |

## pos_kassaregister_se — kassaregister

Implementerar de reglerade funktionerna i SKVFS 2021:17 och
standardexport enligt SKVFS 2021:16.

| Funktion | Kapitel | Implementering |
|---|---|---|
| Journalminne | 4 kap. | `pos.journal.entry` — append-only, SHA-256-kedja |
| Kvittoutskrift | 7 kap. | `pos.receipt` + QWeb `receipt_kassaregister.xml` |
| Dagrapporter (X/Z) | 7 kap. 3 § | `pos.report.x`, `pos.report.z` |
| Kontrollenhet | 7 kap. 1 § | `_control_unit_sign()` — överridbar hook |
| Ändringsspärrar | 6 kap. | `write()`/`unlink()` på `pos.order` och `pos.order.line` |
| Export av journalminne | SKVFS 2021:16 | `pos.journal.export` + XSD-validering |
| Övningsläge | 7 kap. | `pos.session.is_training` |

### Dokumentation

| Fil | Innehåll |
|---|---|
| `docs/tillverkardeklaration.md` | Deklaration mot SKVFS 2021:17, kända begränsningar |
| `docs/testprotokoll.md` | Manuell genomgång av de 54 kraven |
| `docs/prd54-avvikelser.md` | Krav-för-krav-status, öppna avvikelser |
| `docs/versionspolicy.md` | När ny deklaration krävs |
| `docs/behandlingshistorik.md` | Ändringshistorik för reglerade funktioner |
| `docs/integrationsspecifikation.md` | **API-yta för kassaterminal** (se nedan) |

### Tester

```bash
sudo -u odoo /usr/bin/odoo --config /etc/odoo/odoo.conf -d <db> \
    -u pos_kassaregister_se --test-enable --stop-after-init --no-http \
    --logfile=/tmp/test.log
```

104 tester, samtliga godkända (2026-11-02).

## Blockerat arbete — kassaterminalens gränssnitt

Journalminnets händelsemetoder (`log_cash_drawer_opening`,
`log_cash_float_change`, `log_price_inquiry`, `log_clear`,
`log_clock_adjustment`, `action_park*`) är implementerade och testade, men
**anropas inte av något gränssnitt**. Det finns ingen POS-frontend i
modulen.

Det är avsiktligt. Ett gränssnitt kan inte byggas förrän tre frågor är
besvarade, och de besvaras i den ordningen:

| # | Fråga | Typ | Vem avgör |
|---|---|---|---|
| 1 | **Vilken** kassaterminal ska användas? | Affärsbeslut | Beställare |
| 2 | **Kan** den integreras — finns API/SDK/dokumenterad yta? | Teknisk utredning | Utvecklare |
| 3 | **Får** den anslutas — certifiering, leverantörens tillstånd, ansvarsfördelning? | Avtal/compliance | Beställare + juridik |

Först därefter blir frontend-koden meningsfull. Bygger man gränssnittet
först låser man sig vid en gissning om hårdvara.

Backend-API:t ligger **under** detta beslut och är därför oberoende av
vilken terminal som väljs — det är skälet till att det gick att bygga
klart nu. Se `docs/integrationsspecifikation.md` för exakt vad en terminal
behöver kunna anropa.

## Utvecklingskonventioner

- Källkod och commits på **engelska**; UI-strängar engelska i koden,
  svenska i `sv.po`.
- `view_mode: list` (aldrig `tree`) — Odoo 18.
- Migreringar i `migrations/<version>/` — katalogen måste ha en version
  **högre än** den installerade, annars körs skriptet aldrig.
- Secrets i pillar eller keykeep — aldrig i källkod.
