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
"""Wizard that produces the SKVFS 2021:16 export for download."""
import base64

from odoo import _, fields, models
from odoo.exceptions import UserError


class PosJournalExportWizard(models.TransientModel):
    _name = 'pos.journal.export.wizard'
    _description = 'Exportera journalminne enligt SKVFS 2021:16'

    unit_ids = fields.Many2many(
        'pos.registration.unit',
        string='Registreringsenheter',
        required=True,
        help="En eller flera registreringsenheter. Varje post bär den "
             "kassabeteckning den registrerades under.",
    )
    date_from = fields.Date(string='Från och med', required=True)
    date_to = fields.Date(string='Till och med', required=True)
    file_data = fields.Binary(string='Fil', readonly=True)
    file_name = fields.Char(string='Filnamn', readonly=True)
    state = fields.Selection(
        [('draft', 'Utkast'), ('done', 'Klar')],
        default='draft',
    )

    def action_export(self):
        """Build, validate and log the export, then offer the download."""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("Startdatum måste vara före slutdatum."))

        result = self.env['pos.journal.export'].export(
            self.unit_ids, self.date_from, self.date_to)

        self.write({
            'file_data': result['content'],
            'file_name': result['filename'],
            'state': 'done',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=pos.journal.export.wizard'
                   '&id=%s&field=file_data&filename_field=file_name'
                   '&download=true' % self.id,
            'target': 'self',
        }
