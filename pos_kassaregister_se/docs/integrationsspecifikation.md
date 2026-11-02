# Integrationsspecifikation — kassaterminal

**Gäller:** `pos_kassaregister_se` 18.0.1.6.0
**Datum:** 2026-11-02
**Status:** API-yta fastställd. Hårdvara ej vald.

---

## 1. Varför detta dokument finns

Kassaregistret har en färdig backend-yta för de händelser som en
kassaterminal måste rapportera, men inget gränssnitt som anropar den.
Gränssnittet kan inte byggas förrän det är känt **vilken** terminal som
ska användas, **om** den kan integreras och **om** den får anslutas.

Det här dokumentet beskriver vad en terminal behöver kunna anropa. Det
används som underlag när terminalvalet görs — inte som en specifikation
för en redan vald terminal.

## 2. Beslutsordning

| # | Fråga | Avgörs av | Blockerar |
|---|---|---|---|
| 1 | Vilken terminal (tillverkare, modell, firmware)? | Beställare | Allt nedan |
| 2 | Har den öppet API/SDK/dokumenterad integrationsyta? | Utvecklare | Punkt 3–4 |
| 3 | Är den certifierad enligt SKVFS 2021:17? | Beställare + juridik | Punkt 4 |
| 4 | Vem ansvarar för kontrollkoden — terminalen eller kontrollsystemet? | Beställare + juridik | Punkt 5 |

Punkt 4 styr vilken av de två integrationsmodellerna i avsnitt 4 som
gäller.

## 3. Vad registret redan kan ta emot

Samtliga metoder finns på `pos.session` respektive `pos.order.line` och är
testade. De skriver till journalminnet (`pos.journal.entry`) med SHA-256-
kedja.

### 3.1 Kassalåda

| Metod | Event-typ | Kapitel |
|---|---|---|
| `log_cash_drawer_opening(reason=None)` | `OppnaKassaladaVidNollforsaljning` | 4 kap. 4 § |

Anropas när lådan öppnas **utan** att en försäljning registreras.

### 3.2 Växelkassa

| Metod | Event-typ | Kapitel |
|---|---|---|
| `log_cash_float_change(new_float, reason=None)` | `ForandraVaxelkassa` | 4 kap. 6 § |

Loggar gammalt belopp, nytt belopp och differens. Öppningsväxelkassan
loggas automatiskt när kassören räknar lådan (`set_opening_control`).

### 3.3 Prisförfrågan och clear

| Metod | Event-typ | Kapitel |
|---|---|---|
| `log_price_inquiry(product=None, price=None)` | `StallaPrisforfragan` | 4 kap. 9 § |
| `log_clear(scope=None)` | `AnvandaClear` | 4 kap. 9 § |

### 3.4 Klockjustering

| Metod | Event-typ | Kapitel |
|---|---|---|
| `log_clock_adjustment(old_time, new_time, reason=None)` | `StallaOmKlockan` | 4 kap. 10 § |

Loggar både gammal och ny tid samt differensen i sekunder.

### 3.5 Parkering

| Metod | Event-typ | Kapitel |
|---|---|---|
| `line.action_park(reason=None)` | `ParkeraRegistreradArtikel` | 4 kap. 5 § |
| `line.action_resume_parking()` | `OppnaParkering` | 4 kap. 5 § |
| `line.action_delete_parked(reason=None)` | `RaderaParkeradArtikel` | 4 kap. 5 § |
| `line.action_change_parked(new_qty=None, reason=None)` | `AndraParkeradArtikel` | 4 kap. 5 § |

## 4. Vad terminalen måste kunna — två modeller

### Modell A — terminalen är kontrollenhet

Terminalen tar emot kvittodata och returnerar en kontrollkod.
Registret anropar `_control_unit_sign()`.

**Terminalen måste:**
- ta emot kvittodata över ett dokumenterat protokoll (HTTP, seriell, USB)
- returnera en kontrollkod som registret kan lagra på kvittot
- ha ett tillverkningsnummer på exakt **17 tecken** (exportschenat)
- hantera att anropet kan misslyckas — registret vägrar då framställa kvittot

**Kontraktet i koden:**

```python
# pos_kassaregister_se_blackbox/models/pos_receipt_blackbox.py
def _blackbox_transport(self, receipt_dict):
    """Skicka receipt_dict till kontrollenheten, returnera kontrollkoden."""
```

Denna metod är den enda som behöver överskridas vid riktig hårdvara.
Standardimplementationen härleder koden lokalt (SHA-256) så att modulen
går att testa utan hårdvara.

### Modell B — terminalen är ett kontrollsystem

Terminalen är en fullständig kassa med eget certifierat kontrollsystem.
Odoo blir då ett **bokförings- och rapporteringssystem**, inte registret.

**Terminalen måste:**
- exportera journalminne enligt SKVFS 2021:16 (XML mot XSD)
- kunna leverera Z-dagrapporter per försäljningsdag
- kunna leverera kontrollkoder per kvitto

**Konsekvens:** i modell B är `pos_kassaregister_se` inte det certifierade
registret. Tillverkardeklarationen gäller då terminalens tillverkare, inte
Vertel. Detta måste klargöras juridiskt innan modell väljs.

## 5. Vad som INTE är byggt

| Del | Status | Blockerat av |
|---|---|---|
| POS-frontend (OWL/JS) som anropar 3.1–3.5 | Ej byggd | Terminalval (punkt 1) |
| Fysisk drivrutin mot kontrollenhet | Ej byggd | Terminalval (punkt 1–2) |
| Certifiering mot vald terminal | Ej påbörjad | Terminalval (punkt 3) |
| Blackbox-verifiering mot Skatteverket | Separat modul, ej i deklaration | — |

## 6. Nästa steg när terminal är vald

1. Klargör modell A eller B (avsnitt 4) — detta är ett avtalsbeslut.
2. Vid modell A: överskrid `_blackbox_transport()` mot terminalens API.
3. Vid modell A: bygg POS-frontend som anropar metoderna i avsnitt 3.
4. Uppdatera `docs/tillverkardeklaration.md` — ny version kräver ny
   deklaration enligt `docs/versionspolicy.md`.
5. Skicka deklaration till Skatteverket senast 14 dagar före utrullning
   (SKVFS 2021:17 8 kap.).

---

*Vertel Sverige AB*
