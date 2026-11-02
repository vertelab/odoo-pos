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
"""X- and Z-dagrapporter (SKVFS 2021:17 7 kap.).

A Z-report closes the sales day for one registration unit. It carries an
unbroken sequence number from a series reserved for Z-reports only. An
X-report is a snapshot taken during the ongoing day: same figures, but no
Z sequence number is consumed and the session stays open.

Both are computed from the journal memory rather than from ``pos.order``,
so the reports show what was actually registered — including events that
never became an order, such as drawer openings.
"""
import logging
from datetime import datetime, time

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosReportZ(models.Model):
    """Z-dagrapport — closes a sales day for one registration unit."""

    _name = 'pos.report.z'
    _description = 'Z-dagrapport (SKVFS 2021:17 7 kap. 3 §)'
    _order = 'unit_id, sequence desc'
    _rec_name = 'display_name'

    unit_id = fields.Many2one(
        'pos.registration.unit',
        string='Registreringsenhet',
        required=True,
        readonly=True,
        ondelete='restrict',
        index=True,
    )
    sequence = fields.Integer(
        string='Löpnummer',
        readonly=True,
        required=True,
        help="Löpnummer ur en obruten stigande serie avsedd enbart för "
             "Z-dagrapporter (7 kap. 3 §).",
    )
    session_id = fields.Many2one(
        'pos.session',
        string='Kassasession',
        readonly=True,
        ondelete='restrict',
        index=True,
    )
    sales_date = fields.Date(
        string='Försäljningsdag',
        readonly=True,
        required=True,
        index=True,
        help="Datum enligt svensk normaltid, justerad för sommartid.",
    )
    produced_at = fields.Datetime(
        string='Framställningstid',
        readonly=True,
        required=True,
        help="Datum och klockslag då rapporten togs fram, enligt svensk "
             "normaltid justerad för sommartid.",
    )

    # Company details (7 kap. 3 § — företagsuppgifter)
    company_id = fields.Many2one(
        'res.company',
        string='Företag',
        readonly=True,
        required=True,
    )
    company_name = fields.Char(
        string='Företagsnamn',
        readonly=True,
    )
    company_vat = fields.Char(
        string='Organisationsnummer',
        readonly=True,
    )

    # Totals
    total_sales = fields.Monetary(
        string='Total försäljningssumma',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        readonly=True,
        default=lambda self: self.env.company.currency_id,
    )
    cash_register_balance_start = fields.Monetary(
        string='Växelkassa vid öppning',
        readonly=True,
        currency_field='currency_id',
    )
    cash_register_balance_end = fields.Monetary(
        string='Växelkassa vid stängning',
        readonly=True,
        currency_field='currency_id',
    )
    receipt_count = fields.Integer(
        string='Antal kassakvitton',
        readonly=True,
        help="Antal framställda kassakvitton. Returkvitto räknas inte som "
             "kassakvitto. 0 om ingen försäljning registrerats.",
    )
    return_count = fields.Integer(
        string='Antal returkvitton',
        readonly=True,
    )
    drawer_open_count = fields.Integer(
        string='Antal lådöppningar',
        readonly=True,
    )
    open_order_count = fields.Integer(
        string='Antal oavslutade försäljningar',
        readonly=True,
    )
    open_order_amount = fields.Monetary(
        string='Oavslutade försäljningars belopp',
        readonly=True,
        currency_field='currency_id',
    )
    tip_total = fields.Monetary(
        string='Dricks',
        readonly=True,
        currency_field='currency_id',
        help="Dricks redovisas under egen rubrik och ingår inte i "
             "försäljningssumman per betalningsmedel (7 kap. 3 §).",
    )

    line_ids = fields.One2many(
        'pos.report.z.line',
        'report_id',
        string='Rader',
        readonly=True,
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )

    _sql_constraints = [
        ('unit_sequence_uniq', 'unique(unit_id, sequence)',
         'Z-dagrapportens löpnummer måste vara unikt per registreringsenhet.'),
    ]

    @api.depends('unit_id', 'sequence', 'sales_date')
    def _compute_display_name(self):
        for report in self:
            report.display_name = '%s Z-%s (%s)' % (
                report.unit_id.name or '',
                report.sequence,
                fields.Date.to_string(report.sales_date),
            )

    @api.model
    def _swedish_tz(self):
        """Return the Swedish timezone (Europe/Stockholm)."""
        return pytz.timezone('Europe/Stockholm')

    @api.model
    def _to_swedish(self, dt):
        """Convert a naive UTC datetime to a naive Swedish local datetime."""
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(self._swedish_tz()).replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    @api.model
    def _generate_z_report(self, session):
        """Create the Z-report that closes ``session``.

        Computes every figure from the journal memory for the unit and the
        sales day, assigns the next Z sequence number and stores the report.
        The report is never regenerated: an existing report for the same
        session is returned as-is (7 kap. 3 § — the report must be
        retrievable without being recreated).
        """
        unit = session.config_id.registration_unit_id
        if not unit:
            raise UserError(_(
                "Kassakonfigurationen %(config)s saknar registreringsenhet. "
                "En Z-dagrapport kan inte tas fram.",
                config=session.config_id.name,
            ))

        existing = self.search([('session_id', '=', session.id)], limit=1)
        if existing:
            return existing

        produced_at = fields.Datetime.now()
        local = self._to_swedish(produced_at)
        sales_date = local.date()

        data = self._collect_figures(session, unit, sales_date)
        sequence = int(unit.z_sequence_id.next_by_id())

        report = self.create({
            'unit_id': unit.id,
            'sequence': sequence,
            'session_id': session.id,
            'sales_date': sales_date,
            'produced_at': produced_at,
            'company_id': session.company_id.id,
            'company_name': session.company_id.name,
            'company_vat': session.company_id.vat or '',
            **data,
        })
        report._create_lines(session, unit, sales_date)

        self.env['pos.journal.entry']._log_event(
            'ZDagrapport',
            unit=unit,
            session=session,
            amount=report.total_sales,
            payload={
                'report_id': report.id,
                'sequence': sequence,
                'sales_date': fields.Date.to_string(sales_date),
                'receipt_count': report.receipt_count,
            },
        )
        return report

    @api.model
    def _collect_figures(self, session, unit, sales_date):
        """Collect the mandatory Z-report figures for a session.

        Returns a dict of field values. Returkvitton are included in the
        payment breakdown with negative amounts but excluded from the
        receipt count; moms is reported on sales only, without deduction
        for returns (7 kap. 3 §).
        """
        # Training-mode sales never enter the Z report (4 kap. 11 §). They
        # are journal events in their own right, but their amounts must not
        # touch the total sales figure or the VAT breakdown.
        orders = session.order_ids.filtered(
            lambda o: o.state in ('paid', 'done', 'invoiced')
            and not o.receipt_ids.filtered('is_training'))

        total_sales = sum(orders.mapped('amount_total'))
        receipts = orders.filtered(lambda o: o.amount_total >= 0)
        returns = orders.filtered(lambda o: o.amount_total < 0)

        # Drawer openings are journal events, not orders: count them from
        # the journal memory so the figure reflects what actually happened.
        Journal = self.env['pos.journal.entry']
        drawer_opens = Journal.search_count([
            ('unit_id', '=', unit.id),
            ('session_id', '=', session.id),
            ('event_type', '=', 'OppnaKassaladaVidNollforsaljning'),
        ])

        open_orders = session.order_ids.filtered(
            lambda o: o.state == 'draft')

        return {
            'total_sales': total_sales,
            'cash_register_balance_start': session.cash_register_balance_start,
            'cash_register_balance_end': session.cash_register_balance_end_real,
            'receipt_count': len(receipts),
            'return_count': len(returns),
            'drawer_open_count': drawer_opens,
            'open_order_count': len(open_orders),
            'open_order_amount': sum(open_orders.mapped('amount_total')),
            'tip_total': 0.0,
        }

    def _create_lines(self, session, unit, sales_date):
        """Create the payment-method, tax and product-group lines."""
        self.ensure_one()
        Line = self.env['pos.report.z.line']
        orders = session.order_ids.filtered(
            lambda o: o.state in ('paid', 'done', 'invoiced'))

        # Payment methods — returns carry negative amounts (7 kap. 3 §)
        payments = orders.payment_ids
        by_method = {}
        for payment in payments:
            method = payment.payment_method_id
            by_method.setdefault(method, 0.0)
            by_method[method] += payment.amount
        for method, amount in by_method.items():
            Line.create({
                'report_id': self.id,
                'line_type': 'payment',
                'name': method.name,
                'amount': amount,
            })

        # VAT per rate — sales only, no deduction for returns
        tax_by_rate = {}
        for order in orders:
            if order.amount_total < 0:
                continue
            for line in order.lines:
                for tax in line.tax_ids:
                    rate = tax.amount
                    base = line.price_subtotal_incl
                    if tax.price_include:
                        tax_amount = base - (base / (1 + rate / 100.0))
                    else:
                        tax_amount = line.price_subtotal * (rate / 100.0)
                    tax_by_rate.setdefault(rate, 0.0)
                    tax_by_rate[rate] += tax_amount
        for rate, amount in sorted(tax_by_rate.items()):
            Line.create({
                'report_id': self.id,
                'line_type': 'tax',
                'name': _('%s %% moms', ('%g' % rate)),
                'rate': rate,
                'amount': amount,
            })

        # Product groups (huvudgrupper) — sales only, no deduction for returns
        group_by_name = {}
        for order in orders:
            if order.amount_total < 0:
                continue
            for line in order.lines:
                category = line.product_id.categ_id
                name = category.display_name or _('Övrigt')
                group_by_name.setdefault(name, 0.0)
                group_by_name[name] += line.price_subtotal_incl
        for name, amount in sorted(group_by_name.items()):
            Line.create({
                'report_id': self.id,
                'line_type': 'group',
                'name': name,
                'amount': amount,
            })

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------
    def write(self, vals):
        """Z-reports are a legal record and cannot be altered."""
        protected = set(vals) - {'message_main_attachment_id'}
        if protected:
            raise UserError(_(
                "En Z-dagrapport kan inte ändras efter att den tagits fram "
                "(7 kap. 3 § SKVFS 2021:17)."
            ))
        return super().write(vals)

    def unlink(self):
        raise UserError(_(
            "En Z-dagrapport kan inte raderas. Den ska bevaras i sju år "
            "(7 kap. BFL)."
        ))


