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
from odoo import _, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    """Log completed sales and block modification of paid orders."""
    _inherit = 'pos.order'

    def _journal(self, event_type, **kwargs):
        self.ensure_one()
        unit = self.env['pos.registration.unit'].search(
            [('config_id', '=', self.session_id.config_id.id)], limit=1)
        if not unit:
            return self.env['pos.journal.entry']
        return self.env['pos.journal.entry']._log_event(
            event_type, session=self.session_id, order=self, unit=unit,
            **kwargs)

    def action_pos_order_paid(self):
        """Log the receipt when the order is paid.

        ``Kassakvitto`` for a normal sale, ``Returkvitto`` when the order is a
        refund. The amount logged is the absolute order total.
        """
        result = super().action_pos_order_paid()
        for order in self:
            event = 'Returkvitto' if order.amount_total < 0 else 'Kassakvitto'
            order._journal(
                event,
                amount=abs(order.amount_total or 0.0),
                payload={
                    'pos_reference': order.pos_reference,
                    'name': order.name,
                    'amount_total': order.amount_total,
                    'amount_tax': order.amount_tax,
                    'partner_id': order.partner_id.id or False,
                },
            )
        return result

    def write(self, vals):
        """Block modification of a completed sale.

        6 kap. 1 § SKVFS 2021:17: a registered sale must not be changed. Some
        bookkeeping fields are written by Odoo itself after completion, so we
        allow a narrow whitelist and reject the rest.
        """
        allowed = {
            'state', 'account_move', 'invoice_id',
            'message_main_attachment_id', 'access_token',
            'last_order_preparation_change', 'general_note',
        }
        if any(order.state == 'paid' for order in self):
            blocked = set(vals) - allowed
            if blocked:
                raise UserError(_(
                    "A completed sale cannot be modified "
                    "(6 kap. 1 § SKVFS 2021:17). Blocked fields: %(fields)s",
                    fields=', '.join(sorted(blocked)),
                ))
        return super().write(vals)
