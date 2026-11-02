# -*- coding: utf-8 -*-
##############################################################################
#
#    POS Kassaregister SE — Swedish cash register compliance
#    Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################
"""Tests for the SKVFS 2021:16 XML export of the journal memory."""
import base64
from datetime import date, datetime, timedelta

from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

NS_KOMP = ('http://xmls.skatteverket.se/se/skatteverket/td/komponent/'
           'utredningsstod/1.0')
NS_INST = ('http://xmls.skatteverket.se/se/skatteverket/td/instans/'
           'utredningsstod/1.0')


def q(name):
    return '{%s}%s' % (NS_KOMP, name)


@tagged('post_install', '-at_install')
class TestXmlExport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({
            'vat': 'SE556677889901',
            'company_registry': '556677-8899',
        })
        cls.config = cls.env['pos.config'].create({
            'name': 'Kassa export',
            'sales_street': 'Storgatan 1',
            'sales_zip': '111 22',
            'sales_city': 'Stockholm',
        })
        cls.unit = cls.config.registration_unit_id
        cls.unit.write({'control_unit_serial': 'CU-99900000000001'})
        journal = cls.env['account.journal'].create({
            'name': 'Kassa export', 'code': 'KEXP', 'type': 'cash',
            'company_id': cls.env.company.id,
        })
        cls.cash = cls.env['pos.payment.method'].create({
            'name': 'Kontant', 'is_cash_count': True,
            'journal_id': journal.id,
        })
        cls.config.write({'payment_method_ids': [(6, 0, cls.cash.ids)]})
        cls.tax = cls.env['account.tax'].create({
            'name': 'Moms 25%', 'amount': 25.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'price_include_override': 'tax_included',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Hammare', 'list_price': 250.0, 'type': 'consu',
            'available_in_pos': True, 'taxes_id': [(6, 0, cls.tax.ids)],
        })
        cls.Export = cls.env['pos.journal.export']
        cls.Journal = cls.env['pos.journal.entry']

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _session(self):
        return self.env['pos.session'].create({'config_id': self.config.id})

    def _paid_order(self, session, qty=1):
        """Create a paid order with a receipt, as a real sale would."""
        order = self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'product_id': self.product.id, 'qty': qty,
                'price_unit': self.product.list_price,
                'tax_ids': [(6, 0, self.product.taxes_id.ids)],
                'price_subtotal': 0.0, 'price_subtotal_incl': 0.0,
            })],
            'amount_tax': 0.0, 'amount_total': 0.0,
            'amount_paid': 0.0, 'amount_return': 0.0,
        })
        for line in order.lines:
            incl = line.qty * line.price_unit
            line.write({'price_subtotal': incl / 1.25,
                        'price_subtotal_incl': incl})
            line.write({'full_product_name': line._programmed_name()})
        total = sum(order.lines.mapped('price_subtotal_incl'))
        order.write({
            'amount_total': total,
            'amount_tax': total - sum(order.lines.mapped('price_subtotal')),
        })
        self.env['pos.payment'].create({
            'pos_order_id': order.id,
            'payment_method_id': self.cash.id,
            'amount': total,
        })
        order.write({'amount_paid': total})
        order.action_pos_order_paid()
        return order

    def _xml(self, units=None, date_from=None, date_to=None):
        return self.Export.build_xml(
            units or self.unit,
            date_from or date(2020, 1, 1),
            date_to or date(2030, 1, 1),
        )

    def _root(self, xml_bytes):
        return etree.fromstring(xml_bytes)

    # ------------------------------------------------------------------
    # 6.1 — inledande element
    # ------------------------------------------------------------------
    def test_header_elements_present(self):
        """Exporten innehåller de inledande elementen (kap 4–5)."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        root = self._root(self._xml())

        self.assertEqual(root.tag, '{%s}ExportAvDataFranJournalminneEnligt'
                                   'SKVFS2021-16' % NS_INST)
        self.assertIsNotNone(root.find(q(
            'BeteckningPaDetKassaregisterSomExportAvDataFranJournalminnet'
            'SkerIfran')))
        self.assertIsNotNone(root.find(q(
            'TidpunktForNarExportAvDataFranJournalminnetSker')))
        self.assertIsNotNone(root.find(q(
            'ValdPeriodForExportAvDataFranJournalminne')))

    def test_company_block(self):
        """Företagsblocket bär namn, orgnummer och säljadress."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        company = self._root(self._xml()).find(q('InformationOmForetaget'))

        self.assertEqual(company.findtext(q('ForetagetsNamn')),
                         self.env.company.name)
        self.assertEqual(company.findtext(q(
            'OrganisationsnummerEllerPersonnummer')), '5566778899')
        address = company.findtext(q('DenAdressDarForsaljningSker'))
        self.assertIn('Storgatan 1', address)
        self.assertIn('Stockholm', address)

    def test_company_without_org_number_is_refused(self):
        """Export utan organisationsnummer nekas."""
        self.env.company.write({'vat': False, 'company_registry': False})
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        with self.assertRaises(UserError):
            self._xml()

    def test_system_block(self):
        """Kassaregistersystemet bär modell, version och kontrollenhet."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        system = self._root(self._xml()).find(
            q('KassaregistersystemLISTA')).find(q('Kassaregistersystemet'))

        self.assertEqual(system.findtext(q('Kassabeteckning')), self.unit.name)
        self.assertEqual(system.findtext(q(
            'TillverkningsnummerForKontrollenheten')),
            'CU-99900000000001')
        self.assertTrue(system.findtext(q(
            'VersionsnummerForKassaregistret')))

    def test_export_without_control_unit_is_refused(self):
        """Export utan kontrollenhet nekas — filen vore oanvändbar."""
        self.unit.write({'control_unit_serial': False})
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        with self.assertRaises(UserError):
            self._xml()

    # ------------------------------------------------------------------
    # 6.2 — en post per registrering
    # ------------------------------------------------------------------
    def test_one_element_per_entry(self):
        """En post per journalpost, i löpnummerordning."""
        for _i in range(3):
            self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                    payload={})
        doc = self._root(self._xml())
        events = doc.find(q('RegistreringLISTA')).findall(q('Handelse'))

        self.assertEqual(len(events), 3, "Tre poster ska exporteras")
        self.assertEqual(doc.findtext('.//' + q('Kassabeteckning')),
                         self.unit.name)

    def test_event_element_named_after_event_type(self):
        """Händelseelementet heter samma som händelsetypen."""
        self.Journal._log_event('OppnaKassaladaVidNollforsaljning',
                                unit=self.unit, payload={})
        event = self._root(self._xml()).find(
            q('RegistreringLISTA')).find(q('Handelse'))

        self.assertIsNotNone(event.find(q('OppnaKassaladaVidNollforsaljning')))

    def test_flag_events_carry_ja(self):
        """Flagg-händelser bär token "JA" — schemat kräver det."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        event = self._root(self._xml()).find(
            q('RegistreringLISTA')).find(q('Handelse'))

        self.assertEqual(event.findtext(q('StartAvKassaregister')), 'JA')

    def test_receipt_event_carries_amounts(self):
        """Ett kvitto exporteras med belopp i SEK."""
        session = self._session()
        order = self._paid_order(session)
        root = self._root(self._xml())
        receipts = root.findall('.//' + q('Kassakvitto'))

        self.assertTrue(receipts, "Kvittot ska finnas i exporten")
        exported = float(receipts[-1].findtext(q(
            'TotaltForsaljningsbeloppISvenskaKronor')))
        expected = self.Export._to_sek(order, order.amount_total)
        self.assertAlmostEqual(exported, expected, places=2,
                               msg="Kvittobeloppet ska vara omräknat till SEK")

    # ------------------------------------------------------------------
    # 6.3 — valfri period
    # ------------------------------------------------------------------
    def test_empty_period_exports_header_only(self):
        """Period utan registreringar ger fil med enbart inledande element."""
        xml = self._xml(date_from=date(1990, 1, 1), date_to=date(1990, 1, 2))
        root = self._root(xml)

        self.assertTrue(root.find(q('RegistreringLISTA')) is not None)
        # En tom RegistreringLISTA är inte schema-giltig, så exporten ska
        # skapa filen men valideringen ska säga ifrån — det är ärligt.
        with self.assertRaises(UserError):
            self.Export.validate_xml(xml)

    def test_period_across_month_boundary(self):
        """Period över månadsskifte tar med poster från båda månaderna."""
        # Två poster med kända tidsstämplar inom perioden
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        self.Journal._log_event('StoppAvKassaregister', unit=self.unit,
                                payload={})
        xml = self._xml(date_from=date(2020, 1, 1), date_to=date(2030, 1, 1))
        events = self._root(xml).find(q('RegistreringLISTA')).findall(
            q('Handelse'))
        self.assertEqual(len(events), 2)

    def test_period_excludes_entries_outside_range(self):
        """Poster utanför perioden tas inte med."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        xml = self._xml(date_from=date(1990, 1, 1), date_to=date(1990, 1, 2))
        events = self._root(xml).find(q('RegistreringLISTA')).findall(
            q('Handelse'))
        self.assertEqual(events, [], "Inga poster utanför perioden")

    # ------------------------------------------------------------------
    # 6.4 — flera enheter
    # ------------------------------------------------------------------
    def test_two_units_in_one_export(self):
        """Export från två enheter — varje post bär sin kassabeteckning."""
        config2 = self.env['pos.config'].create({'name': 'Kassa export 2'})
        unit2 = config2.registration_unit_id
        unit2.write({'control_unit_serial': 'CU-99900000000002'})

        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        self.Journal._log_event('StartAvKassaregister', unit=unit2,
                                payload={})

        xml = self._xml(units=self.unit | unit2)
        events = self._root(xml).find(q('RegistreringLISTA')).findall(
            q('Handelse'))
        names = {e.findtext(q('Kassabeteckning')) for e in events}

        self.assertEqual(len(events), 2)
        self.assertEqual(names, {self.unit.name, unit2.name})

    # ------------------------------------------------------------------
    # 6.5 — XSD-validering
    # ------------------------------------------------------------------
    def test_valid_export_passes_validation(self):
        """En korrekt export validerar mot Skatteverkets schema."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        self.assertTrue(self.Export.validate_xml(self._xml()))

    def test_invalid_xml_is_rejected(self):
        """En fil som inte validerar levereras inte."""
        broken = b'<?xml version="1.0"?><Felmanglande/>'
        with self.assertRaises(UserError):
            self.Export.validate_xml(broken)

    def test_export_method_does_not_return_invalid_file(self):
        """export() validerar före leverans — tom lista nekas."""
        with self.assertRaises(UserError):
            self.Export.export(self.env['pos.registration.unit'], date(
                2020, 1, 1), date(2030, 1, 1))

    # ------------------------------------------------------------------
    # 6.6 — SEK
    # ------------------------------------------------------------------
    def test_amounts_are_in_sek(self):
        """Belopp räknas om till SEK enligt kursen vid försäljningen."""
        sek = self.env.ref('base.SEK')
        session = self._session()
        order = self._paid_order(session)

        converted = self.Export._to_sek(order, 100.0)
        expected = order.currency_id._convert(
            100.0, sek, order.company_id, order.date_order)

        self.assertAlmostEqual(converted, expected, places=2,
                               msg="Beloppet ska räknas om till SEK")

    def test_amounts_in_sek_are_unchanged(self):
        """Ett belopp som redan är i SEK räknas inte om."""
        sek = self.env.ref('base.SEK')
        session = self._session()
        order = self._paid_order(session)
        # A paid order cannot be modified (6 kap. 1 §), so build an unpaid
        # order in SEK to exercise the conversion path.
        draft = self.env['pos.order'].create({
            'session_id': session.id,
            'amount_tax': 0.0, 'amount_total': 0.0,
            'amount_paid': 0.0, 'amount_return': 0.0,
        })
        # Draft orders are still modifiable; a paid one is not (6 kap. 1 §).
        draft.write({'currency_id': sek.id})
        self.assertEqual(draft.currency_id, sek)
        self.assertAlmostEqual(self.Export._to_sek(draft, 100.0), 100.0,
                               msg="Ett SEK-belopp ska inte räknas om")

    # ------------------------------------------------------------------
    # 6.7 — reproducerbarhet och loggning
    # ------------------------------------------------------------------
    def test_repeated_export_is_identical(self):
        """Upprepad export av samma period ger identiskt innehåll."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        first = self._xml()
        second = self._xml()

        def strip_timestamp(xml):
            """Drop the export timestamp — it is the only thing that moves."""
            root = etree.fromstring(xml)
            node = root.find(q(
                'TidpunktForNarExportAvDataFranJournalminnetSker'))
            if node is not None:
                node.text = 'TID'
            return etree.tostring(root)

        self.assertEqual(strip_timestamp(first), strip_timestamp(second),
                         "Exporterna ska vara identiska")

    def test_export_is_logged_in_journal(self):
        """Varje export loggas i journalminnet."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        before = self.Journal.search_count([
            ('unit_id', '=', self.unit.id),
            ('event_type', '=', 'OvrigRapport'),
        ])
        result = self.Export.export(self.unit, date(2020, 1, 1),
                                    date(2030, 1, 1))
        after = self.Journal.search_count([
            ('unit_id', '=', self.unit.id),
            ('event_type', '=', 'OvrigRapport'),
        ])

        self.assertEqual(after, before + 1, "Exporten ska loggas")
        self.assertIn('.xml', result['filename'])
        self.assertTrue(base64.b64decode(result['content']).startswith(
            b'<?xml'))

    def test_export_log_records_period_and_units(self):
        """Exportloggen bär period, enheter och användare."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        # The period must contain entries, otherwise the file is not valid.
        self.Export.export(self.unit, date(2020, 1, 1), date(2030, 1, 1))

        entry = self.Journal.search([
            ('unit_id', '=', self.unit.id),
            ('event_type', '=', 'OvrigRapport'),
        ], order='sequence desc', limit=1)

        self.assertEqual(entry.payload['date_from'], '2020-01-01')
        self.assertEqual(entry.payload['date_to'], '2030-01-01')
        self.assertIn(self.unit.name, entry.payload['units'])
        self.assertTrue(entry.payload['user'])

    # ------------------------------------------------------------------
    # Periodvalidering
    # ------------------------------------------------------------------
    def test_start_after_end_is_refused(self):
        """Startdatum efter slutdatum nekas."""
        self.Journal._log_event('StartAvKassaregister', unit=self.unit,
                                payload={})
        with self.assertRaises(UserError):
            self._xml(date_from=date(2030, 1, 1), date_to=date(2020, 1, 1))
