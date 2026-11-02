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
"""Tests for kassakvittot (SKVFS 2021:17 7 kap. 1 §).

Covers every scenario in ``specs/kassaregister/kvittoutskrift/spec.md``.
"""
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestKvittoutskrift(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({'vat': '556012345601'})
        cls.config = cls.env['pos.config'].create({'name': 'Kassa kvitto-test'})
        cls.unit = cls.config.registration_unit_id
        cls.unit.write({'control_unit_serial': 'CU-12345600000001'})
        cls.config.write({
            'sales_street': 'Storgatan 12',
            'sales_zip': '111 22',
            'sales_city': 'Stockholm',
        })
        cls.Receipt = cls.env['pos.receipt']

        journal_1 = cls.env['account.journal'].create({
            'name': 'Kassa ett', 'code': 'KSA1', 'type': 'cash',
            'company_id': cls.env.company.id,
        })
        cls.cash = cls.env['pos.payment.method'].create({
            'name': 'Kontant', 'is_cash_count': True,
            'journal_id': journal_1.id,
        })
        cls.config.write({'payment_method_ids': [(6, 0, cls.cash.ids)]})

        cls.tax_25 = cls.env['account.tax'].create({
            'name': 'Moms 25%', 'amount': 25.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'price_include_override': 'tax_included',
        })
        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'Moms 12%', 'amount': 12.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'price_include_override': 'tax_included',
        })
        cls.goods = cls.env['product.product'].create({
            'name': 'Kaffebryggare', 'list_price': 500.0, 'type': 'consu',
            'available_in_pos': True, 'taxes_id': [(6, 0, cls.tax_25.ids)],
        })
        cls.service = cls.env['product.product'].create({
            'name': 'Installation', 'list_price': 400.0, 'type': 'service',
            'available_in_pos': True, 'taxes_id': [(6, 0, cls.tax_12.ids)],
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _open_session(self, config=None):
        return self.env['pos.session'].create(
            {'config_id': (config or self.config).id})

    def _make_order(self, session, lines, method=None):
        method = method or self.cash
        order = self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'product_id': product.id,
                'qty': qty,
                'price_unit': product.list_price,
                'tax_ids': [(6, 0, product.taxes_id.ids)],
                'price_subtotal': 0.0,
                'price_subtotal_incl': 0.0,
            }) for product, qty in lines],
            'amount_tax': 0.0, 'amount_total': 0.0,
            'amount_paid': 0.0, 'amount_return': 0.0,
        })
        for line in order.lines:
            incl = line.qty * line.price_unit
            rate = line.tax_ids[:1].amount or 0.0
            line.write({
                'price_subtotal': incl / (1 + rate / 100.0),
                'price_subtotal_incl': incl,
            })
        order.write({
            'amount_total': sum(order.lines.mapped('price_subtotal_incl')),
            'amount_tax': sum(order.lines.mapped('price_subtotal_incl'))
                          - sum(order.lines.mapped('price_subtotal')),
        })
        self.env['pos.payment'].create({
            'pos_order_id': order.id,
            'payment_method_id': method.id,
            'amount': order.amount_total,
        })
        order.write({'amount_paid': order.amount_total})
        return order

    def _pay(self, order):
        order.action_pos_order_paid()
        return self.Receipt.search([('order_id', '=', order.id)], limit=1)

    # ------------------------------------------------------------------
    # Requirement: obligatoriska uppgifter a–m
    # ------------------------------------------------------------------
    def test_receipt_has_all_mandatory_fields(self):
        """Scenario: kvittot innehåller fälten a–m."""
        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        receipt = self._pay(order)

        self.assertTrue(receipt, "Ett kvitto ska framställas vid betalning")
        # a
        self.assertTrue(receipt.company_name, "a: företagsnamn")
        self.assertTrue(receipt.company_vat, "a: organisationsnummer")
        # b
        self.assertTrue(receipt.street, "b: gatuadress")
        self.assertTrue(receipt.city, "b: ortsnamn")
        # c
        self.assertTrue(receipt.produced_at, "c: datum och klockslag")
        # d
        self.assertTrue(receipt.sequence, "d: löpnummer")
        # e
        self.assertTrue(receipt.register_name, "e: kassabeteckning")
        # f, g, h
        self.assertTrue(receipt.line_ids, "f/g/h: artiklar och belopp")
        # i, j
        self.assertTrue(receipt.tax_line_ids, "i/j: moms per skattesats")
        # k
        self.assertTrue(receipt.payment_line_ids, "k: betalningsmedel")
        # l
        self.assertTrue(receipt.control_unit_serial,
                        "l: kontrollenhetens tillverkningsnummer")
        self.assertTrue(receipt.control_code, "l: kontrollkod")

    def test_receipt_with_goods_and_services(self):
        """Scenario: kvitto med både varor och tjänster."""
        session = self._open_session()
        order = self._make_order(
            session, [(self.goods, 1), (self.service, 1)])
        receipt = self._pay(order)

        self.assertEqual(len(receipt.line_ids), 2)
        goods_line = receipt.line_ids.filtered(
            lambda l: l.product_id == self.goods)
        service_line = receipt.line_ids.filtered(
            lambda l: l.product_id == self.service)
        self.assertFalse(goods_line.is_service, "Varor ska inte vara tjänster")
        self.assertTrue(service_line.is_service, "Tjänsten ska märkas som tjänst")
        self.assertEqual(goods_line.qty, 1)
        self.assertEqual(service_line.qty, 1)

    def test_receipt_with_only_services(self):
        """Scenario: enbart tjänster — inga varor med antalet noll."""
        session = self._open_session()
        order = self._make_order(session, [(self.service, 2)])
        receipt = self._pay(order)

        self.assertTrue(all(line.is_service for line in receipt.line_ids),
                        "Alla rader ska vara tjänster")
        self.assertFalse(
            receipt.line_ids.filtered(lambda l: not l.is_service),
            "Inga varor ska redovisas med antalet noll",
        )

    def test_receipt_with_only_goods(self):
        """Scenario: enbart varor — inga tjänster med antalet noll."""
        session = self._open_session()
        order = self._make_order(session, [(self.goods, 3)])
        receipt = self._pay(order)

        self.assertFalse(
            receipt.line_ids.filtered(lambda l: l.is_service),
            "Inga tjänster ska redovisas med antalet noll",
        )
        self.assertEqual(receipt.line_ids[0].qty, 3)

    def test_vat_split_per_rate_in_plain_text(self):
        """Fält j: momsen fördelas per skattesats i klartext."""
        session = self._open_session()
        order = self._make_order(
            session, [(self.goods, 1), (self.service, 1)])
        receipt = self._pay(order)

        rates = sorted(receipt.tax_line_ids.mapped('rate'))
        self.assertEqual(rates, [12.0, 25.0],
                         "Båda skattesatserna ska redovisas")
        for line in receipt.tax_line_ids:
            self.assertIn('moms', line.name.lower(),
                          "Skattesatsen ska anges i klartext")
            self.assertNotIn('.0', line.name,
                             "Satsen ska skrivas 25, inte 25.0")

    # ------------------------------------------------------------------
    # Requirement: adressen är försäljningsställets
    # ------------------------------------------------------------------
    def test_receipt_uses_sales_location_address(self):
        """Scenario: två butiker med olika adresser."""
        self.config.write({
            'sales_street': 'Avenyn 1',
            'sales_zip': '411 36',
            'sales_city': 'Göteborg',
        })

        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        receipt = self._pay(order)

        self.assertEqual(receipt.street, 'Avenyn 1',
                         "Butikens adress ska anges, inte huvudkontorets")
        self.assertEqual(receipt.city, 'Göteborg')

    def test_receipt_refused_without_address(self):
        """Scenario: adress saknas — kvittoframställning nekas."""
        self.config.write({
            'sales_street': False, 'sales_zip': False, 'sales_city': False,
        })
        self.env.company.write({'street': False, 'city': False})

        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        with self.assertRaises(UserError) as ctx:
            order.action_pos_order_paid()
        self.assertIn('adress', str(ctx.exception).lower(),
                      "Felmeddelandet ska ange att adress saknas")

    # ------------------------------------------------------------------
    # Requirement: obruten löpnummerserie per enhet
    # ------------------------------------------------------------------
    def test_return_consumes_a_number(self):
        """Scenario: retur förbrukar ett löpnummer."""
        session = self._open_session()
        sale = self._pay(self._make_order(session, [(self.goods, 1)]))
        ret = self._pay(self._make_order(session, [(self.goods, -1)]))

        self.assertEqual(ret.kind, 'return', "Kvittot ska vara ett returkvitto")
        self.assertEqual(ret.sequence, sale.sequence + 1,
                         "Returen får nästa nummer i serien")

    def test_copy_consumes_no_number(self):
        """Scenario: kopia förbrukar inget löpnummer."""
        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        sale = self._pay(order)
        next_before = self.unit.receipt_sequence_id.number_next_actual

        copy = self.Receipt._produce(order, kind='copy')

        self.assertEqual(copy.sequence, sale.sequence,
                         "Kopian bär det ursprungliga kvittots löpnummer")
        self.assertEqual(
            self.unit.receipt_sequence_id.number_next_actual, next_before,
            "Serien förbrukar inget nytt nummer")

    def test_second_copy_is_refused(self):
        """Scenario: en tredje utskrift nekas (6 kap. 3 §)."""
        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        self._pay(order)
        self.Receipt._produce(order, kind='copy')

        with self.assertRaises(UserError) as ctx:
            self.Receipt._produce(order, kind='copy')
        self.assertIn('kopia', str(ctx.exception).lower())

    def test_two_registers_have_separate_series(self):
        """Scenario: två kassor har separata serier."""
        cash_2 = self.env['pos.payment.method'].create({
            'name': 'Kontant kassa två',
            'is_cash_count': True,
            'journal_id': self.env['account.journal'].search(
                [('type', '=', 'cash'), ('id', '!=', self.cash.journal_id.id),
                 ('company_id', '=', self.env.company.id)],
                limit=1).id,
        })
        config_2 = self.env['pos.config'].create({'name': 'Kassa två'})
        unit_2 = config_2.registration_unit_id
        unit_2.write({'control_unit_serial': 'CU-99900000000003'})
        config_2.write({
            'payment_method_ids': [(6, 0, cash_2.ids)],
            'sales_street': 'Västra Hamngatan 3',
            'sales_city': 'Göteborg',
        })

        session_1 = self._open_session()
        receipt_1 = self._pay(self._make_order(session_1, [(self.goods, 1)]))

        session_2 = self._open_session(config_2)
        receipt_2 = self._pay(
            self._make_order(session_2, [(self.goods, 1)], method=cash_2))

        self.assertEqual(receipt_1.sequence, 1)
        self.assertEqual(receipt_2.sequence, 1,
                         "Varje enhet har sin egen serie")
        self.assertNotEqual(receipt_1.unit_id, receipt_2.unit_id)
        self.assertNotEqual(
            (receipt_1.register_name, receipt_1.sequence),
            (receipt_2.register_name, receipt_2.sequence),
            "Kassabeteckning + löpnummer identifierar kvittot unikt",
        )

    # ------------------------------------------------------------------
    # Requirement: belopp i svenska kronor
    # ------------------------------------------------------------------
    def test_amount_in_sek_when_foreign_currency(self):
        """Scenario: försäljning i EUR — beloppet anges även i SEK."""
        eur = self.env.ref('base.EUR', raise_if_not_found=False)
        sek = self.env.ref('base.SEK', raise_if_not_found=False)
        if not eur or not sek:
            self.skipTest("EUR/SEK saknas i databasen")

        self.config.write({'currency_id': eur.id})

        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        receipt = self._pay(order)

        self.assertEqual(receipt.currency_id, eur,
                         "Kvittot visar beloppet i EUR för kunden")

        # The SEK amount must be the EUR amount converted at the rate that
        # applies on the sale date — not a copy of the EUR amount.
        expected = eur._convert(
            order.amount_total, sek, order.company_id, order.date_order)
        self.assertAlmostEqual(receipt.amount_total_sek, expected, places=2,
                               msg="Motsvarande belopp i SEK ska anges")
        self.assertNotAlmostEqual(
            receipt.amount_total_sek, receipt.amount_total, places=2,
            msg="SEK-beloppet får inte vara samma som EUR-beloppet")

    # ------------------------------------------------------------------
    # Requirement: kontrollenhet
    # ------------------------------------------------------------------
    def test_control_unit_signs_every_receipt_kind(self):
        """Scenario: samtliga kvittotyper signeras."""
        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        sale = self._pay(order)
        self.assertTrue(sale.control_code, "Kassakvittot ska bära kontrollkod")

        copy = self.Receipt._produce(order, kind='copy')
        self.assertTrue(copy.control_code, "Kopian ska bära kontrollkod")

        training = self.Receipt._produce(order, kind='training')
        self.assertTrue(training.control_code,
                        "Övningskvittot ska bära kontrollkod")

    def test_receipt_refused_when_control_unit_unreachable(self):
        """Scenario: kontrollenheten svarar inte."""
        self.unit.write({'control_unit_serial': False})
        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])

        with self.assertRaises(UserError) as ctx:
            order.action_pos_order_paid()
        self.assertIn('kontrollenhet', str(ctx.exception).lower(),
                      "Kvittot framställs inte och försäljningen registreras "
                      "inte som genomförd")

    # ------------------------------------------------------------------
    # Requirement: kassabeteckning
    # ------------------------------------------------------------------
    def test_receipt_shows_register_name_with_sequence(self):
        """Scenario: kassabeteckning i anslutning till löpnumret."""
        session = self._open_session()
        receipt = self._pay(self._make_order(session, [(self.goods, 1)]))
        self.assertEqual(receipt.register_name, self.unit.name,
                         "Kassabeteckningen ska anges på kvittot")

    # ------------------------------------------------------------------
    # Requirement: version och modellbeteckning
    # ------------------------------------------------------------------
    def test_model_designation_contains_se(self):
        """Scenario: modellbeteckningen innehåller 'SE'."""
        self.assertIn('SE', self.unit.model_designation.upper(),
                      "Modellbeteckningen ska innehålla 'SE'")

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------
    def test_receipt_cannot_be_modified(self):
        """Ett framställt kvitto kan inte ändras."""
        session = self._open_session()
        receipt = self._pay(self._make_order(session, [(self.goods, 1)]))
        with self.assertRaises(UserError):
            receipt.amount_total = 0.0

    def test_receipt_cannot_be_deleted(self):
        """Ett kvitto kan inte raderas."""
        session = self._open_session()
        receipt = self._pay(self._make_order(session, [(self.goods, 1)]))
        with self.assertRaises(UserError):
            receipt.unlink()

    # ------------------------------------------------------------------
    # QWeb rendering
    # ------------------------------------------------------------------
    def test_receipt_template_renders_markings(self):
        """Markeringstexterna finns i mallen med rätt teckenstorlek."""
        session = self._open_session()
        order = self._make_order(session, [(self.goods, 1)])
        receipt = self._pay(order)

        html = self.env['ir.actions.report']._render_qweb_html(
            'pos_kassaregister_se.report_pos_receipt', receipt.ids)[0].decode()

        self.assertIn(receipt.company_name, html, "Företagsnamnet saknas")
        self.assertIn(receipt.street, html, "Adressen saknas")
        self.assertIn('Kontrollenhet', html, "Kontrollenheten saknas")
        self.assertIn('SE', html, "Modellbeteckningen saknas")

        # A copy is marked "kopia" at twice the amount text size
        copy = self.Receipt._produce(order, kind='copy')
        html_copy = self.env['ir.actions.report']._render_qweb_html(
            'pos_kassaregister_se.report_pos_receipt', copy.ids)[0].decode()
        self.assertIn('kopia', html_copy.lower(), "Kopian ska märkas 'kopia'")
        self.assertIn('font-size: 2em', html_copy,
                      "Markeringen ska vara minst dubbelt så stor")
