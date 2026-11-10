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
"""Tests for the prohibitions on forbidden functions (SKVFS 2021:17 6 kap.).

Covers every scenario in
``specs/kassaregister/otillatna-funktioner/spec.md``.
"""
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestOtillatnaFunktioner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({'vat': '556012345601'})
        cls.config = cls.env['pos.config'].create({'name': 'Kassa spärr-test'})
        cls.unit = cls.config.registration_unit_id
        cls.unit.write({'control_unit_serial': 'CU-55500000000001'})
        cls.config.write({
            'sales_street': 'Storgatan 1',
            'sales_city': 'Stockholm',
        })
        journal = cls.env['account.journal'].create({
            'name': 'Kassa spärr', 'code': 'KSPR', 'type': 'cash',
            'company_id': cls.env.company.id,
        })
        cls.cash = cls.env['pos.payment.method'].create({
            'name': 'Kontant', 'is_cash_count': True, 'journal_id': journal.id,
        })
        cls.config.write({'payment_method_ids': [(6, 0, cls.cash.ids)]})
        cls.tax = cls.env['account.tax'].create({
            'name': 'Moms 25%', 'amount': 25.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'price_include_override': 'tax_included',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Skruvdragare', 'list_price': 1000.0, 'type': 'consu',
            'available_in_pos': True, 'taxes_id': [(6, 0, cls.tax.ids)],
        })

    def _session(self, is_training=False):
        return self.env['pos.session'].create({
            'config_id': self.config.id, 'is_training': is_training,
        })

    def _training_config(self):
        """A second register, used for training mode.

        A POS config can only have one open session at a time, so training
        mode needs its own register.
        """
        journal = self.env['account.journal'].create({
            'name': 'Kassa övning', 'code': 'KOVN', 'type': 'cash',
            'company_id': self.env.company.id,
        })
        method = self.env['pos.payment.method'].create({
            'name': 'Kontant övning', 'is_cash_count': True,
            'journal_id': journal.id,
        })
        config = self.env['pos.config'].create({
            'name': 'Kassa övning',
            'payment_method_ids': [(6, 0, method.ids)],
            'sales_street': 'Storgatan 1',
            'sales_city': 'Stockholm',
        })
        config.registration_unit_id.write({'control_unit_serial': 'CU-77700000000002'})
        return config, method

    def _order(self, session, qty=1):
        order = self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'product_id': self.product.id,
                'qty': qty,
                'price_unit': self.product.list_price,
                'tax_ids': [(6, 0, self.product.taxes_id.ids)],
                'price_subtotal': 0.0,
                'price_subtotal_incl': 0.0,
            })],
            'amount_tax': 0.0, 'amount_total': 0.0,
            'amount_paid': 0.0, 'amount_return': 0.0,
        })
        for line in order.lines:
            incl = line.qty * line.price_unit
            line.write({
                'price_subtotal': incl / 1.25,
                'price_subtotal_incl': incl,
            })
            # Odoo does not set full_product_name on create; the register
            # stamps the article's programmed text.
            line.write({'full_product_name': line._programmed_name()})
        order.write({
            'amount_total': sum(order.lines.mapped('price_subtotal_incl')),
            'amount_tax': sum(order.lines.mapped('price_subtotal_incl'))
                          - sum(order.lines.mapped('price_subtotal')),
        })
        # Use the payment method configured on this session's register.
        # Training mode runs on its own config with its own method, so
        # self.cash is not necessarily allowed there.
        method = session.config_id.payment_method_ids[:1] or self.cash
        self.env['pos.payment'].create({
            'pos_order_id': order.id,
            'payment_method_id': method.id,
            'amount': order.amount_total,
        })
        order.write({'amount_paid': order.amount_total})
        return order

    def _paid_order(self, session, qty=1):
        order = self._order(session, qty)
        order.action_pos_order_paid()
        return order

    # ------------------------------------------------------------------
    # 7.1 — neka ändring av registrerad försäljning
    # ------------------------------------------------------------------
    def test_paid_order_cannot_be_modified(self):
        """En betald order får inte ändras (6 kap. 1 §)."""
        order = self._paid_order(self._session())
        with self.assertRaises(UserError) as ctx:
            order.write({'amount_total': 1.0})
        self.assertIn('cannot be modified', str(ctx.exception).lower())

    def test_done_order_cannot_be_modified(self):
        """En avslutad order får inte heller ändras (6 kap. 1 §)."""
        order = self._paid_order(self._session())
        order.write({'state': 'done'})
        with self.assertRaises(UserError):
            order.write({'amount_total': 1.0})

    def test_order_line_name_locked_after_payment(self):
        """En betald orders artikelbenämning får inte ändras (6 kap. 1 §)."""
        order = self._paid_order(self._session())
        with self.assertRaises(UserError):
            order.lines.write({'full_product_name': 'Något annat'})

    # ------------------------------------------------------------------
    # 7.2 — neka radering
    # ------------------------------------------------------------------
    def test_paid_order_cannot_be_deleted(self):
        """En betald order kan inte raderas (6 kap. 1 §)."""
        order = self._paid_order(self._session())
        with self.assertRaises(UserError) as ctx:
            order.unlink()
        self.assertIn('raderas', str(ctx.exception).lower())

    def test_draft_order_cannot_be_deleted_when_register_active(self):
        """Inte heller ett utkast får raderas — serien måste vara obruten."""
        session = self._session()
        order = self._order(session)
        with self.assertRaises(UserError):
            order.unlink()

    # ------------------------------------------------------------------
    # 7.3 — betalning och kvittoframställning är atomär
    # ------------------------------------------------------------------
    def test_no_paid_order_when_receipt_production_fails(self):
        """Kvittot framställs först — misslyckas det blir ordern inte betald."""
        session = self._session()
        order = self._order(session)
        # Remove the control unit: receipt production must fail.
        self.unit.write({'control_unit_serial': False})

        with self.assertRaises(UserError):
            order.action_pos_order_paid()

        order.invalidate_recordset()
        self.assertNotEqual(order.state, 'paid',
                            "Ordern får inte lämnas som betald när kvittot "
                            "inte kunde framställas (6 kap. 2 §)")
        self.assertFalse(
            self.env['pos.receipt'].search([('order_id', '=', order.id)]),
            "Inget kvitto ska ha skapats",
        )

    # ------------------------------------------------------------------
    # 7.4 — högst två utskrifter, den andra märkt "kopia"
    # ------------------------------------------------------------------
    def test_third_print_is_refused(self):
        """Tredje utskriften nekas (6 kap. 3 §)."""
        order = self._paid_order(self._session())
        Receipt = self.env['pos.receipt']

        first = Receipt.search([('order_id', '=', order.id)], limit=1)
        self.assertEqual(first.kind, 'sale', "Första utskriften är originalet")

        copy = Receipt._produce(order, kind='copy')
        self.assertEqual(copy.kind, 'copy', "Andra utskriften märks som kopia")
        self.assertEqual(copy.sequence, first.sequence,
                         "Kopian bär originalets löpnummer")

        with self.assertRaises(UserError):
            Receipt._produce(order, kind='copy')

    def test_action_print_receipt_refuses_third_print(self):
        """Utskriftsknappen nekar tredje utskriften (6 kap. 3 §)."""
        order = self._paid_order(self._session())
        order.action_print_receipt()  # first copy
        with self.assertRaises(UserError):
            order.action_print_receipt()

    # ------------------------------------------------------------------
    # 7.5 — artikelns förprogrammerade text
    # ------------------------------------------------------------------
    def test_article_name_cannot_be_replaced_with_free_text(self):
        """Artiklamnets text får inte bytas mot fritext (6 kap. 4 §)."""
        session = self._session()
        order = self._order(session)
        with self.assertRaises(UserError) as ctx:
            order.lines.write({'full_product_name': 'Eget påhittat namn'})
        self.assertIn('förprogrammerade', str(ctx.exception).lower())

    def test_article_name_equals_product_name(self):
        """Den registrerade benämningen är artikelns egen text."""
        session = self._session()
        order = self._order(session)
        self.assertEqual(order.lines.full_product_name,
                         self.product.display_name,
                         "Benämningen ska vara artikelns förprogrammerade text")

    # ------------------------------------------------------------------
    # 7.6 — markeringstexterna och deras storlek
    # ------------------------------------------------------------------
    def test_marking_texts_are_twice_the_amount_size(self):
        """Markeringstexterna är minst dubbelt så stora som beloppstexten."""
        order = self._paid_order(self._session())
        Receipt = self.env['pos.receipt']
        report = self.env['ir.actions.report']

        for kind, expected in [('copy', 'kopia'),
                               ('training', 'övning (ovning)'),
                               ('proforma', 'ej kvitto')]:
            receipt = Receipt._produce(order, kind=kind)
            html = report._render_qweb_html(
                'pos_kassaregister_se.report_pos_receipt',
                receipt.ids)[0].decode()
            self.assertIn(expected, html.lower(),
                          "Markeringstexten '%s' saknas" % expected)
            self.assertIn('font-size: 2em', html,
                          "Markeringen ska vara minst dubbelt så stor "
                          "som beloppstexten (5 kap. 5 §)")

    # ------------------------------------------------------------------
    # 7.7 — övningsläge hålls åtskilt
    # ------------------------------------------------------------------
    def test_training_mode_does_not_affect_z_report(self):
        """Övningsläge påverkar inte Z-dagrapportens totala försäljning."""
        session = self._session()
        self._paid_order(session, qty=1)          # real sale: 1000
        z = self.env['pos.report.z']._generate_z_report(session)
        self.assertAlmostEqual(z.total_sales, 1000.0, places=2)

        training_config, training_method = self._training_config()
        training_session = self.env['pos.session'].create({
            'config_id': training_config.id, 'is_training': True,
        })
        order = self._order(training_session, qty=5)   # 5000 in training
        order.action_pos_order_paid()

        receipt = self.env['pos.receipt'].search(
            [('order_id', '=', order.id)], limit=1)
        self.assertEqual(receipt.kind, 'training',
                         "Övningsläget ska ge övningskvitton")
        self.assertTrue(receipt.is_training)

        z = self.env['pos.report.z']._generate_z_report(session)
        self.assertAlmostEqual(
            z.total_sales, 1000.0, places=2,
            msg="Övningsförsäljning får inte ingå i Z-dagrapporten "
                "(4 kap. 11 §)")

    def test_training_mode_is_logged_in_journal_memory(self):
        """Övningsläget loggas i journalminnet (4 kap. 11 §)."""
        training_config, _method = self._training_config()
        session = self.env['pos.session'].create({
            'config_id': training_config.id, 'is_training': True,
        })
        entries = self.env['pos.journal.entry'].search([
            ('session_id', '=', session.id),
            ('event_type', '=', 'StallaOmTillOvningslage'),
        ])
        self.assertTrue(entries, "Övningsläget ska loggas i journalminnet")

    def test_training_receipt_consumes_no_number(self):
        """Övningskvittot förbrukar inget löpnummer (7 kap. 1 §)."""
        training_config, _method = self._training_config()
        session = self.env['pos.session'].create({
            'config_id': training_config.id, 'is_training': True,
        })
        order = self._order(session)
        order.action_pos_order_paid()
        receipt = self.env['pos.receipt'].search(
            [('order_id', '=', order.id)], limit=1)
        self.assertEqual(receipt.sequence, 0,
                         "Övningskvitton förbrukar inget löpnummer")
