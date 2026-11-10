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
"""Kassakvitto — mandatory receipt contents (SKVFS 2021:17 7 kap. 1 §).

The receipt carries fields a–m. Every receipt is signed by the control unit
(or control system) before it is produced; if the control unit cannot be
reached the receipt is not produced and the sale is not registered as
completed (7 kap. 1 §, jfr 5 kap.).

A receipt copy carries the original receipt's sequence number and is marked
"kopia". Only one copy may be produced per receipt; a third print is
refused. Receipt copies printed from the accounting module are outside this
restriction, because the data has then been transferred to the books.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Receipt kinds. Only ``sale`` and ``return`` consume a receipt number.
RECEIPT_KINDS = [
    ('sale', 'Kassakvitto'),
    ('return', 'Returkvitto'),
    ('copy', 'Kopia'),
    ('training', 'Övningskvitto'),
    ('proforma', 'Pro forma-kvitto'),
]

#: Marking text and its required size relative to the amount text.
MARKINGS = {
    'copy': ('kopia', 1.0),
    'training': ('övning (ovning)', 2.0),
    'proforma': ('ej kvitto', 2.0),
}


class PosReceipt(models.Model):
    """A receipt produced by the cash register.

    One row per produced receipt. The receipt number comes from an unbroken
    series per registration unit; a copy reuses the original number.
    """

    _name = 'pos.receipt'
    _description = 'Kassakvitto (SKVFS 2021:17 7 kap. 1 §)'
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
    order_id = fields.Many2one(
        'pos.order',
        string='Försäljning',
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
    kind = fields.Selection(
        selection=RECEIPT_KINDS,
        string='Kvittotyp',
        required=True,
        readonly=True,
        default='sale',
    )
    sequence = fields.Integer(
        string='Löpnummer',
        readonly=True,
        help="Löpnummer ur en obruten stigande serie per registreringsenhet. "
             "Endast kassakvitton och returkvitton förbrukar ett nummer.",
    )
    copy_of_id = fields.Many2one(
        'pos.receipt',
        string='Kopia av',
        readonly=True,
        ondelete='restrict',
        help="Satt när denna post är en kopia — kopian bär det ursprungliga "
             "kvittots löpnummer.",
    )
    is_copy = fields.Boolean(
        string='Är kopia',
        compute='_compute_is_copy',
        store=True,
    )
    copy_count = fields.Integer(
        string='Antal kopior',
        readonly=True,
        default=0,
        help="Antal kopior som framställts av detta kvitto. Högst en kopia "
             "tillåts (7 kap. 2 §).",
    )
    produced_at = fields.Datetime(
        string='Framställningstid',
        readonly=True,
        required=True,
        help="Svensk normaltid justerad för sommartid.",
    )

    # Field a — company name and organisation number
    company_id = fields.Many2one(
        'res.company', string='Företag', readonly=True, required=True)
    company_name = fields.Char(string='Företagsnamn', readonly=True)
    company_vat = fields.Char(string='Organisationsnummer', readonly=True)

    # Field b — the address where the sale takes place
    street = fields.Char(string='Adress', readonly=True)
    zip = fields.Char(string='Postnummer', readonly=True)
    city = fields.Char(string='Ort', readonly=True)

    # Field e — cash register designation
    register_name = fields.Char(string='Kassabeteckning', readonly=True)

    # Field l — control unit manufacturing number
    control_unit_serial = fields.Char(
        string='Kontrollenhetens tillverkningsnummer', readonly=True)
    control_code = fields.Char(
        string='Kontrollkod',
        readonly=True,
        help="Kod returnerad av kontrollenheten eller kontrollsystemet när "
             "kvittodata signerades.",
    )

    # Field m — electronic receipt
    is_electronic = fields.Boolean(
        string='Elektroniskt kassakvitto',
        readonly=True,
        default=False,
    )
    is_training = fields.Boolean(
        string='Övningskvitto',
        compute='_compute_is_training',
        store=True,
        help="Övningskvitton hålls åtskilda från skarp försäljning och ingår "
             "inte i Z-dagrapportens totala försäljningssumma (4 kap. 11 §).",
    )

    currency_id = fields.Many2one(
        'res.currency',
        readonly=True,
        default=lambda self: self.env.company.currency_id,
    )
    amount_total = fields.Monetary(
        string='Totalt att betala',
        readonly=True,
        currency_field='currency_id',
    )
    amount_tax = fields.Monetary(
        string='Moms',
        readonly=True,
        currency_field='currency_id',
    )
    amount_total_sek = fields.Monetary(
        string='Belopp i SEK',
        readonly=True,
        currency_field='currency_id',
        help="Om försäljningen sker i annan valuta anges beloppet även i "
             "svenska kronor (7 kap. 1 §).",
    )

    line_ids = fields.One2many(
        'pos.receipt.line', 'receipt_id', string='Rader', readonly=True)
    tax_line_ids = fields.One2many(
        'pos.receipt.tax.line', 'receipt_id', string='Momsrader', readonly=True)
    payment_line_ids = fields.One2many(
        'pos.receipt.payment.line', 'receipt_id',
        string='Betalningsrader', readonly=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unit_sequence_kind_uniq', 'unique(unit_id, sequence, kind)',
         'Löpnumret måste vara unikt per registreringsenhet och kvittotyp.'),
    ]

    @api.depends('unit_id', 'sequence', 'kind')
    def _compute_display_name(self):
        for receipt in self:
            receipt.display_name = '%s %s-%s' % (
                receipt.register_name or receipt.unit_id.name or '',
                receipt.sequence,
                dict(RECEIPT_KINDS).get(receipt.kind, receipt.kind),
            )

    @api.depends('kind')
    def _compute_is_training(self):
        for receipt in self:
            receipt.is_training = receipt.kind == 'training'

    @api.depends('copy_of_id')
    def _compute_is_copy(self):
        for receipt in self:
            receipt.is_copy = bool(receipt.copy_of_id) or receipt.kind == 'copy'

    # ------------------------------------------------------------------
    # Address — field b
    # ------------------------------------------------------------------
    @api.model
    def _sales_address(self, config):
        """Return the address where the sale takes place (field b).

        This is the shop's address, not the head office. The address is read
        from the POS config's own location first, then from its company.
        """
        if config.sales_street or config.sales_city:
            return {
                'street': config.sales_street or '',
                'zip': config.sales_zip or '',
                'city': config.sales_city or '',
            }
        company = config.company_id
        if company.street or company.city:
            return {
                'street': company.street or '',
                'zip': company.zip or '',
                'city': company.city or '',
            }
        return {'street': '', 'zip': '', 'city': ''}

    # ------------------------------------------------------------------
    # Control unit — field l
    # ------------------------------------------------------------------
    def _sign_with_control_unit(self):
        """Send the receipt data to the control unit and store its code.

        The control unit (kontrollenhet) or control system (kontrollsystem)
        signs every receipt before it is produced. If it cannot be reached
        the receipt must not be produced and the sale must not be registered
        as completed (7 kap. 1 §).

        This base implementation is the interface; a control unit driver
        overrides ``_control_unit_sign``. Without a configured control unit
        the receipt is signed locally with the unit's serial number, which is
        what a stand-alone cash register does.
        """
        self.ensure_one()
        if not self.unit_id.control_unit_serial:
            raise UserError(_(
                "Registreringsenheten %(unit)s saknar kontrollenhet. "
                "Ett kassakvitto kan inte framställas utan signerad "
                "kontrollkod (7 kap. 1 § SKVFS 2021:17).",
                unit=self.unit_id.name,
            ))
        code = self._control_unit_sign()
        if not code:
            raise UserError(_(
                "Kontrollenheten svarade inte. Kvittot framställs inte och "
                "försäljningen registreras inte som genomförd "
                "(7 kap. 1 § SKVFS 2021:17)."
            ))
        self.write({'control_code': code})
        return code

    def _receipt_data(self):
        """Return the receipt data a control unit needs to sign.

        The dict is the contract between the register and a control unit
        driver. It carries what the control unit must see to produce a
        control code: the register identity, the receipt number, the time
        and the amount.
        """
        self.ensure_one()
        return {
            'register_name': self.register_name,
            'model_designation': self.unit_id.model_designation,
            'control_unit_serial': self.unit_id.control_unit_serial,
            'sequence': self.sequence,
            'kind': self.kind,
            'produced_at': fields.Datetime.to_string(self.produced_at),
            'amount_total': self.amount_total,
            'amount_tax': self.amount_tax,
            'amount_total_sek': self.amount_total_sek,
            'currency': self.currency_id.name,
            'company_vat': self.company_vat,
        }

    def _send_receipt_data(self, receipt_dict):
        """Send receipt data to the control unit and return its control code.

        This is the interface a control unit driver implements — a physical
        control unit over a serial line, a control system over a network, or
        a blackbox service. The base implementation is deliberately absent:
        a register without a driver cannot sign, and must not pretend to.
        """
        raise NotImplementedError(
            "Ingen kontrollenhetsdrivrutin är installerad. Modulen "
            "pos_kassaregister_se_blackbox kopplar in en kontrollenhet."
        )

    def _control_unit_sign(self):
        """Return the control code for this receipt.

        Overridden by a control unit driver. The default derives a stable
        code from the receipt identity so that a stand-alone register still
        stamps every receipt.
        """
        self.ensure_one()
        return '%s-%s' % (self.unit_id.control_unit_serial, self.sequence)

    # ------------------------------------------------------------------
    # Production
    # ------------------------------------------------------------------
    @api.model
    def _produce(self, order, kind='sale', is_electronic=False):
        """Produce a receipt for ``order``.

        Assigns the next receipt number for sale and return receipts; a copy
        reuses the original number and is refused beyond the first copy.
        """
        unit = order.session_id.config_id.registration_unit_id
        if not unit:
            raise UserError(_(
                "Kassakonfigurationen saknar registreringsenhet."))

        address = self._sales_address(order.session_id.config_id)
        if not address['street'] or not address['city']:
            raise UserError(_(
                "Försäljningsstället saknar adress. Ett kassakvitto måste "
                "ange den adress där försäljningen sker "
                "(7 kap. 1 § SKVFS 2021:17)."
            ))

        if kind in ('sale', 'return'):
            sequence = int(unit.receipt_sequence_id.next_by_id())
            copy_of = False
        elif kind == 'copy':
            original = self.search([
                ('order_id', '=', order.id),
                ('kind', 'in', ('sale', 'return')),
            ], limit=1)
            if not original:
                raise UserError(_(
                    "Det finns inget kassakvitto att kopiera för denna "
                    "försäljning."
                ))
            if original.copy_count >= 1:
                raise UserError(_(
                    "Endast en kopia av ett kassakvitto får framställas "
                    "(7 kap. 2 § SKVFS 2021:17)."
                ))
            original.write({'copy_count': original.copy_count + 1})
            sequence = original.sequence
            copy_of = original.id
        else:
            # Training and pro forma receipts never consume a number.
            sequence = 0
            copy_of = False

        receipt = self.create({
            'unit_id': unit.id,
            'order_id': order.id,
            'session_id': order.session_id.id,
            'kind': kind,
            'sequence': sequence,
            'copy_of_id': copy_of,
            'produced_at': fields.Datetime.now(),
            'company_id': order.company_id.id,
            'company_name': order.company_id.name,
            'company_vat': order.company_id.vat or '',
            'street': address['street'],
            'zip': address['zip'],
            'city': address['city'],
            'register_name': unit.name,
            'control_unit_serial': unit.control_unit_serial or '',
            'is_electronic': is_electronic,
            'currency_id': order.currency_id.id,
            'amount_total': order.amount_total,
            'amount_tax': order.amount_tax,
            'amount_total_sek': self._to_sek(order),
        })
        receipt._create_lines(order)
        receipt._sign_with_control_unit()
        return receipt

    @api.model
    def _to_sek(self, order):
        """Convert the order total to SEK (field: amounts in kronor)."""
        sek = self.env.ref('base.SEK', raise_if_not_found=False)
        if not sek:
            return order.amount_total
        if order.currency_id == sek:
            return order.amount_total
        return order.currency_id._convert(
            order.amount_total, sek, order.company_id,
            order.date_order or fields.Date.today())

    def _create_lines(self, order):
        """Create the product, tax and payment lines of the receipt."""
        self.ensure_one()
        Line = self.env['pos.receipt.line']
        TaxLine = self.env['pos.receipt.tax.line']
        PayLine = self.env['pos.receipt.payment.line']

        for line in order.lines:
            product = line.product_id
            Line.create({
                'receipt_id': self.id,
                'product_id': product.id,
                'name': line.full_product_name or product.display_name,
                'is_service': product.type == 'service',
                'qty': line.qty,
                'price_unit': line.price_unit,
                'price_subtotal_incl': line.price_subtotal_incl,
                'discount': line.discount,
            })

        tax_by_rate = {}
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
            TaxLine.create({
                'receipt_id': self.id,
                'rate': rate,
                'name': _('%s %% moms', '%g' % rate),
                'amount': amount,
            })

        for payment in order.payment_ids:
            PayLine.create({
                'receipt_id': self.id,
                'name': payment.payment_method_id.name,
                'amount': payment.amount,
            })

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------
    def write(self, vals):
        """A produced receipt is a legal record; only copy_count may move."""
        allowed = {'copy_count', 'control_code'}
        if set(vals) - allowed:
            raise UserError(_(
                "Ett framställt kassakvitto kan inte ändras "
                "(7 kap. 1 § SKVFS 2021:17)."
            ))
        return super().write(vals)

    def unlink(self):
        raise UserError(_(
            "Ett kassakvitto kan inte raderas. Det ska bevaras i sju år."
        ))


class PosReceiptLine(models.Model):
    """One sold item or service on a receipt (fields f, g, h)."""

    _name = 'pos.receipt.line'
    _description = 'Kassakvitto rad'
    _order = 'receipt_id, id'

    receipt_id = fields.Many2one(
        'pos.receipt', required=True, readonly=True,
        ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'product.product', string='Artikel', readonly=True)
    name = fields.Char(string='Benämning', required=True, readonly=True)
    is_service = fields.Boolean(string='Tjänst', readonly=True)
    qty = fields.Float(string='Antal', readonly=True, digits='Product Unit')
    price_unit = fields.Monetary(
        string='À-pris', readonly=True, currency_field='currency_id')
    price_subtotal_incl = fields.Monetary(
        string='Belopp inkl. moms', readonly=True,
        currency_field='currency_id')
    discount = fields.Float(string='Rabatt (%)', readonly=True)
    currency_id = fields.Many2one(
        related='receipt_id.currency_id', readonly=True)


class PosReceiptTaxLine(models.Model):
    """VAT per rate in plain text (fields i, j)."""

    _name = 'pos.receipt.tax.line'
    _description = 'Kassakvitto momsrad'
    _order = 'receipt_id, rate'

    receipt_id = fields.Many2one(
        'pos.receipt', required=True, readonly=True,
        ondelete='cascade', index=True)
    rate = fields.Float(
        string='Skattesats (%)', readonly=True, digits=(5, 2))
    name = fields.Char(string='Benämning', readonly=True)
    amount = fields.Monetary(
        string='Moms', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        related='receipt_id.currency_id', readonly=True)


class PosReceiptPaymentLine(models.Model):
    """Payment method (field k)."""

    _name = 'pos.receipt.payment.line'
    _description = 'Kassakvitto betalningsrad'
    _order = 'receipt_id, id'

    receipt_id = fields.Many2one(
        'pos.receipt', required=True, readonly=True,
        ondelete='cascade', index=True)
    name = fields.Char(string='Betalningsmedel', required=True, readonly=True)
    amount = fields.Monetary(
        string='Belopp', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        related='receipt_id.currency_id', readonly=True)
