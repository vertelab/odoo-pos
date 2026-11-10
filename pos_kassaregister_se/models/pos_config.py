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
from odoo.exceptions import UserError


class PosConfig(models.Model):
    """Attach a registration unit to every POS configuration."""
    _inherit = 'pos.config'

    registration_unit_id = fields.Many2one(
        comodel_name='pos.registration.unit',
        string='Registration Unit',
        compute='_compute_registration_unit',
        store=True,
        readonly=False,
        ondelete='restrict',
        help="The cash register registration unit backing this POS "
             "configuration. Required before a session can be opened.",
    )
    registration_unit_ready = fields.Boolean(
        compute='_compute_registration_unit_ready',
        string='Cash Register Configured',
    )
    sales_street = fields.Char(
        string='Försäljningsställets adress',
        help="Gatunamn och nummer för den fysiska plats där försäljningen "
             "sker. Anges på kassakvittot (7 kap. 1 § b SKVFS 2021:17).",
    )
    sales_zip = fields.Char(string='Postnummer')
    sales_city = fields.Char(
        string='Ort',
        help="Ortsnamn för försäljningsstället (7 kap. 1 § b).",
    )

    @api.depends('name')
    def _compute_registration_unit(self):
        """Resolve the unit that points back at this config.

        The unit is found by searching for ``config_id == self.id``. The
        compute depends on ``name`` only to have a trigger; the unit itself
        is provisioned by ``pos.registration.unit.create()``, which runs when
        the config is created.
        """
        Unit = self.env['pos.registration.unit']
        for config in self:
            config.registration_unit_id = Unit.search(
                [('config_id', '=', config.id)], limit=1)

    @api.depends('registration_unit_id', 'registration_unit_id.name',
                 'registration_unit_id.model_designation',
                 'registration_unit_id.serial_number')
    def _compute_registration_unit_ready(self):
        for config in self:
            unit = config.registration_unit_id
            config.registration_unit_ready = bool(
                unit and unit.name and unit.model_designation
                and unit.serial_number
            )

    def _check_kassaregister_ready(self):
        """Raise when the cash register is not configured for this config.

        4 kap. 2 § SKVFS 2021:17 requires a cash register designation before
        the register is taken into use.
        """
        for config in self:
            if not config.registration_unit_ready:
                raise UserError(_(
                    "The cash register is not configured for '%(config)s'. "
                    "Set the cash register designation, model designation "
                    "(must contain 'SE') and serial number before opening a "
                    "session (4 kap. 2 § SKVFS 2021:17).",
                    config=config.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure a registration unit exists for every new POS config."""
        configs = super().create(vals_list)
        Unit = self.env['pos.registration.unit']
        for config in configs:
            if not Unit.search_count([('config_id', '=', config.id)]):
                Unit.create({
                    'config_id': config.id,
                    'name': config.name,
                    'model_designation': 'ODOO18-SE',
                    'serial_number': 'PENDING-%s' % config.id,
                })
        return configs
