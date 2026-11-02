# Testprotokoll — pos_kassaregister_se

**Modul:** `pos_kassaregister_se`
**Version:** 18.0.1.5.0
**Testdatum:** 2026-11-02
**Testmiljö:** Odoo 18.0-20261012, databas `pos_kass_test`, PostgreSQL
**Testmetod:** Automatiska enhetstester i Odoo:s testramverk, kompletterade
med XSD-validering av exporten.

Testnamnen nedan är hämtade ur källkoden. Varje rad motsvarar en metod i
`tests/` och kan köras om var för sig.

---

## 1. Sammanfattning

| Testfil | Antal tester | Resultat |
|---|---|---|
| `test_dagrapporter.py` | 19 | Godkänd |
| `test_journal_entry.py` | 9 | Godkänd |
| `test_journalminne_handelser.py` | 12 | Godkänd |
| `test_kvittoutskrift.py` | 19 | Godkänd |
| `test_otillatna_funktioner.py` | 14 | Godkänd |
| `test_registration_unit.py` | 7 | Godkänd |
| `test_xml_export.py` | 22 | Godkänd |
| **Summa** | **102** | **102 godkända, 0 underkända** |

Kommando:

```bash
odoo -c /etc/odoo/odoo.conf -d pos_kass_test \
     --update=pos_kassaregister_se --test-enable \
     --log-level=test --stop-after-init --no-http
```

Returkod `0` = samtliga tester godkända.

---

## 2. Testpunkter per krav

### 2.4 Dagrapporter (7 kap. 3 §)

| # | Testpunkt | Krav | Testmetod | Resultat |
|---|---|---|---|---|
| 1 | Z-rapport skapas vid stängning | 7:3 | `test_dagrapporter.test_z_report_created_on_session_close` | Godkänd |
| 2 | Z-rapporten hämtas utan att återskapas | 7:3 | `test_dagrapporter.test_z_report_is_retrievable_without_recreation` | Godkänd |
| 3 | Ingen Z-rapport för oanvänd enhet | 7:3 | `test_dagrapporter.test_no_z_report_for_unused_unit` | Godkänd |
| 4 | Z-rapporten har obligatoriska fält | 7:3 | `test_dagrapporter.test_z_report_mandatory_fields` | Godkänd |
| 5 | Retur i betalningsfördelning, ej i kvittoantal | 7:3 | `test_dagrapporter.test_return_in_payment_breakdown_not_in_receipt_count` | Godkänd |
| 6 | Momsuppdelning bortser från returer | 7:3 | `test_dagrapporter.test_tax_breakdown_ignores_returns` | Godkänd |
| 7 | Nollförsäljningsdag visar noll kvitton | 7:3 | `test_dagrapporter.test_zero_sales_day_reports_zero_receipts` | Godkänd |
| 8 | Lådöppningar räknas | 7:3 | `test_dagrapporter.test_drawer_openings_counted` | Godkänd |
| 9 | Z-löpnumret är obrutet | 7:3 | `test_dagrapporter.test_z_sequence_is_unbroken` | Godkänd |
| 10 | Z-serien är skild från journalminnets serie | 7:3 | `test_dagrapporter.test_z_sequence_separate_from_journal_sequence` | Godkänd |
| 11 | X-rapporten stänger inte sessionen | 7:3 | `test_dagrapporter.test_x_report_does_not_close_session` | Godkänd |
| 12 | X-rapporten förbrukar inget Z-löpnummer | 7:3 | `test_dagrapporter.test_x_report_consumes_no_z_sequence` | Godkänd |
| 13 | X och Z visar samma siffror | 7:3 | `test_dagrapporter.test_x_report_has_same_figures_as_z` | Godkänd |
| 14 | Z-rapporten loggas i journalminnet | 4:10 | `test_dagrapporter.test_z_report_logged_in_journal` | Godkänd |
| 15 | X-rapporten loggas i journalminnet | 4:10 | `test_dagrapporter.test_x_report_logged_in_journal` | Godkänd |
| 16 | Svensk tid vid sommartid | 7:3 | `test_dagrapporter.test_swedish_time_under_dst` | Godkänd |
| 17 | Svensk tid vid vintertid | 7:3 | `test_dagrapporter.test_swedish_time_winter` | Godkänd |
| 18 | Z-rapporten kan inte ändras | 7:3 | `test_dagrapporter.test_z_report_cannot_be_modified` | Godkänd |
| 19 | Z-rapporten kan inte raderas | 7:3 | `test_dagrapporter.test_z_report_cannot_be_deleted` | Godkänd |

### 2.2 Journalminne — grund (4 kap. 10 §)

