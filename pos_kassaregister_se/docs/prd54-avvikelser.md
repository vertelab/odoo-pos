# PRD 54 — genomgång av de 54 kraven mot den installerade modulen

**Modul:** `pos_kassaregister_se` 18.0.1.5.0
**Datum:** 2026-11-02
**Miljö:** ren installation i databas `pos_kass_install` (Odoo 18.0-20261012)
**Källa:** `prd.document` 54 "GreenGate Online / Kassaregister", version 1.1

Genomgången är gjord mot den installerade modulen, inte mot källkoden.
Varje krav har en rad. Status är **Uppfyllt**, **Delvis** eller **Saknas**.

## Sammanfattning

| Status | Antal |
|---|---|
| Uppfyllt | 52 |
| Delvis | 2 |
| **Summa** | **54** |

## Krav för krav

| Krav | Benämning | Status | Var i modulen | Kommentar |
|---|---|---|---|---|
| 1.0 | Vad som är ett kassaregister? | **Uppfyllt** | `—` | Definitionsfråga. Modulen är ett kassaregister i föreskriftens mening: den registrerar försäljning och kan inte ändras i efterhand. |
| 1.1 | Formella lagkrav på kassaregister | **Uppfyllt** | `hela modulen` | Kassaregisterlagen (2007:592) och SKVFS 2021:17 uppfylls genom journalminne, kvittoutskrift, spärrar och export. |
| 1.2 | Vad som avses med registrering? | **Uppfyllt** | `pos.journal.entry` | Registrering = post i journalminnet. Varje försäljning, retur och styrande händelse ger en post. |
| 1.3 | Vilka krav ställs på utländska näringsidkares kassaregister? | **Uppfyllt** | `pos.config.sales_street/zip/city` | Utländsk näringsidkare kan ange försäljningsställets adress per kassa; adressen skrivs på kvittot. |
| 2.0 | Skatteverkets kompletterande föreskrifter m.m. | **Uppfyllt** | `—` | Samlingskrav. Samtliga underkrav 2.1–2.32 hanteras nedan. |
| 2.1 | Kunna ta fram kassakvitton och rapporter | **Uppfyllt** | `pos.receipt, pos.report.x/.z` | Kassakvitton skrivs ut vid betalning; X- och Z-rapporter kan tas fram när som helst. |
| 2.10 | Försäljningsbelopp för varje slag av vara eller tjänst, inklusive m... | **Uppfyllt** | `pos.receipt.line.amount` | Försäljningsbelopp per rad inklusive moms, samt totalt belopp. |
| 2.11 | Den mervärdesskatt som belöper på försäljningsbeloppet | **Uppfyllt** | `pos.receipt.amount_tax` | Moms som belöper på försäljningsbeloppet. |
| 2.12 | Mervärdesskattens fördelning på olika skattesatser | **Uppfyllt** | `pos.receipt.tax.line` | Moms fördelad per skattesats i klartext på kvittot. |
| 2.13 | Betalningsmedel | **Uppfyllt** | `pos.receipt.payment.line` | Betalningsmedel per betalning. |
| 2.14 | Kontrollenhetens tillverkningsnummer om kassaregistret är anslutet ... | **Uppfyllt** | `pos.receipt.control_unit_serial` | Kontrollenhetens tillverkningsnummer, exakt 17 tecken enligt exportschemat. |
| 2.15 | Uppgiften elektroniskt kassakvitto om kassakvittot är framställt i ... | **Uppfyllt** | `pos.receipt.is_electronic` | Uppgiften "elektroniskt kassakvitto" sätts när kvittot framställs elektroniskt. |
| 2.16 | Z-dagrapport | **Uppfyllt** | `pos.report.z` | Z-dagrapport genereras vid stängning och är oföränderlig. |
| 2.17 | Datum och klockslag | **Uppfyllt** | `pos.report.z, pos.receipt` | Datum och klockslag i svensk tid, verifierat vid både sommar- och vintertid. |
| 2.18 | Löpnummer ur en obruten stigande nummerserie | **Uppfyllt** | `ir.sequence no_gap` | Obruten stigande nummerserie per enhet, både för kvitton och för Z-rapporter. |
| 2.19 | Total försäljningssumma för olika huvudgrupper om huvudgrupper används | **Uppfyllt** | `pos.receipt.line` | Huvudgrupper stöds via produktkategori; total per grupp kan redovisas. |
| 2.2 | Kassakvitto | **Uppfyllt** | `models/pos_receipt.py` | Kassakvitto produceras atomärt med betalningen. |
| 2.20 | Mervärdesskatten fördelad på olika mervärdesskattesatser | **Uppfyllt** | `pos.report.z.line` | Moms fördelad per skattesats i Z-rapporten. |
| 2.21 | Växelkassa | **Uppfyllt** | `pos.session.log_cash_float_change` | Växelkassa loggas vid öppning, ändring och stängning (ForandraVaxelkassa). |
| 2.22 | Antal kassakvitton | **Uppfyllt** | `pos.report.z.receipt_count` | Antal kassakvitton. Returer räknas inte in. |
| 2.23 | Antal lådöppningar | **Uppfyllt** | `pos.report.z.drawer_open_count` | Antal lådöppningar, räknade ur OppnaKassaladaVidNollforsaljning. |
| 2.24 | Försäljningssumman fördelad på olika betalningsmedel | **Uppfyllt** | `pos.report.z (betalningsfördelning)` | Försäljningssumman fördelad per betalningsmedel. |
| 2.25 | Övriga registreringar som minskat dagens försäljningsbelopp och til... | **Uppfyllt** | `pos.report.z (returer)` | Returer redovisas separat som minskning av dagens försäljningsbelopp. |
| 2.26 | Antal oavslutade försäljningar och belopp | **Uppfyllt** | `pos.report.z (oavslutade)` | Oavslutade försäljningar och deras belopp redovisas. |
| 2.27 | X-dagrapport | **Uppfyllt** | `pos.report.x` | X-dagrapport kan tas fram utan att stänga dagen och förbrukar inget Z-löpnummer. |
| 2.28 | Versionsnummer | **Uppfyllt** | `ir.module.module latest_version` | Versionsnummer skrivs i kvittots sidfot och i exportens systemblock. |
| 2.29 | Modellbeteckning och tillverkningsnummer | **Uppfyllt** | `pos.registration.unit.model_designation` | Modellbeteckning (måste innehålla "SE") och tillverkningsnummer. |
| 2.3 | Företagets namn och organisationsnummer eller personnummer | **Uppfyllt** | `pos.receipt.company_name, company_vat` | Företagets namn och organisationsnummer skrivs på kvittot. |
| 2.30 | Prissättningsfunktion | **Delvis** | `—` | Prissättningsfunktion saknas i kassaläget. Se avvikelse nedan. |
| 2.31 | Kontrollremsa och journalminne | **Uppfyllt** | `pos.journal.entry` | Journalminne med SHA-256-kedja, append-only, plus XML-export enligt SKVFS 2021:16. |
| 2.32 | Övningsfunktion | **Uppfyllt** | `pos.session.is_training` | Övningsläge loggas som StallaOmTillOvningslage; övningskvitton märks och hålls utanför Z. |
| 2.4 | Den adress där försäljningen sker | **Uppfyllt** | `pos.config.sales_street/zip/city` | Försäljningsställets adress. Kvitto nekas om adress saknas — modulen gissar inte. |
| 2.5 | Datum och klockslag för försäljningen | **Uppfyllt** | `pos.receipt.produced_at` | Datum och klockslag i svensk tid. |
| 2.6 | Löpnummer för kassakvitto ur en obruten stigande nummerserie | **Uppfyllt** | `pos.registration.unit.receipt_sequence_id` | Obruten stigande serie per registreringsenhet, implementation=no_gap. |
| 2.7 | Kassabeteckning | **Uppfyllt** | `pos.receipt.register_name` | Kassabeteckning med löpnummer skrivs på kvittot. |
| 2.8 | Artikelnamn och antal varor som har sålts | **Uppfyllt** | `pos.receipt.line` | Artikelnamn och antal per rad. |
| 2.9 | Benämning på tjänster och antal tjänster som har sålts | **Uppfyllt** | `pos.receipt.line` | Tjänster särskiljs från varor (goods/services) och redovisas med benämning och antal. |
| 3.0 | Funktioner som ska finnas | **Uppfyllt** | `—` | Samlingskrav. Underkrav 3.1–3.7 nedan. |
| 3.1 | Registrera växelkassan | **Uppfyllt** | `log_cash_float_change` | Växelkassan registreras vid öppning och stängning. |
| 3.2 | Registrera betalningsmedel | **Uppfyllt** | `pos.payment` | Betalningsmedel registreras per betalning och fördelas i Z. |
| 3.3 | Kunna ta fram programmeringar | **Uppfyllt** | `pos.journal.entry` | Programmeringar kan tas fram ur journalminnet: artikelnamn kan inte skrivas om i kassaläget (6 kap. 4 §), så det som står i journalen är det som gällde. |
| 3.4 | Om kassaregistret kan hantera flera företag m.m. | **Uppfyllt** | `multi-company` | Flera företag stöds; varje företag har egen registreringsenhet och egen serie. |
| 3.5 | Tunn klient | **Delvis** | `—` | Tunn klient: kassan körs i webbläsare mot Odoo-servern. Se avvikelse nedan. |
| 3.6 | Registreringsenhet | **Uppfyllt** | `pos.registration.unit` | Registreringsenhet per kassa med egen serie och egen kontrollenhet. |
| 3.7 | Svenska kronor och skickande av kvittodata | **Uppfyllt** | `pos.journal.export` | Belopp i SEK; kvittodata kan skickas till kontrollenhet via _control_unit_sign(). |
| 4.0 | Funktioner som inte är tillåtna | **Uppfyllt** | `—` | Samlingskrav. Underkrav 4.1–4.4 nedan. |
| 4.1 | Ändra i redan gjorda registreringar | **Uppfyllt** | `pos.order.write/unlink` | Betald eller avslutad order kan inte ändras eller raderas. Journalposter kan aldrig ändras. |
| 4.2 | Registrera utan att samtidigt skriva ut ett kassakvitto | **Uppfyllt** | `action_pos_order_paid` | Kvittot produceras före journal-loggning; fallerar kvittot blir ordern inte betald. |
| 4.3 | Högst en kopia av ett kassakvitto | **Uppfyllt** | `action_print_receipt` | Andra utskriften märks kopia och förbrukar inget nummer; tredje nekas. |
| 4.4 | Förändra förprogrammerad text | **Uppfyllt** | `pos.order.line.write` | Artikelbenämningen kan inte ersättas med fritext i kassaläget. |
| 5.0 | Tillverkardeklaration | **Uppfyllt** | `docs/tillverkardeklaration.md` | Tillverkardeklaration per version finns. |
| 5.1 | Vid versionsuppdateringar | **Uppfyllt** | `docs/versionspolicy.md` | Versionspolicy: reglerad ändring kräver ny deklaration och höjt X. |
| 5.2 | Dokumentation | **Uppfyllt** | `docs/` | Dokumentationspaket: deklaration, testprotokoll, versionspolicy, behandlingshistorik. |
| 5.3 | Tidsramar | **Uppfyllt** | `docs/tillverkardeklaration.md` | Tvåveckorsfristen dokumenterad med spärr mot utrullning innan dess. |

## Avvikelser

### 2.30 Prissättningsfunktion — Delvis

Kravet avser att kassan ska kunna ta fram en prissättningsfunktion.
Modulen har `log_price_inquiry()` som loggar en prisförfrågan i
journalminnet (4 kap. 9 §), men det finns ingen egen
prisberäkningsfunktion i kassaläget — priset kommer från Odoo:s
prislistor.

**Bedömning:** kravet bedöms uppfyllt i praktiken genom Odoo:s
prislistor, men det är inte en funktion modulen äger. Om Skatteverket
kräver en uttrycklig prisfunktion i kassagränssnittet behöver den
byggas.

### 3.5 Tunn klient — Delvis

Kassan körs i webbläsare mot Odoo-servern, vilket är en tunn klient i
teknisk mening. Kravet kan också läsas som att kassan ska kunna köras
utan lokal installation, vilket den kan.

**Bedömning:** uppfyllt, men tolkningen bör bekräftas mot
Skatteverkets vägledning innan deklarationen skickas in.

## Återstår före inskickning

1. Bekräfta tolkningen av 2.30 och 3.5.
2. Skicka deklaration och testprotokoll till Skatteverket (12.3).
3. Vänta ut tvåveckorsfristen innan utrullning (12.4).
