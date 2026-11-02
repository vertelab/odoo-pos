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
"""Tests for the journal memory events of 4 kap. (parking, drawer, float).

Covers the operations that produce no order and therefore can only be
captured where they happen.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestJournalminneHandelser(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env['pos.config'].create({'name': 'Kassa minne-test'})
        cls.unit = cls.config.registration_unit_id
        cls.unit.write({'control_unit_serial': 'CU-321'})
        cls.config.write({
            'sales_street': 'Storgatan 1', 'sales_city': 'Stockholm',
        })
        journal = cls.env['account.journal'].create({
            'name': 'Kassa minne', 'code': 'KMIN', 'type': 'cash',
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
            'name': 'Hammare', 'list_price': 200.0, 'type': 'consu',
            'available_in_pos': True, 'taxes_id': [(6, 0, cls.tax.ids)],
        })
        cls.Journal = cls.env['pos.journal.entry']

    def _session(self):
        return self.env['pos.session'].create({'config_id': self.config.id})

    def _order(self, session):
        order = self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'product_id': self.product.id, 'qty': 1,
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
        order.write({
            'amount_total': sum(order.lines.mapped('price_subtotal_incl')),
            'amount_tax': sum(order.lines.mapped('price_subtotal_incl'))
                          - sum(order.lines.mapped('price_subtotal')),
        })
        return order

    def _events(self, session, event_type):
        return self.Journal.search([
            ('session_id', '=', session.id),
            ('event_type', '=', event_type),
        ])

    # ------------------------------------------------------------------
    # 4.6 — parkering
    # ------------------------------------------------------------------
    def test_parking_is_logged(self):
        """Parkering av en artikel loggas (4 kap. 5 §)."""
        session = self._session()
        order = self._order(session)
        order.lines.action_park(reason='Kunden hämtar mer')

        entry = self._events(session, 'ParkeraRegistreradArtikel')
        self.assertEqual(len(entry), 1, "Parkeringen ska loggas")
        self.assertEqual(entry.payload['product_id'], self.product.id)
        self.assertIn('Kunden hämtar mer', entry.payload['reason'])

    def test_resume_parking_is_logged(self):
        """Återupptagen parkering loggas (4 kap. 5 §)."""
        session = self._session()
        order = self._order(session)
        order.lines.action_resume_parking()
        self.assertEqual(
            len(self._events(session, 'OppnaParkering')), 1,
            "Återupptagen parkering ska loggas")

    def test_delete_parked_is_logged(self):
        """Raderad parkerad artikel loggas (4 kap. 5 §)."""
        session = self._session()
        order = self._order(session)
        order.lines.action_delete_parked(reason='Kunden ångrade sig')
        entry = self._events(session, 'RaderaParkeradArtikel')
        self.assertEqual(len(entry), 1)
        self.assertIn('ångrade', entry.payload['reason'])

    def test_change_parked_is_logged(self):
        """Ändrad parkerad artikel loggas med gammalt och nytt antal."""
        session = self._session()
        order = self._order(session)
        order.lines.action_change_parked(new_qty=3)
        entry = self._events(session, 'AndraParkeradArtikel')
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry.payload['old_qty'], 1)
        self.assertEqual(entry.payload['new_qty'], 3)

    # ------------------------------------------------------------------
    # 4.7 — kassalåda utan försäljning
    # ------------------------------------------------------------------
    def test_drawer_opening_without_sale_is_logged(self):
        """Kassalåda öppnad utan försäljning loggas (4 kap. 4 §)."""
        session = self._session()
        session.log_cash_drawer_opening(reason='Växling')

        entry = self._events(session, 'OppnaKassaladaVidNollforsaljning')
        self.assertEqual(len(entry), 1,
                         "Öppningen ska loggas i journalminnet")
        self.assertIn('Växling', entry.payload['reason'])

    def test_drawer_openings_counted_in_z_report(self):
        """Lådöppningarna räknas i Z-dagrapporten (7 kap. 3 §)."""
        session = self._session()
        session.log_cash_drawer_opening()
        session.log_cash_drawer_opening()

        z = self.env['pos.report.z']._generate_z_report(session)
        self.assertEqual(z.drawer_open_count, 2,
                         "Båda öppningarna ska räknas")

    # ------------------------------------------------------------------
    # 4.8 — växelkassa
    # ------------------------------------------------------------------
    def test_cash_float_change_is_logged(self):
        """Ändrad växelkassa loggas med gammalt och nytt belopp."""
        session = self._session()
        session.write({'cash_float_start': 1000.0})
        session.log_cash_float_change(1500.0, reason='Påfyllning')

        entry = self._events(session, 'ForandraVaxelkassa').filtered(
            lambda e: e.payload.get('reason') == 'Påfyllning')
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry.payload['old_float'], 1000.0)
        self.assertEqual(entry.payload['new_float'], 1500.0)
        self.assertEqual(entry.payload['difference'], 500.0)

    def test_opening_float_is_logged(self):
        """Öppningsväxelkassan loggas när sessionen öppnas."""
        session = self.env['pos.session'].create({
            'config_id': self.config.id,
        })
        entries = self._events(session, 'ForandraVaxelkassa')
        self.assertTrue(entries, "Öppningsväxelkassan ska loggas")
        self.assertEqual(entries[0].payload['reason'], 'Öppningsväxelkassa')

    # ------------------------------------------------------------------
    # 4.9 — prisförfrågan och clear
    # ------------------------------------------------------------------
    def test_price_inquiry_is_logged(self):
        """Prisförfrågan loggas (4 kap. 9 §)."""
        session = self._session()
        session.log_price_inquiry(self.product, 200.0)

        entry = self._events(session, 'StallaPrisforfragan')
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry.payload['product_id'], self.product.id)
        self.assertEqual(entry.payload['price'], 200.0)

    def test_clear_is_logged(self):
        """Använd clear-funktionen loggas (4 kap. 9 §)."""
        session = self._session()
        session.log_clear(scope='hela försäljningen')

        entry = self._events(session, 'AnvandaClear')
        self.assertEqual(len(entry), 1)
        self.assertIn('försäljningen', entry.payload['scope'])

    # ------------------------------------------------------------------
    # 4.10 — klockan
    # ------------------------------------------------------------------
    def test_clock_adjustment_is_logged(self):
        """Klockjustering loggas med gammal och ny tid (4 kap. 10 §)."""
        session = self._session()
        old = fields.Datetime.now()
        new = old + timedelta(minutes=5)
        session.log_clock_adjustment(old, new, reason='NTP-korrigering')

        entry = self._events(session, 'StallaOmKlockan')
        self.assertEqual(len(entry), 1, "Klockjusteringen ska loggas")
        self.assertEqual(entry.payload['delta_seconds'], 300.0)
        self.assertEqual(entry.payload['reason'], 'NTP-korrigering')
        self.assertIn(fields.Datetime.to_string(new),
                      entry.payload['new_time'])

    # ------------------------------------------------------------------
    # Kedjan håller för alla nya händelser
    # ------------------------------------------------------------------
    def test_chain_remains_valid_after_new_events(self):
        """Hash-kedjan håller efter de nya händelsetyperna."""
        session = self._session()
        order = self._order(session)
        order.lines.action_park()
        session.log_cash_drawer_opening()
        session.log_cash_float_change(2000.0)
        session.log_price_inquiry(self.product, 200.0)
        session.log_clear()
        session.log_clock_adjustment(
            fields.Datetime.now(), fields.Datetime.now() + timedelta(seconds=30))

        entries = self.Journal.search(
            [('session_id', '=', session.id)], order='sequence asc')
        self.assertTrue(len(entries) >= 6)
        self.assertEqual(entries._check_chain(), [],
                         "Kedjan ska vara obruten efter de nya händelserna")