| # | Testpunkt | Krav | Testmetod | Resultat |
|---|---|---|---|---|
| 20 | Löpnumret är utan luckor | 4:10 | `test_journal_entry.test_t3_sequence_is_unbroken` | Godkänd |
| 21 | Raderad artikel finns kvar i journalminnet | 4:10 | `test_journal_entry.test_t3_deleted_article_stays_in_journal` | Godkänd |
| 22 | ORM-write blockeras | 4:10 | `test_journal_entry.test_t4_orm_write_blocked` | Godkänd |
| 23 | ORM-unlink blockeras | 4:10 | `test_journal_entry.test_t4_orm_unlink_blocked` | Godkänd |
| 24 | Kedjan är intakt | 4:10 | `test_journal_entry.test_t5_chain_intact` | Godkänd |
| 25 | Kedjan upptäcker manipulation | 4:10 | `test_journal_entry.test_t5_chain_detects_tampering` | Godkänd |
| 26 | Okänd händelsetyp avvisas | 4:10 | `test_journal_entry.test_unknown_event_type_rejected` | Godkänd |
| 27 | Belopp och payload lagras | 4:10 | `test_journal_entry.test_amount_and_payload_stored` | Godkänd |
| 28 | DB-skydd återkallar skrivrättigheter | 4:10 | `test_journal_entry.test_db_guard_revokes_write_privileges` | Godkänd |

### 2.3 Journalminne — händelser (4 kap. 4–10 §§)

| # | Testpunkt | Krav | Testmetod | Resultat |
|---|---|---|---|---|
| 29 | Parkering av artikel loggas | 4:5 | `test_journalminne_handelser.test_parking_is_logged` | Godkänd |
| 30 | Återupptagen parkering loggas | 4:5 | `test_journalminne_handelser.test_resume_parking_is_logged` | Godkänd |
| 31 | Raderad parkerad artikel loggas | 4:5 | `test_journalminne_handelser.test_delete_parked_is_logged` | Godkänd |
| 32 | Ändrad parkerad artikel loggas | 4:5 | `test_journalminne_handelser.test_change_parked_is_logged` | Godkänd |
| 33 | Kassalåda öppnad utan försäljning loggas | 4:4 | `test_journalminne_handelser.test_drawer_opening_without_sale_is_logged` | Godkänd |
| 34 | Lådöppningar räknas i Z-dagrapporten | 7:3 | `test_journalminne_handelser.test_drawer_openings_counted_in_z_report` | Godkänd |
| 35 | Ändrad växelkassa loggas | 4:6 | `test_journalminne_handelser.test_cash_float_change_is_logged` | Godkänd |
| 36 | Öppningsväxelkassan loggas | 4:6 | `test_journalminne_handelser.test_opening_float_is_logged` | Godkänd |
| 37 | Prisförfrågan loggas | 4:9 | `test_journalminne_handelser.test_price_inquiry_is_logged` | Godkänd |
| 38 | Använd clear-funktionen loggas | 4:9 | `test_journalminne_handelser.test_clear_is_logged` | Godkänd |
| 39 | Klockjustering loggas | 4:10 | `test_journalminne_handelser.test_clock_adjustment_is_logged` | Godkänd |
| 40 | Kedjan håller efter de nya händelserna | 4:10 | `test_journalminne_handelser.test_chain_remains_valid_after_new_events` | Godkänd |

### 2.5 Kvittoutskrift (7 kap. 1 §)

