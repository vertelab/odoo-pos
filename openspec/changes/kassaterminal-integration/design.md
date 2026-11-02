# Design — Kassaterminal-integration

**Status:** Ej påbörjad. Beskriver vägval, inte valt väg.

## Kontext

Backend-API:t är terminaloberoende: det tar emot data och skriver till
journalminnet. Frågan är hur en kassaterminal når det.

## Två integrationsmodeller

### Modell A — terminalen är kontrollenhet

```
┌──────────────┐   kvittodata   ┌──────────────┐
│  Odoo        │ ─────────────► │  Terminal    │
│  (registret) │ ◄───────────── │ (kontrollenh)│
└──────────────┘  kontrollkod   └──────────────┘
```

Odoo är det certifierade registret. Terminalen signerar kvitton.

**Fördelar:** Vertel behåller deklarationen. Full kontroll över
journalminnet.

**Nackdelar:** Kräver att terminalen har öppet API. Kräver egen
certifiering.

**Implementering:** överskrid `_blackbox_transport()` i en drivrutinsmodul:

```python
class PosReceiptVendorX(models.Model):
    _inherit = 'pos.receipt'

    def _blackbox_transport(self, receipt_dict):
        response = requests.post(
            self.env['ir.config_parameter'].sudo()
                .get_param('kassaregister.vendor_x_url'),
            json=receipt_dict, timeout=5,
        )
        response.raise_for_status()
        return response.json()['control_code']
```

### Modell B — terminalen är kontrollsystem

```
┌──────────────┐   journalminne  ┌──────────────┐
│  Odoo        │ ──────────────► │  Terminal    │
│ (bokföring)  │                 │ (cert. reg.) │
└──────────────┘                 └──────────────┘
```

Terminalen är registret. Odoo exporterar journalminne enligt
SKVFS 2021:16 och tar emot Z-dagrapporter.

**Fördelar:** Ingen egen certifiering. Terminalens tillverkare ansvarar.

**Nackdelar:** Vertel deklarerar inte. Odoo blir ett stödjsystem, inte
registret. Kravet på journalminne i Odoo kan då bli överflödigt — eller
måste speglas mot terminalens.

**Konsekvens för deklarationen:** `docs/tillverkardeklaration.md` gäller
inte. Detta måste klargöras juridiskt innan modell väljs.

## Frontend — gemensamt för båda modellerna

Metoderna i `docs/integrationsspecifikation.md` avsnitt 3 anropas från
OWL-komponenter i `static/src/`. Varje anrop är en RPC mot
`pos.session`-metoden.

```javascript
// statisk/src/js/cash_drawer.js (skiss)
async openDrawerWithoutSale(reason) {
    await this.env.services.orm.call(
        'pos.session', 'log_cash_drawer_opening',
        [this.session.id, reason],
    );
}
```

**Varför detta inte kan byggas nu:** vilka händelser som ska vara
tillgängliga i gränssnittet beror på terminalens knapplayout. En terminal
med fysisk lådknapp behöver ingen mjukvaruknapp; en pekskärmsterminal gör
det. Att bygga alla sex nu vore att bygga för en gissad terminal.

## Öppna frågor

1. Vilken terminal? (blockerar allt)
2. Modell A eller B? (avgör deklarationsansvar)
3. Ska Odoo behålla journalminnet i modell B, eller spegla terminalens?
4. Vilka händelser ska ha en knapp i gränssnittet, givet terminalens
   fysiska layout?
5. Ska `pos_kassaregister_se_blackbox` slås ihop med drivrutinsmodulen när
   hårdvara är vald, eller förbli separat?

## Icke-beslut

Följande är medvetet **inte** beslutat, eftersom det kräver svar på
frågorna ovan:

- Protokoll (HTTP, seriell, USB)
- Felhantering vid tappad kontakt med terminalen
- Om kontrollkoden ska cachelagras
- Om gränssnittet ska vara OWL eller ren JS