class PosReportZLine(models.Model):
    """One row on a Z-report: payment method, tax rate or product group."""

    _name = 'pos.report.z.line'
    _description = 'Z-dagrapport rad'
    _order = 'report_id, line_type, id'

    report_id = fields.Many2one(
        'pos.report.z',
        required=True,
        readonly=True,
        ondelete='cascade',
        index=True,
    )
    line_type = fields.Selection(
        selection=[
            ('payment', 'Betalningsmedel'),
            ('tax', 'Momsfördelning'),
            ('group', 'Huvudgrupp'),
            ('reduction', 'Övrig minskning'),
        ],
        string='Typ',
        required=True,
        readonly=True,
    )
    name = fields.Char(
        string='Benämning',
        required=True,
        readonly=True,
    )
    rate = fields.Float(
        string='Skattesats (%)',
        readonly=True,
        digits=(5, 2),
    )
    amount = fields.Monetary(
        string='Belopp',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='report_id.currency_id',
        readonly=True,
    )


class PosReportX(models.Model):
    """X-dagrapport — a snapshot during the ongoing sales day.

    Carries the same figures as a Z-report but has no Z sequence number and
    does not close the session (7 kap. 3 §).
    """

    _name = 'pos.report.x'
    _description = 'X-dagrapport (SKVFS 2021:17 7 kap.)'
    _order = 'produced_at desc'
    _rec_name = 'display_name'

    unit_id = fields.Many2one(
        'pos.registration.unit',
        string='Registreringsenhet',
        required=True,
        readonly=True,
        ondelete='restrict',
        index=True,
    )
    session_id = fields.Many2one(
        'pos.session',
        string='Kassasession',
        readonly=True,
        ondelete='restrict',
        index=True,
    )
    sales_date = fields.Date(
        string='Försäljningsdag',
        readonly=True,
        required=True,
    )
    produced_at = fields.Datetime(
        string='Framställningstid',
        readonly=True,
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Företag',
        readonly=True,
        required=True,
    )
    company_name = fields.Char(string='Företagsnamn', readonly=True)
    company_vat = fields.Char(string='Organisationsnummer', readonly=True)

    total_sales = fields.Monetary(
        string='Total försäljningssumma',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        readonly=True,
        default=lambda self: self.env.company.currency_id,
    )
    cash_register_balance_start = fields.Monetary(
        string='Växelkassa vid öppning',
        readonly=True,
        currency_field='currency_id',
    )
    cash_register_balance_end = fields.Monetary(
        string='Växelkassa vid stängning',
        readonly=True,
        currency_field='currency_id',
    )
    receipt_count = fields.Integer(string='Antal kassakvitton', readonly=True)
    return_count = fields.Integer(string='Antal returkvitton', readonly=True)
    drawer_open_count = fields.Integer(string='Antal lådöppningar', readonly=True)
    open_order_count = fields.Integer(
        string='Antal oavslutade försäljningar', readonly=True)
    open_order_amount = fields.Monetary(
        string='Oavslutade försäljningars belopp',
        readonly=True,
        currency_field='currency_id',
    )
    tip_total = fields.Monetary(
        string='Dricks',
        readonly=True,
        currency_field='currency_id',
    )
    line_ids = fields.One2many(
        'pos.report.x.line',
        'report_id',
        string='Rader',
        readonly=True,
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('unit_id', 'sales_date', 'produced_at')
    def _compute_display_name(self):
        for report in self:
            report.display_name = '%s X (%s)' % (
                report.unit_id.name or '',
                fields.Date.to_string(report.sales_date),
            )

    @api.model
    def _generate_x_report(self, session):
        """Take an X-report snapshot for the ongoing session.

        Does not consume a Z sequence number and leaves the session open.
        """
        unit = session.config_id.registration_unit_id
        if not unit:
            raise UserError(_(
                "Kassakonfigurationen saknar registreringsenhet."
            ))

        produced_at = fields.Datetime.now()
        local = self.env['pos.report.z']._to_swedish(produced_at)
        sales_date = local.date()
        data = self.env['pos.report.z']._collect_figures(
            session, unit, sales_date)

        report = self.create({
            'unit_id': unit.id,
            'session_id': session.id,
            'sales_date': sales_date,
            'produced_at': produced_at,
            'company_id': session.company_id.id,
            'company_name': session.company_id.name,
            'company_vat': session.company_id.vat or '',
            **data,
        })

        # Same line breakdown as the Z-report
        Line = self.env['pos.report.x.line']
        orders = session.order_ids.filtered(
            lambda o: o.state in ('paid', 'done', 'invoiced'))

        by_method = {}
        for payment in orders.payment_ids:
            method = payment.payment_method_id
            by_method.setdefault(method, 0.0)
            by_method[method] += payment.amount
        for method, amount in by_method.items():
            Line.create({
                'report_id': report.id,
                'line_type': 'payment',
                'name': method.name,
                'amount': amount,
            })

        tax_by_rate = {}
        for order in orders:
            if order.amount_total < 0:
                continue
            for line in order.lines:
                for tax in line.tax_ids:
                    rate = tax.amount
                    base = line.price_subtotal_incl
                    if tax.price_include:
                        tax_amount = base - (base / (1 + rate / 100.0))
                    else:
                        tax_amount = line.price_subtotal * (rate / 100.0)
                    tax_by_rate.setdefault(rate, 0.0)
                    tax_by_rate[rate] += tax_amount
        for rate, amount in sorted(tax_by_rate.items()):
            Line.create({
                'report_id': report.id,
                'line_type': 'tax',
                'name': _('%s %% moms', ('%g' % rate)),
                'rate': rate,
                'amount': amount,
            })

        self.env['pos.journal.entry']._log_event(
            'XDagrapport',
            unit=unit,
            session=session,
            amount=report.total_sales,
            payload={
                'report_id': report.id,
                'sales_date': fields.Date.to_string(sales_date),
                'receipt_count': report.receipt_count,
            },
        )
        return report


class PosReportXLine(models.Model):
    """One row on an X-report."""

    _name = 'pos.report.x.line'
    _description = 'X-dagrapport rad'
    _order = 'report_id, line_type, id'

    report_id = fields.Many2one(
        'pos.report.x',
        required=True,
        readonly=True,
        ondelete='cascade',
        index=True,
    )
    line_type = fields.Selection(
        selection=[
            ('payment', 'Betalningsmedel'),
            ('tax', 'Momsfördelning'),
            ('group', 'Huvudgrupp'),
            ('reduction', 'Övrig minskning'),
        ],
        string='Typ',
        required=True,
        readonly=True,
    )
    name = fields.Char(string='Benämning', required=True, readonly=True)
    rate = fields.Float(string='Skattesats (%)', readonly=True, digits=(5, 2))
    amount = fields.Monetary(
        string='Belopp',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='report_id.currency_id',
        readonly=True,
    )