| # | Testpunkt | Krav | Testmetod | Resultat |
|---|---|---|---|---|
| 41 | Kvittot har samtliga obligatoriska fält (a–m) | 7:1 | `test_kvittoutskrift.test_receipt_has_all_mandatory_fields` | Godkänd |
| 42 | Kvitto med både varor och tjänster | 7:1 | `test_kvittoutskrift.test_receipt_with_goods_and_services` | Godkänd |
| 43 | Kvitto med enbart tjänster | 7:1 | `test_kvittoutskrift.test_receipt_with_only_services` | Godkänd |
| 44 | Kvitto med enbart varor | 7:1 | `test_kvittoutskrift.test_receipt_with_only_goods` | Godkänd |
| 45 | Moms per skattesats i klartext | 7:1 | `test_kvittoutskrift.test_vat_split_per_rate_in_plain_text` | Godkänd |
| 46 | Kvittot använder försäljningsställets adress | 7:1 | `test_kvittoutskrift.test_receipt_uses_sales_location_address` | Godkänd |
| 47 | Kvitto nekas utan adress | 7:1 | `test_kvittoutskrift.test_receipt_refused_without_address` | Godkänd |
| 48 | Retur förbrukar ett löpnummer | 7:1 | `test_kvittoutskrift.test_return_consumes_a_number` | Godkänd |
| 49 | Kopia förbrukar inget löpnummer | 7:1 | `test_kvittoutskrift.test_copy_consumes_no_number` | Godkänd |
| 50 | Andra kopian nekas | 7:1 | `test_kvittoutskrift.test_second_copy_is_refused` | Godkänd |
| 51 | Två kassor har separata serier | 7:1 | `test_kvittoutskrift.test_two_registers_have_separate_series` | Godkänd |
| 52 | Belopp i SEK vid utländsk valuta | 7:1 | `test_kvittoutskrift.test_amount_in_sek_when_foreign_currency` | Godkänd |
| 53 | Kontrollenheten signerar alla kvittotyper | 7:1 | `test_kvittoutskrift.test_control_unit_signs_every_receipt_kind` | Godkänd |
| 54 | Kvitto nekas när kontrollenheten inte svarar | 7:1 | `test_kvittoutskrift.test_receipt_refused_when_control_unit_unreachable` | Godkänd |
| 55 | Kvittot visar kassabeteckning med löpnummer | 7:1 | `test_kvittoutskrift.test_receipt_shows_register_name_with_sequence` | Godkänd |
| 56 | Modellbeteckningen innehåller "SE" | 7:1 | `test_kvittoutskrift.test_model_designation_contains_se` | Godkänd |
| 57 | Kvittot kan inte ändras | 7:1 | `test_kvittoutskrift.test_receipt_cannot_be_modified` | Godkänd |
| 58 | Kvittot kan inte raderas | 7:1 | `test_kvittoutskrift.test_receipt_cannot_be_deleted` | Godkänd |
| 59 | QWeb-mallen renderar markeringstexterna | 7:1 | `test_kvittoutskrift.test_receipt_template_renders_markings` | Godkänd |

### 2.6 Spärrar mot otillåtna funktioner (6 kap.)

| # | Testpunkt | Krav | Testmetod | Resultat |
|---|---|---|---|---|
| 60 | Betald order kan inte ändras | 6:1 | `test_otillatna_funktioner.test_paid_order_cannot_be_modified` | Godkänd |
| 61 | Avslutad order kan inte ändras | 6:1 | `test_otillatna_funktioner.test_done_order_cannot_be_modified` | Godkänd |
| 62 | Artikelbenämningen låses efter betalning | 6:4 | `test_otillatna_funktioner.test_order_line_name_locked_after_payment` | Godkänd |
| 63 | Betald order kan inte raderas | 6:1 | `test_otillatna_funktioner.test_paid_order_cannot_be_deleted` | Godkänd |
| 64 | Utkast kan inte raderas när registret är aktivt | 6:1 | `test_otillatna_funktioner.test_draft_order_cannot_be_deleted_when_register_active` | Godkänd |
| 65 | Ingen betald order när kvittoproduktionen fallerar | 6:1 | `test_otillatna_funktioner.test_no_paid_order_when_receipt_production_fails` | Godkänd |
| 66 | Tredje utskriften nekas | 6:1 | `test_otillatna_funktioner.test_third_print_is_refused` | Godkänd |
| 67 | action_print_receipt nekar tredje utskriften | 6:1 | `test_otillatna_funktioner.test_action_print_receipt_refuses_third_print` | Godkänd |
| 68 | Artikelbenämningen kan inte ersättas med fritext | 6:4 | `test_otillatna_funktioner.test_article_name_cannot_be_replaced_with_free_text` | Godkänd |
| 69 | Artikelbenämningen motsvarar produkten | 6:4 | `test_otillatna_funktioner.test_article_name_equals_product_name` | Godkänd |
| 70 | Markeringstexterna är dubbelt så stora som beloppet | 7:1 | `test_otillatna_funktioner.test_marking_texts_are_twice_the_amount_size` | Godkänd |
| 71 | Övningsläget påverkar inte Z-rapporten | 7:1 | `test_otillatna_funktioner.test_training_mode_does_not_affect_z_report` | Godkänd |
| 72 | Övningsläget loggas i journalminnet | 7:1 | `test_otillatna_funktioner.test_training_mode_is_logged_in_journal_memory` | Godkänd |
| 73 | Övningskvittot förbrukar inget löpnummer | 7:1 | `test_otillatna_funktioner.test_training_receipt_consumes_no_number` | Godkänd |

### 2.1 Registreringsenhet (7 kap. 1 §)

