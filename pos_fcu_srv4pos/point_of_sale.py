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
from odoo.exceptions import except_orm, Warning, RedirectWarning

from odoo import http
from odoo.http import request
from odoo import SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)


class pos_config(models.Model):
    """ POS config  """
    _inherit = 'pos.config'

    iface_fcu = fields.Boolean(string="Financial Control Unit")
    fcu_contract = fields.Char(string="FCU Contract")
    fcu_server = fields.Char("FCU Server (http://server[:port])")
    cash_register_id = fields.Char()

class pos_order(models.Model):
    """ POS order  """
    _inherit = 'pos.order'

    fcu_id = fields.Char()

    #~ @api.multi
    #~ def action_done(self):
        #~ _logger.error('POS: %s' % self)
        #~ for s in self:
            #~ _logger.error('POS: %s' % s)
            #~ super(pos_order, s).action_done()
            #~ raise Warning('Action Done')
        #~ return True

    #~ @api.multi
    #~ def create_from_ui(self,orders):
        #~ _logger.error('POS: %s' % orders)
        #~ for s in self:
            #~ o_list = super(pos_order, s).create_from_ui(orders)
        #~ return o_list
        #~ #raise Warning('Action create_from_ui %s %s %s' % (orders,o_list,self))

    def _process_order(self, order):
        _logger.error('POS: %s' % order)
        res = super(pos_order, self)._process_order(order)
        _logger.error('POS: %s' % res)
        o = self.browse(res.id)
        # pos_client = fcu_post({'reciept':''},contract,app_id)
        o.fcu_id = "controle_code %s" %o.id # get controle_code
        return res
    
    # ~ @api.model
    # ~ def create_from_ui(self, orders):
        # ~ """Create new POS orders from the POS UI."""
        # ~ # Keep only new orders
        # ~ submitted_references = [o['data']['name'] for o in orders]
        # ~ pos_order = self.search([('pos_reference', 'in', submitted_references)])
        # ~ existing_orders = pos_order.read(['pos_reference'])
        # ~ existing_references = set([o['pos_reference'] for o in existing_orders])
        # ~ orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]
        # ~ order_ids = []

        # ~ for tmp_order in orders_to_save:
            # ~ to_invoice = tmp_order['to_invoice']
            # ~ order = tmp_order['data']
            # ~ if to_invoice:
                # ~ self._match_payment_to_invoice(order)
            # ~ pos_order = self._process_order(order)
            # ~ order_ids.append(pos_order.id)

            # ~ try:
                # ~ pos_order.action_pos_order_paid()
            # ~ except psycopg2.OperationalError:
                # ~ # do not hide transactional errors, the order(s) won't be saved!
                # ~ raise
            # ~ except Exception as e:
                # ~ _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

            # ~ if to_invoice:
                # ~ pos_order.action_pos_order_invoice()
                # ~ pos_order.invoice_id.sudo().action_invoice_open()
                # ~ pos_order.account_move = pos_order.invoice_id.move_id
        # ~ return order_ids
    
    """
Z-dagrapport 
3 § En Z-dagrapport ska minst innehålla uppgifter om
a. företagets namn och organisationsnummer eller personnummer
b. datum och klockslag för när rapporten tas fram
c. löpnummer ur en obruten stigande nummerserie                                             
d. uppgift att det är en Z-dagrapport
e. kassabeteckning                                                                          pos_config.cash_register_id
f. total försäljningssumma (summerade försäljningsbelopp)
g. total försäljningssumma för olika huvudgrupper om huvudgrupper används
h. mervärdesskatten fördelad på olika mervärdesskattesatser
i. växelkassa
j. antal sålda varor
k. antal sålda tjänster
l. antal kassakvitton
m. antal lådöppningar
n. antal kvittokopior och belopp
o. antal registreringar i övningsläge och belopp
p. försäljningssumman fördelad på olika betalningsmedel
q. antal returer och belopp
r. rabatter
s. övriga registreringar som minskat dagens försäljningsbelopp och till vilket belopp
t. antal oavslutade försäljningar och belopp
u. grand total försäljning
v. grand total retur
w. grand total netto.
"""

#pos_fcu.py
class pos_registry(models.Model):
    _name = 'pos.registry'
    _description = 'POS Registry'
    
    serial_no = fields.Char(string='Serial')
    line_ids = fields.One2many(comodel_name='pos.registry.line', inverse_name='registry_id', string='Registry Lines')

    @api.multi
    def write(self, values):
        raise Warning(_("You are not allowed to change the POS registry!"))

    @api.multi
    def unlink(self):
        raise Warning(_("You are not allowed to change the POS registry!"))
    
class pos_registry_line(models.Model):
    _name = 'pos.registry.line'
    _description = 'POS Registry Line'

    registry_id = fields.Many2one(comodel_name='pos.registry', string='Registry')

    @api.multi
    def write(self, values):
        raise Warning(_("You are not allowed to change the POS registry!"))

    @api.multi
    def unlink(self):
        raise Warning(_("You are not allowed to change the POS registry!"))

class pos_session(models.Model):
    _inherit = 'pos.session'

    @api.multi
    def get_company_name(self):
        self.ensure_one()
        return self.env.user.partner_id.company_id.name

    @api.multi
    def get_company_orgnr(self):
        self.ensure_one()
        return self.env.user.partner_id.company_id.company_registry

    @api.multi
    def get_company_currency(self):
        self.ensure_one()
        return self.env.user.partner_id.company_id.currency_id.symbol

    @api.multi
    def get_sale_total_amount(self):
        self.ensure_one()
        return sum(self.statement_ids.mapped('total_entry_encoding'))

    # only on tax in line
    @api.multi
    def get_tax_mp1_amount(self):
        self.ensure_one()
        lines = self.env['pos.order.line'].search([('order_id.session_id', '=', self.id)]).filtered(lambda l: self.env['account.tax'].search([('name', '=', 'MP1')]) in l.tax_ids)
        return sum([(line.price_subtotal_incl - line.price_subtotal) for line in lines])

    @api.multi
    def get_tax_mp2_amount(self):
        self.ensure_one()
        lines = self.env['pos.order.line'].search([('order_id.session_id', '=', self.id)]).filtered(lambda l: self.env['account.tax'].search([('name', '=', 'MP2')]) in l.tax_ids)
        return sum([(line.price_subtotal_incl - line.price_subtotal) for line in lines])

    @api.multi
    def get_tax_mp3_amount(self):
        self.ensure_one()
        lines = self.env['pos.order.line'].search([('order_id.session_id', '=', self.id)]).filtered(lambda l: self.env['account.tax'].search([('name', '=', 'MP3')]) in l.tax_ids)
        return sum([(line.price_subtotal_incl - line.price_subtotal) for line in lines])

    @api.multi
    def get_incoming_exchange(self):
        return sum(self.statement_ids.mapped('balance_start'))

    @api.multi
    def get_sold_goods_quantity(self):
        self.ensure_one()
        return sum(self.env['pos.order.line'].search([('order_id.session_id', '=', self.id)]).filtered(lambda l: l.product_id.type != 'service').mapped('qty'))

    @api.multi
    def get_sold_services_quantity(self):
        self.ensure_one()
        return sum(self.env['pos.order.line'].search([('order_id.session_id', '=', self.id)]).filtered(lambda l: l.product_id.type == 'service').mapped('qty'))

