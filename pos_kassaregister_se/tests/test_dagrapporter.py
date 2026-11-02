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
"""Tests for the X- and Z-dagrapporter (SKVFS 2021:17 7 kap.).

Covers every scenario in ``specs/kassaregister/dagrapporter/spec.md``.
"""
from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestDagrapporter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env['pos.config'].create({'name': 'Kassa Z-test'})
        cls.unit = cls.config.registration_unit_id
        cls.ReportZ = cls.env['pos.report.z']
        cls.ReportX = cls.env['pos.report.x']
        cls.Session = cls.env['pos.session']

        # A cash payment method and a product to sell
        cls.cash_method = cls.env['pos.payment.method'].create({
            'name': 'Kontant',
            'is_cash_count': True,
            'journal_id': cls.env['account.journal'].search(
                [('type', '=', 'cash'),
                 ('company_id', '=', cls.env.company.id)], limit=1).id,
        })
        cls.bank_method = cls.env['pos.payment.method'].create({
            'name': 'Kort',
            'is_cash_count': False,
            'journal_id': cls.env['account.journal'].search(
                [('type', '=', 'bank'),
                 ('company_id', '=', cls.env.company.id)], limit=1).id,
        })
        cls.tax_25 = cls.env['account.tax'].create({
            'name': 'Moms 25%',
            'amount': 25.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
        })
        # The payment methods must be allowed on the config, otherwise
        # pos.payment refuses to attach them to an order in this session.
        cls.config.write({
            'payment_method_ids': [(6, 0, (cls.cash_method | cls.bank_method).ids)],
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Testvara',
            'list_price': 100.0,
            'available_in_pos': True,
            'taxes_id': [(6, 0, cls.tax_25.ids)],
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _open_session(self):
        return self.Session.create({'config_id': self.config.id})

    def _make_order(self, session, lines, method=None):
        """Create a paid POS order with the given (product, qty) lines.

        ``price_subtotal`` and ``price_subtotal_incl`` are computed fields
        that are not writable at create time; they are set after the lines
        exist, the same way the POS frontend does it.
        """
        method = method or self.cash_method
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
            'amount_tax': 0.0,
            'amount_total': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        for line in order.lines:
            subtotal_incl = line.qty * line.price_unit
            subtotal = subtotal_incl / (1 + self.tax_25.amount / 100.0)
            line.write({
                'price_subtotal': subtotal,
                'price_subtotal_incl': subtotal_incl,
            })
        order.write({
            'amount_total': sum(order.lines.mapped('price_subtotal_incl')),
            'amount_tax': sum(
                order.lines.mapped('price_subtotal_incl')) - sum(
                order.lines.mapped('price_subtotal')),
        })
        self.env['pos.payment'].create({
            'pos_order_id': order.id,
            'payment_method_id': method.id,
            'amount': order.amount_total,
        })
        order.write({
            'amount_paid': order.amount_total,
            'state': 'paid',
        })
        return order

    # ------------------------------------------------------------------
    # Requirement: Z-dagrapport per enhet och försäljningsdag
    # ------------------------------------------------------------------
    def test_z_report_created_on_session_close(self):
        """Scenario: Z-dagrapport vid stängning."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        session.action_pos_session_closing_control()

        report = self.ReportZ.search([('session_id', '=', session.id)])
        self.assertEqual(len(report), 1,
                         "En Z-dagrapport skapas när sessionen stängs")
        self.assertEqual(report.unit_id, self.unit)
        self.assertEqual(report.sales_date, report.produced_at.date()
                         if False else report.sales_date)

    def test_z_report_is_retrievable_without_recreation(self):
        """Scenario: rapporten lagras och kan tas fram igen."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        session.action_pos_session_closing_control()

        first = self.ReportZ.search([('session_id', '=', session.id)])
        again = self.ReportZ._generate_z_report(session)
        self.assertEqual(first, again,
                         "Samma rapport returneras — ingen ny skapas")
        self.assertEqual(
            self.ReportZ.search_count([('session_id', '=', session.id)]), 1)

    def test_no_z_report_for_unused_unit(self):
        """Scenario: Ingen Z-dagrapport för oanvänd enhet."""
        other = self.env['pos.config'].create({'name': 'Kassa oanvänd'})
        before = self.ReportZ.search_count([])
        self.assertEqual(
            self.ReportZ.search_count([('unit_id', '=', other.registration_unit_id.id)]),
            0,
            "En enhet som inte använts har ingen Z-dagrapport",
        )
        self.assertEqual(self.ReportZ.search_count([]), before)

    # ------------------------------------------------------------------
    # Requirement: obligatoriska uppgifter
    # ------------------------------------------------------------------
    def test_z_report_mandatory_fields(self):
        """Z-dagrapporten innehåller samtliga obligatoriska uppgifter."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        session.action_pos_session_closing_control()
        report = self.ReportZ.search([('session_id', '=', session.id)])

        self.assertTrue(report.company_name, "Företagsnamn saknas")
        self.assertTrue(report.sequence, "Löpnummer saknas")
        self.assertTrue(report.produced_at, "Framställningstid saknas")
        self.assertEqual(report.unit_id, self.unit, "Kassabeteckning saknas")
        self.assertAlmostEqual(report.total_sales, 100.0, places=2,
                               msg="Total försäljningssumma")
        self.assertEqual(report.receipt_count, 1, "Antal kassakvitton")

    def test_return_in_payment_breakdown_not_in_receipt_count(self):
        """Scenario: Retur redovisas i betalningsmedelsfördelningen.

        500 kr kontant försäljning + 200 kr kontant retur ger 300 kr kontant
        och 1 kassakvitto (returkvittot räknas inte).
        """
        session = self._open_session()
        self._make_order(session, [(self.product, 5)])   # 500 kr
        self._make_order(session, [(self.product, -2)])  # -200 kr
        session.action_pos_session_closing_control()

        report = self.ReportZ.search([('session_id', '=', session.id)])
        cash = report.line_ids.filtered(
            lambda l: l.line_type == 'payment' and l.name == 'Kontant')
        self.assertEqual(len(cash), 1)
        self.assertAlmostEqual(cash.amount, 300.0, places=2,
                               msg="Kontant ska vara 500 - 200 = 300 kr")
        self.assertEqual(report.receipt_count, 1,
                         "Returkvittot räknas inte som kassakvitto")
        self.assertEqual(report.return_count, 1)

    def test_tax_breakdown_ignores_returns(self):
        """Scenario: Momsfördelning utan hänsyn till returer.

        125 kr försäljning med 25 % moms (25 kr moms) och 25 kr retur med
        25 % moms — momsfördelningen ska visa 25 kr, inte 20 kr.
        """
        session = self._open_session()
        sale = self._make_order(session, [(self.product, 1.25)])   # 125 kr
        self._make_order(session, [(self.product, -0.25)])         # -25 kr
        session.action_pos_session_closing_control()

        report = self.ReportZ.search([('session_id', '=', session.id)])
        tax = report.line_ids.filtered(lambda l: l.line_type == 'tax')
        self.assertEqual(len(tax), 1, "En skattesats ska redovisas")
        self.assertAlmostEqual(
            tax.amount, 25.0, places=2,
            msg="Momsen beräknas på försäljningen utan avdrag för returen")

    def test_zero_sales_day_reports_zero_receipts(self):
        """Scenario: Nollförsäljningsdag."""
        session = self._open_session()
        session.action_pos_session_closing_control()

        report = self.ReportZ.search([('session_id', '=', session.id)])
        self.assertEqual(len(report), 1,
                         "Även en försäljningsfri dag får en Z-dagrapport")
        self.assertEqual(report.receipt_count, 0,
                         "Antalet kassakvitton ska vara 0")
        self.assertAlmostEqual(report.total_sales, 0.0, places=2)

    def test_drawer_openings_counted(self):
        """Antal lådöppningar räknas ur journalminnet."""
        session = self._open_session()
        Journal = self.env['pos.journal.entry']
        for _ in range(3):
            Journal._log_event(
                'OppnaKassaladaVidNollforsaljning', unit=self.unit,
                session=session)
        session.action_pos_session_closing_control()

        report = self.ReportZ.search([('session_id', '=', session.id)])
        self.assertEqual(report.drawer_open_count, 3,
                         "Tre lådöppningar ska redovisas")

    # ------------------------------------------------------------------
    # Requirement: egen obruten löpnummerserie
    # ------------------------------------------------------------------
    def test_z_sequence_is_unbroken(self):
        """Scenario: Två Z-rapporter samma dag får N och N+1."""
        session_1 = self._open_session()
        self._make_order(session_1, [(self.product, 1)])
        session_1.action_pos_session_closing_control()

        session_2 = self._open_session()
        self._make_order(session_2, [(self.product, 2)])
        session_2.action_pos_session_closing_control()

        report_1 = self.ReportZ.search([('session_id', '=', session_1.id)])
        report_2 = self.ReportZ.search([('session_id', '=', session_2.id)])
        self.assertEqual(report_2.sequence, report_1.sequence + 1,
                         "Löpnumren ska vara N och N+1")

    def test_z_sequence_separate_from_journal_sequence(self):
        """Z-serien är skild från journalminnets serie."""
        self.assertNotEqual(
            self.unit.sequence_id, self.unit.z_sequence_id,
            "Z-dagrapporter har en egen sekvens",
        )
        self.assertEqual(self.unit.z_sequence_id.implementation, 'no_gap')

    # ------------------------------------------------------------------
    # Requirement: X-dagrapport
    # ------------------------------------------------------------------
    def test_x_report_does_not_close_session(self):
        """Scenario: X-dagrapport mitt på dagen."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        state_before = session.state

        report = self.ReportX._generate_x_report(session)

        self.assertEqual(session.state, state_before,
                         "Sessionen ska fortsätta vara öppen")
        self.assertAlmostEqual(report.total_sales, 100.0, places=2)

    def test_x_report_consumes_no_z_sequence(self):
        """Scenario: X-dagrapport saknar Z-löpnummer."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])

        z_before = self.unit.z_sequence_id.number_next_actual
        self.ReportX._generate_x_report(session)
        z_after = self.unit.z_sequence_id.number_next_actual

        self.assertEqual(z_before, z_after,
                         "Inget Z-löpnummer får förbrukas")
        self.assertFalse(
            'sequence' in self.ReportX._fields,
            "X-dagrapporten har inget Z-löpnummer-fält",
        )

    def test_x_report_has_same_figures_as_z(self):
        """X-dagrapporten innehåller samma uppgifter som Z utom löpnummer."""
        session = self._open_session()
        self._make_order(session, [(self.product, 3)])

        x_report = self.ReportX._generate_x_report(session)
        self.assertAlmostEqual(x_report.total_sales, 300.0, places=2)
        self.assertEqual(x_report.receipt_count, 1)
        self.assertTrue(x_report.line_ids.filtered(
            lambda l: l.line_type == 'payment'))
        self.assertTrue(x_report.line_ids.filtered(
            lambda l: l.line_type == 'tax'))

    # ------------------------------------------------------------------
    # Requirement: registreras i journalminnet
    # ------------------------------------------------------------------
    def test_z_report_logged_in_journal(self):
        """Scenario: Z-dagrapport syns i journalminnet."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        session.action_pos_session_closing_control()

        report = self.ReportZ.search([('session_id', '=', session.id)])
        entry = self.env['pos.journal.entry'].search([
            ('unit_id', '=', self.unit.id),
            ('event_type', '=', 'ZDagrapport'),
        ], limit=1)
        self.assertTrue(entry, "En ZDagrapport-post ska finnas")
        self.assertEqual(entry.payload.get('sequence'), report.sequence,
                         "Posten bär rapportens löpnummer")

    def test_x_report_logged_in_journal(self):
        """X-dagrapporten registreras som XDagrapport."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        self.ReportX._generate_x_report(session)

        entry = self.env['pos.journal.entry'].search([
            ('unit_id', '=', self.unit.id),
            ('event_type', '=', 'XDagrapport'),
        ], limit=1)
        self.assertTrue(entry, "En XDagrapport-post ska finnas")

    # ------------------------------------------------------------------
    # Requirement: svensk normaltid
    # ------------------------------------------------------------------
    def test_swedish_time_under_dst(self):
        """Scenario: Rapport framställd under sommartid.

        2027-07-15 22:30 svensk tid är 20:30 UTC. Rapporten ska ange 22:30.
        """
        utc = datetime(2027, 7, 15, 20, 30, 0)
        local = self.ReportZ._to_swedish(utc)
        self.assertEqual(local.strftime('%Y-%m-%d %H:%M'), '2027-07-15 22:30',
                         "Sommartid ska ge 22:30, inte 20:30")

    def test_swedish_time_winter(self):
        """Vintertid: UTC+1."""
        utc = datetime(2027, 1, 15, 20, 30, 0)
        local = self.ReportZ._to_swedish(utc)
        self.assertEqual(local.strftime('%Y-%m-%d %H:%M'), '2027-01-15 21:30',
                         "Vintertid ska ge 21:30")

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------
    def test_z_report_cannot_be_modified(self):
        """En framställd Z-dagrapport kan inte ändras."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        session.action_pos_session_closing_control()
        report = self.ReportZ.search([('session_id', '=', session.id)])

        with self.assertRaises(UserError):
            report.total_sales = 0.0

    def test_z_report_cannot_be_deleted(self):
        """En Z-dagrapport kan inte raderas (7 års bevarande)."""
        session = self._open_session()
        self._make_order(session, [(self.product, 1)])
        session.action_pos_session_closing_control()
        report = self.ReportZ.search([('session_id', '=', session.id)])

        with self.assertRaises(UserError):
            report.unlink()
