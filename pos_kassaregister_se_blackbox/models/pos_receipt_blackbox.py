# -*- coding: utf-8 -*-
##############################################################################
#
#    POS Kassaregister SE — control unit bridge
#    Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################
"""Control unit bridge — signs every receipt before it is produced.

A control unit (kontrollenhet) or control system (kontrollsystem) signs the
receipt data and returns a control code. The code is stored on the receipt
and written to the journal memory, so that a control code can be traced to
the receipt it belongs to (7 kap. 1 § SKVFS 2021:17).

The transport is deliberately pluggable: ``_blackbox_transport`` is the one
method a deployment overrides to speak to its actual unit. The default
derives the code locally from the receipt data, which is what a stand-alone
register does and what makes the module testable without hardware.
"""
import hashlib
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosReceiptBlackbox(models.Model):
    _inherit = 'pos.receipt'

    # ------------------------------------------------------------------
    # Control unit contract
    # ------------------------------------------------------------------
    def _blackbox_transport(self, receipt_dict):
        """Send ``receipt_dict`` to the control unit, return its control code.

        Override this in a deployment that talks to real hardware. The
        default derives a deterministic code from the receipt data, so the
        same receipt always yields the same code.
        """
        payload = '|'.join(
            str(receipt_dict.get(key) or '')
            for key in (
                'control_unit_serial', 'register_name', 'sequence', 'kind',
                'produced_at', 'amount_total_sek', 'company_vat',
            )
        )
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16].upper()

    def _send_receipt_data(self, receipt_dict):
        """Send the receipt to the control unit and return the control code."""
        self.ensure_one()
        if not receipt_dict.get('control_unit_serial'):
            raise UserError(_(
                "Kontrollenhetens tillverkningsnummer saknas. Kvittot kan "
                "inte signeras (7 kap. 1 § SKVFS 2021:17)."
            ))

        code = self._blackbox_transport(receipt_dict)
        if not code:
            raise UserError(_(
                "Kontrollenheten svarade inte. Kvittot framställs inte."
            ))

        _logger.info(
            "Kontrollkod %s från kontrollenhet %s för kvitto %s",
            code, receipt_dict['control_unit_serial'],
            receipt_dict.get('sequence'),
        )
        return code

    def _control_unit_sign(self):
        """Sign through the control unit instead of locally."""
        self.ensure_one()
        return self._send_receipt_data(self._receipt_data())


class PosSessionBlackbox(models.Model):
    """Require a control unit before a session may be opened.

    A register without a control unit cannot sign its receipts, so it must
    not be taken into use (4 kap. 9 § SKVFS 2021:17). The check lives here,
    in the bridge, so that a deployment without the bridge keeps working —
    but a deployment with the bridge never opens a session it cannot sign.
    """

    _inherit = 'pos.session'

    def _check_control_unit_configured(self):
        """Raise when the register has no control unit or control system."""
        for session in self:
            unit = session.config_id.registration_unit_id
            if not unit or not unit.control_unit_serial:
                raise UserError(_(
                    "Kassan '%(config)s' saknar kontrollenhet. En session "
                    "kan inte öppnas utan en kontrollenhet eller ett "
                    "kontrollsystem (4 kap. 9 § SKVFS 2021:17).",
                    config=session.config_id.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        sessions = super().create(vals_list)
        sessions._check_control_unit_configured()
        return sessions
