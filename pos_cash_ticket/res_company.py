# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
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
from openerp import models, fields, api, _
from openerp import http
from openerp.http import request
import werkzeug
from openerp.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)


class res_company(models.Model):
    _inherit = 'res.company'

    pos_logo = fields.Binary(string="POS Logo")

class companyLogo(http.Controller):

    @http.route(['/company_logo.png'], type='http', auth="public", website=True)
    def company_logo(self):
        company = request.env['res.users'].browse(request.env.uid).company_id
        response = werkzeug.wrappers.Response()
        if company.pos_logo:
            return request.env['website']._image('res.company', company.id, 'pos_logo', response, max_width=None, max_height=200)
        elif company.logo:
            return request.env['website']._image('res.company', company.id, 'logo', response, max_width=None, max_height=200)
        else:
            return None