| # | Testpunkt | Krav | Testmetod | Resultat |
|---|---|---|---|---|
| 74 | En registreringsenhet skapas per kassa | 7:1 | `test_registration_unit.test_t1_unit_created_per_config` | Godkänd |
| 75 | Enheten har en egen löpnummerserie | 4:10 | `test_registration_unit.test_t1_unit_has_sequence` | Godkänd |
| 76 | Modellbeteckningen måste innehålla "SE" | 7:1 | `test_registration_unit.test_t2_model_designation_requires_se` | Godkänd |
| 77 | Modellbeteckning med "SE" godtas | 7:1 | `test_registration_unit.test_t2_model_designation_se_accepted` | Godkänd |
| 78 | Modellbeteckningen är skiftlägesoberoende | 7:1 | `test_registration_unit.test_t2_model_designation_case_insensitive` | Godkänd |
| 79 | Separata serier per enhet | 7:3 | `test_registration_unit.test_t6_separate_series_per_unit` | Godkänd |
| 80 | Session nekas utan fullständig enhet | 7:1 | `test_registration_unit.test_session_blocked_without_complete_unit` | Godkänd |

### 2.7 XML-export (SKVFS 2021:16)

| # | Testpunkt | Krav | Testmetod | Resultat |
|---|---|---|---|---|
| 81 | Exporten innehåller de inledande elementen | 4 kap. | `test_xml_export.test_header_elements_present` | Godkänd |
| 82 | Företagsblocket bär namn, orgnummer och adress | 5 kap. | `test_xml_export.test_company_block` | Godkänd |
| 83 | Export utan organisationsnummer nekas | 5 kap. | `test_xml_export.test_company_without_org_number_is_refused` | Godkänd |
| 84 | Kassaregistersystemet bär modell, version och kontrollenhet | 5 kap. | `test_xml_export.test_system_block` | Godkänd |
| 85 | Export utan kontrollenhet nekas | 5 kap. | `test_xml_export.test_export_without_control_unit_is_refused` | Godkänd |
| 86 | En post per journalpost | 6 kap. | `test_xml_export.test_one_element_per_entry` | Godkänd |
| 87 | Händelseelementet heter som händelsetypen | 6–36 kap. | `test_xml_export.test_event_element_named_after_event_type` | Godkänd |
| 88 | Flagg-händelser bär token "JA" | 6–36 kap. | `test_xml_export.test_flag_events_carry_ja` | Godkänd |
| 89 | Kvittot exporteras med belopp | 12 kap. | `test_xml_export.test_receipt_event_carries_amounts` | Godkänd |
| 90 | Tom period ger fil med enbart huvud | 4 kap. | `test_xml_export.test_empty_period_exports_header_only` | Godkänd |
| 91 | Period över månadsskifte | 4 kap. | `test_xml_export.test_period_across_month_boundary` | Godkänd |
| 92 | Poster utanför perioden utesluts | 4 kap. | `test_xml_export.test_period_excludes_entries_outside_range` | Godkänd |
| 93 | Två enheter i en export | 4 kap. | `test_xml_export.test_two_units_in_one_export` | Godkänd |
| 94 | Giltig export validerar mot XSD | 4 kap. | `test_xml_export.test_valid_export_passes_validation` | Godkänd |
| 95 | Ogiltig fil avvisas | 4 kap. | `test_xml_export.test_invalid_xml_is_rejected` | Godkänd |
| 96 | export() levererar inte ogiltig fil | 4 kap. | `test_xml_export.test_export_method_does_not_return_invalid_file` | Godkänd |
| 97 | Belopp räknas om till SEK | 4 kap. | `test_xml_export.test_amounts_are_in_sek` | Godkänd |
| 98 | SEK-belopp räknas inte om | 4 kap. | `test_xml_export.test_amounts_in_sek_are_unchanged` | Godkänd |
| 99 | Upprepad export ger identiskt innehåll | 4 kap. | `test_xml_export.test_repeated_export_is_identical` | Godkänd |
| 100 | Exporten loggas i journalminnet | 4:10 | `test_xml_export.test_export_is_logged_in_journal` | Godkänd |
| 101 | Exportloggen bär period, enheter och användare | 4:10 | `test_xml_export.test_export_log_records_period_and_units` | Godkänd |
| 102 | Startdatum efter slutdatum nekas | 4 kap. | `test_xml_export.test_start_after_end_is_refused` | Godkänd |

---

## 3. XSD-validering

Exporten valideras mot Skatteverkets instansschema:

```
schemas/xmls/instans/utredningsstod/2021-12-08/
    ExportAvDataFranJournalminneEnligtSKVFS202116-2021-12-08.xsd
```

Schemat och dess tre komponentfiler medföljer modulen. Valideringen sker
automatiskt i `pos.journal.export.validate_xml()` och är obligatorisk
innan en fil lämnas ut.

**Verifierat:** en export med fullständigt huvud och minst en händelse
validerar. En export med saknat organisationsnummer, saknad
kontrollenhet eller felaktigt elementnamn avvisas med ett felmeddelande
som namnger det felande elementet.

---

## 4. Underkända testpunkter

Inga.

---

*Protokollet upprättas per version. Vid ändring av reglerad funktion
upprättas ett nytt protokoll.*
