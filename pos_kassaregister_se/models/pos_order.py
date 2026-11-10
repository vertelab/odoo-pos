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
from odoo import _, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    """Log completed sales and block modification of paid orders."""
    _inherit = 'pos.order'

    receipt_ids = fields.One2many(
        comodel_name='pos.receipt',
        inverse_name='order_id',
        string='Kvitton',
        readonly=True,
    )

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
        """Produce the receipt when the order is paid.

        Registration and receipt production are atomic (6 kap. 2 §): the
        receipt is produced first, and if it cannot be produced the sale is
        not registered as completed. ``Kassakvitto`` for a normal sale,
        ``Returkvitto`` when the order is a refund.
        """
        result = super().action_pos_order_paid()
        for order in self:
            event = 'Returkvitto' if order.amount_total < 0 else 'Kassakvitto'
            kind = 'return' if order.amount_total < 0 else 'sale'

            # Produce the receipt before the sale counts as completed. A
            # failure here raises and rolls the payment back.
            receipt = self.env['pos.receipt']._produce(
                order,
                kind='training' if order.session_id.is_training else kind,
            )

            order._journal(
                event,
                amount=abs(order.amount_total or 0.0),
                payload={
                    'pos_reference': order.pos_reference,
                    'name': order.name,
                    'amount_total': order.amount_total,
                    'amount_tax': order.amount_tax,
                    'partner_id': order.partner_id.id or False,
                    'receipt_id': receipt.id,
                    'receipt_sequence': receipt.sequence,
                    'control_code': receipt.control_code,
                },
            )
        return result

    def action_print_receipt(self):
        """Print the receipt, or a copy when one has already been produced.

        A second print is marked "kopia" and reuses the original number; a
        third print is refused (6 kap. 3 §).
        """
        self.ensure_one()
        Receipt = self.env['pos.receipt']
        original = Receipt.search([
            ('order_id', '=', self.id),
            ('kind', 'in', ('sale', 'return', 'training')),
        ], limit=1)
        if not original:
            return super().action_print_receipt()
        if original.copy_count >= 1:
            raise UserError(_(
                "Endast en kopia av ett kassakvitto får framställas. "
                "Kvittot har redan skrivits ut två gånger "
                "(6 kap. 3 § SKVFS 2021:17)."
            ))
        receipt = Receipt._produce(self, kind='copy')
        return self.env.ref(
            'pos_kassaregister_se.action_report_pos_receipt'
        ).report_action(receipt)

    def unlink(self):
        """A registered sale may not be deleted (6 kap. 1 §).

        Deleting a sale would break the unbroken receipt series and the
        journal memory chain, so it is refused outright when the cash
        register is active.
        """
        if any(order.session_id.config_id.registration_unit_id
               for order in self):
            raise UserError(_(
                "En registrerad försäljning kan inte raderas. Kassaregistret "
                "måste bevara samtliga transaktioner "
                "(6 kap. 1 § SKVFS 2021:17)."
            ))
        return super().unlink()

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
        if any(order.state in ('paid', 'done') for order in self):
            blocked = set(vals) - allowed
            if blocked:
                raise UserError(_(
                    "A completed sale cannot be modified "
                    "(6 kap. 1 § SKVFS 2021:17). Blocked fields: %(fields)s",
                    fields=', '.join(sorted(blocked)),
                ))
        return super().write(vals)


class PosOrderLine(models.Model):
    """Guard the lines of a registered sale.

    6 kap. 1 § SKVFS 2021:17 forbids changing a registered sale. ``PosOrder``
    enforces that on the order itself, but a line can be reached directly
    through ``order.lines`` and would otherwise be writable after payment.
    This override closes that path.
    """

    _inherit = 'pos.order.line'

    def write(self, vals):
        """Block modification of a line belonging to a completed sale."""
        if any(line.order_id.state in ('paid', 'done') for line in self):
            raise UserError(_(
                "En rad i en registrerad försäljning kan inte ändras. "
                "Kassaregistret måste bevara samtliga transaktioner "
                "(6 kap. 1 § SKVFS 2021:17)."
            ))
        return super().write(vals)

    def unlink(self):
        """Block deletion of a line belonging to a completed sale."""
        if any(line.order_id.state in ('paid', 'done') for line in self):
            raise UserError(_(
                "En rad i en registrerad försäljning kan inte raderas. "
                "Kassaregistret måste bevara samtliga transaktioner "
                "(6 kap. 1 § SKVFS 2021:17)."
            ))
        return super().unlink()
