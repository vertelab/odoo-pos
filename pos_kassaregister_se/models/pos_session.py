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
from odoo import api, models


class PosSession(models.Model):
    """Log session start and stop to the journal memory."""
    _inherit = 'pos.session'

    def _journal(self, event_type, **kwargs):
        """Write a journal entry for this session, if a unit is configured."""
        self.ensure_one()
        unit = self.env['pos.registration.unit'].search(
            [('config_id', '=', self.config_id.id)], limit=1)
        if not unit:
            # No registration unit means the cash register is not configured
            # for compliance. Do not raise here — ``pos.config.create`` and
            # ``_check_kassaregister_ready`` are the gates that stop a session
            # from being opened at all.
            return self.env['pos.journal.entry']
        return self.env['pos.journal.entry']._log_event(
            event_type, session=self, unit=unit, **kwargs)

    @api.model_create_multi
    def create(self, vals_list):
        """Block session creation when the cash register is not configured.

        In Odoo 18 a POS session is created and opened in one step
        (``PosSession.create`` calls ``action_pos_session_open``), so the gate
        has to sit in ``create`` rather than in an ``open_session_cb``.
        """
        config_ids = {vals['config_id'] for vals in vals_list if vals.get('config_id')}
        if config_ids:
            self.env['pos.config'].browse(list(config_ids))._check_kassaregister_ready()
        sessions = super().create(vals_list)
        for session in sessions:
            session._journal('StartAvKassaregister')
        return sessions

    def action_pos_session_closing_control(self, *args, **kwargs):
        result = super().action_pos_session_closing_control(*args, **kwargs)
        for session in self:
            session._journal('StoppAvKassaregister')
            # A Z-report is produced when the sales day is closed, before the
            # session stops being the authoritative record (7 kap. 3 §).
            session._generate_z_report()
        return result

    def _generate_z_report(self):
        """Produce the Z-dagrapport that closes this session's sales day."""
        self.ensure_one()
        return self.env['pos.report.z']._generate_z_report(self)

    def action_generate_x_report(self):
        """Take an X-dagrapport snapshot without closing the session."""
        self.ensure_one()
        report = self.env['pos.report.x']._generate_x_report(self)
        return {
            'type': 'ir.actions.act_window',
            'name': 'X-dagrapport',
            'res_model': 'pos.report.x',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }
