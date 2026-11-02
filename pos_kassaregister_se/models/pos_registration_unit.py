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
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosRegistrationUnit(models.Model):
    """A physical cash register (registreringsenhet).

    Every ``pos.config`` is backed by exactly one registration unit. The unit
    carries the cash register designation printed on receipts, the model
    designation (which must contain "SE" per 4 kap. 6 § SKVFS 2021:17) and the
    serial number reported to Skatteverket.
    """

    _name = 'pos.registration.unit'
    _description = 'Cash Register Registration Unit'
    _order = 'name'

    name = fields.Char(
        string='Cash Register Designation',
        required=True,
        help="Designation printed on every receipt (fält e) and in the "
             "Z report. Must be unique within the company.",
    )
    config_id = fields.Many2one(
        comodel_name='pos.config',
        string='POS Configuration',
        required=True,
        ondelete='restrict',
        index=True,
        help="The POS configuration this registration unit belongs to.",
    )
    company_id = fields.Many2one(
        related='config_id.company_id',
        store=True,
        readonly=True,
    )
    model_designation = fields.Char(
        string='Model Designation',
        required=True,
        default='ODOO18-SE',
        help="Model designation of the cash register. Must contain 'SE' "
             "(4 kap. 6 § SKVFS 2021:17).",
    )
    serial_number = fields.Char(
        string='Serial Number',
        required=True,
        help="Manufacturing number of the registration unit (fält l on the "
             "receipt).",
    )
    control_unit_serial = fields.Char(
        string='Control Unit Serial',
        help="Manufacturing number of the certified control unit "
             "(kontrollenhet) or control system (kontrollsystem), depending "
             "on which is connected.",
    )
    sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Journal Sequence',
        readonly=True,
        copy=False,
        help="Unbroken sequence for journal memory entries on this unit "
             "(4 kap. 2 § SKVFS 2021:17).",
    )
    z_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Z-report Sequence',
        readonly=True,
        copy=False,
        help="Unbroken sequence reserved for Z-dagrapporter only, separate "
             "from the receipt series (7 kap. 3 § SKVFS 2021:17).",
    )
    receipt_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Receipt Sequence',
        readonly=True,
        copy=False,
        help="Unbroken series for kassakvitton and returkvitton on this unit. "
             "Only those two kinds consume a number — copies, training and "
             "pro forma receipts do not (7 kap. 1 § SKVFS 2021:17).",
    )
    journal_entry_ids = fields.One2many(
        comodel_name='pos.journal.entry',
        inverse_name='unit_id',
        string='Journal Entries',
        readonly=True,
    )
    journal_entry_count = fields.Integer(
        compute='_compute_journal_entry_count',
        string='Journal Entries',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)',
         'The cash register designation must be unique within the company.'),
        ('config_uniq', 'unique(config_id)',
         'A POS configuration can only have one registration unit.'),
    ]

    @api.depends('journal_entry_ids')
    def _compute_journal_entry_count(self):
        for unit in self:
            unit.journal_entry_count = len(unit.journal_entry_ids)

    @api.constrains('model_designation')
    def _check_model_designation(self):
        """Model designation must contain 'SE' (4 kap. 6 § SKVFS 2021:17)."""
        for unit in self:
            if not unit.model_designation or 'SE' not in unit.model_designation.upper():
                raise ValidationError(_(
                    "The model designation must contain 'SE' "
                    "(4 kap. 6 § SKVFS 2021:17). Got: %(value)s",
                    value=unit.model_designation,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        """Create a no-gap journal sequence for every new unit."""
        # Validate config_id before provisioning anything. Without this the
        # method would first create three ir.sequence records with the code
        # suffix "None" and only then hit the NOT NULL constraint on
        # config_id, leaving orphan sequences behind and surfacing the
        # failure as a raw NotNullViolation instead of a readable error.
        for vals in vals_list:
            if not vals.get('config_id'):
                raise ValidationError(_(
                    "A registration unit must be linked to a POS "
                    "configuration (4 kap. 2 § SKVFS 2021:17)."))
        for vals in vals_list:
            if not vals.get('sequence_id'):
                config_id = vals.get('config_id')
                name = vals.get('name') or _('Cash register')
                vals['sequence_id'] = self.env['ir.sequence'].create({
                    'name': _('Journal memory: %(unit)s', unit=name),
                    'code': 'pos.journal.entry.%s' % config_id,
                    'implementation': 'no_gap',
                    'padding': 8,
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': self.env['pos.config'].browse(
                        config_id).company_id.id or self.env.company.id,
                }).id
            if not vals.get('z_sequence_id'):
                config_id = vals.get('config_id')
                name = vals.get('name') or _('Cash register')
                vals['z_sequence_id'] = self.env['ir.sequence'].create({
                    'name': _('Z-dagrapport: %(unit)s', unit=name),
                    'code': 'pos.report.z.%s' % config_id,
                    'implementation': 'no_gap',
                    'padding': 6,
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': self.env['pos.config'].browse(
                        config_id).company_id.id or self.env.company.id,
                }).id
            if not vals.get('receipt_sequence_id'):
                config_id = vals.get('config_id')
                name = vals.get('name') or _('Cash register')
                vals['receipt_sequence_id'] = self.env['ir.sequence'].create({
                    'name': _('Kassakvitto: %(unit)s', unit=name),
                    'code': 'pos.receipt.%s' % config_id,
                    'implementation': 'no_gap',
                    'padding': 4,
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': self.env['pos.config'].browse(
                        config_id).company_id.id or self.env.company.id,
                }).id
        return super().create(vals_list)

    def action_view_journal_entries(self):
        """Open the journal memory filtered to this unit."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Memory — %(unit)s', unit=self.name),
            'res_model': 'pos.journal.entry',
            'view_mode': 'list,form',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
        }

    def _check_chain_unit(self):
        """Verify the hash chain for this registration unit.

        Walks every entry in sequence order and checks both links: that
        ``previous_hash`` matches the preceding entry's hash, and that
        ``entry_hash`` matches a recomputation over the stored data.

        :return: list of dicts describing broken links; empty when intact
        """
        self.ensure_one()
        Journal = self.env['pos.journal.entry']
        broken = []
        expected_previous = ''
        for entry in Journal.search([('unit_id', '=', self.id)],
                                    order='sequence asc'):
            if entry.previous_hash != expected_previous:
                broken.append({
                    'sequence': entry.sequence,
                    'reason': 'previous_hash does not match the preceding entry',
                })
            if entry._compute_entry_hash() != entry.entry_hash:
                broken.append({
                    'sequence': entry.sequence,
                    'reason': 'entry_hash does not match the stored data',
                })
            expected_previous = entry.entry_hash
        return broken

    def action_check_chain(self):
        """Verify the hash chain and report the result to the user."""
        self.ensure_one()
        broken = self._check_chain_unit()
        if broken:
            details = '\n'.join(
                'seq %(sequence)s: %(reason)s' % item for item in broken)
            raise UserError(_(
                "The journal memory hash chain is broken for %(unit)s:\n"
                "%(details)s",
                unit=self.name, details=details,
            ))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Chain intact'),
                'message': _(
                    'The journal memory hash chain for %(unit)s verifies.',
                    unit=self.name),
                'type': 'success',
                'sticky': False,
            },
        }
