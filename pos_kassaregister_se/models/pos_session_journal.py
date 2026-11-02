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
"""Journal memory events for cash drawer, cash float and clock (4 kap.).

The journal memory records every operation that changes the state of the
cash register: cash drawer openings without a sale, changes to the cash
float, price inquiries, use of the clear function and clock adjustments.
None of these produce an order, so they can only be captured at the point
where the operation happens.
"""
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosSessionCashDrawer(models.Model):
    """Cash drawer openings and cash float changes (4 kap. 4, 6 §§)."""
    _inherit = 'pos.session'

    cash_float_start = fields.Monetary(
        string='Växelkassa vid start',
        currency_field='currency_id',
        help="Kontantbelopp i kassalådan när sessionen öppnades.",
    )

    def _current_cash_float(self):
        """Return the cash float as the register currently knows it.

        ``cash_float_start`` only tracks float changes made through
        :meth:`log_cash_float_change`. Until the first such change the
        authoritative figure is the opening float the cashier counted,
        which Odoo stores in ``cash_register_balance_start``.
        """
        self.ensure_one()
        if self.cash_float_start:
            return self.cash_float_start
        return self.cash_register_balance_start or 0.0

    def log_cash_drawer_opening(self, reason=None):
        """Log an opening of the cash drawer without a sale (4 kap. 4 §).

        Opening the drawer without a sale must be recorded in the journal
        memory, with the reason if one is given.
        """
        self.ensure_one()
        return self._journal(
            'OppnaKassaladaVidNollforsaljning',
            payload={'reason': reason or ''},
        )

    def log_cash_float_change(self, new_float, reason=None):
        """Log a change to the cash float (4 kap. 6 §).

        The change is logged with both the old and the new amount so that
        the journal memory shows what the float was before and after.
        """
        self.ensure_one()
        old = self._current_cash_float()
        entry = self._journal(
            'ForandraVaxelkassa',
            amount=new_float,
            payload={
                'old_float': old,
                'new_float': new_float,
                'difference': new_float - old,
                'reason': reason or '',
            },
        )
        self.write({'cash_float_start': new_float})
        return entry

    def log_price_inquiry(self, product=None, price=None):
        """Log a price inquiry (4 kap. 9 §).

        A price inquiry is a read-only operation, but the register must still
        record that it happened.
        """
        self.ensure_one()
        return self._journal(
            'StallaPrisforfragan',
            payload={
                'product_id': product.id if product else False,
                'product_name': product.display_name if product else '',
                'price': price or 0.0,
            },
        )

    def log_clear(self, scope=None):
        """Log use of the clear function (4 kap. 9 §)."""
        self.ensure_one()
        return self._journal(
            'AnvandaClear',
            payload={'scope': scope or ''},
        )

    def log_clock_adjustment(self, old_time, new_time, reason=None):
        """Log a clock adjustment (4 kap. 10 §).

        Adjusting the register's clock must be recorded with both the old
        and the new time, so that the time series in the journal memory can
        be reconstructed.
        """
        self.ensure_one()
        delta = (new_time - old_time).total_seconds()
        return self._journal(
            'StallaOmKlockan',
            payload={
                'old_time': fields.Datetime.to_string(old_time),
                'new_time': fields.Datetime.to_string(new_time),
                'delta_seconds': delta,
                'reason': reason or '',
            },
        )


class PosOrderLineParking(models.Model):
    """Parked articles (4 kap. 5 §).

    Parking an article removes it from the current sale without deleting it.
    The journal memory must show that the article was parked, that the
    parking was resumed, and if the parked article was later deleted or
    changed.
    """
    _inherit = 'pos.order.line'

    def action_park(self, reason=None):
        """Log that an article was parked."""
        self.ensure_one()
        return self.order_id._journal(
            'ParkeraRegistreradArtikel',
            amount=abs(self.price_subtotal_incl or 0.0),
            payload={
                'line_id': self.id,
                'product_id': self.product_id.id,
                'product_name': self.full_product_name or '',
                'qty': self.qty,
                'reason': reason or '',
            },
        )

    def action_resume_parking(self):
        """Log that a parked article was resumed."""
        self.ensure_one()
        return self.order_id._journal(
            'OppnaParkering',
            amount=abs(self.price_subtotal_incl or 0.0),
            payload={
                'line_id': self.id,
                'product_id': self.product_id.id,
                'product_name': self.full_product_name or '',
                'qty': self.qty,
            },
        )

    def action_delete_parked(self, reason=None):
        """Log that a parked article was deleted (4 kap. 5 §).

        A parked article may be deleted, but the deletion must be recorded.
        """
        self.ensure_one()
        return self.order_id._journal(
            'RaderaParkeradArtikel',
            amount=abs(self.price_subtotal_incl or 0.0),
            payload={
                'line_id': self.id,
                'product_id': self.product_id.id,
                'product_name': self.full_product_name or '',
                'qty': self.qty,
                'reason': reason or '',
            },
        )

    def action_change_parked(self, new_qty=None, reason=None):
        """Log a change to a parked article."""
        self.ensure_one()
        return self.order_id._journal(
            'AndraParkeradArtikel',
            payload={
                'line_id': self.id,
                'product_id': self.product_id.id,
                'product_name': self.full_product_name or '',
                'old_qty': self.qty,
                'new_qty': new_qty if new_qty is not None else self.qty,
                'reason': reason or '',
            },
        )
