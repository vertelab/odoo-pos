# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017- Vertel (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _
import simplejson
import os
import odoo
import time
import random
import werkzeug.utils

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import module_boot, login_redirect

import logging
_logger = logging.getLogger(__name__)


class PosController(http.Controller):

    @http.route('/pos_fcu/init', type="json", auth="public")
    def init(self):
        notifications = request.env['im_chat.message'].init_messages()
        return notifications

    @http.route('/pos_fcu/post', type="json", auth="public")
    def post(self, uuid, message_type, message_content):
        # execute the post method as SUPERUSER_ID
        message_id = request.env['im_chat.message'].post(uuid, message_type, message_content)
        return message_id


class account_journal(models.Model):
    _inherit = 'account.journal'

    journal_user = fields.Boolean(string='PoS Payment Method', help='Check this box if this journal define a payment method that can be used in point of sales.')
    amount_authorized_diff = fields.Float(string='Amount Authorized Difference', help='This field depicts the maximum difference allowed between the ending balance and the theorical cash when closing a session, for non-POS managers. If this maximum is reached, the user will have an error message at the closing of his session saying that he needs to contact his manager.')
    self_checkout_payment_method = fields.Boolean(string='Self Checkout Payment Method', default=False)


class account_cash_statement(models.Model):
    _inherit = 'account.bank.statement'

    pos_session_id = fields.Many2one(comodel_name='pos.session', copy=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
