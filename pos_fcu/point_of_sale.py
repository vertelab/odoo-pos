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

class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_fcu_vat = fields.Boolean(string='FCU VAT', help='Checking this will make the FCU count this tax as VAT.')

class pos_config(models.Model):
    """ POS config  """
    _inherit = 'pos.config'

    iface_fcu = fields.Boolean(string="Financial Control Unit")
    fcu_contract = fields.Char(string="FCU Contract")
    fcu_server = fields.Char("FCU Server (http://server[:port])")
    cash_register_id = fields.Char()
    registry_id = fields.Many2one(string='Registry', comodel_name='pos.registry', compute='_get_registry_id')

    def _get_registry_id(self):
        self.registry_id = self.env['pos.registry'].sudo().search([('pos_id', '=', self.id)])

    def fcu_post(self, reciept, app_id):
        return "control_code"

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
g. total försäljningssumma för olika huvudgrupper om huvudgrupper används                   vad är en huvudgrupp? kategori?
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

# javascript
# PaymentScreenWidget.validate_order > finalize_validation > push_order
#     * registrera med FCU
#     * skriv ut kvitto

# ReceiptScreenWidget.print
#     * registrera utskrift av kvittokopia

#pos_fcu.py
class pos_registry(models.Model):
    _name = 'pos.registry'
    _description = 'POS Registry'

    serial_no = fields.Char(string='Serial')
    line_ids = fields.One2many(comodel_name='pos.registry.line', inverse_name='registry_id', string='Registry Lines')
    pos_id = fields.Many2one(string='POS', comodel_name='pos.config', required=True)

    # ~ @api.multi
    # ~ def write(self, values):
        # ~ raise Warning(_("You are not allowed to change the POS registry!"))

    # ~ @api.multi
    # ~ def unlink(self):
        # ~ raise Warning(_("You are not allowed to change the POS registry!"))

class pos_registry_line(models.Model):
    _name = 'pos.registry.line'
    _description = 'POS Registry Line'

    registry_id = fields.Many2one(comodel_name='pos.registry', string='Registry')
    receipt_id = fields.Many2one(comodel_name='pos.registry.receipt', string='Receipt')
    type = fields.Selection([
        ('receipt', 'Receipt'),
        ('open', 'Registry Opened'),
        ('price_change', 'Price Change')])
    date = fields.Datetime(string='Date')

    # ~ @api.multi
    # ~ def write(self, values):
        # ~ raise Warning(_("You are not allowed to change the POS registry!"))

    # ~ @api.multi
    # ~ def unlink(self):
        # ~ raise Warning(_("You are not allowed to change the POS registry!"))

class pos_registry_receipt(models.Model):
    _name = 'pos.registry.receipt'
    _description = 'POS Registry Receipt'

    control_code = fields.Char(string='Control Code', help="Control code from the FCU.")
    vat_25 = fields.Float(string='VAT 25%')
    vat_12 = fields.Float(string='VAT 12%')
    vat_6 = fields.Float(string='VAT 6%')
    discount = fields.Float(string='Discount Total')
    is_copy = fields.Float(string='Copy', help="This is a copy of a receipt.")


    refund = fields.Boolean(string='Refund')

    # ~ @api.multi
    # ~ def write(self, values):
        # ~ raise Warning(_("You are not allowed to change the POS registry!"))

    # ~ @api.multi
    # ~ def unlink(self):
        # ~ raise Warning(_("You are not allowed to change the POS registry!"))

# ~ class pos_registry_receipt_line(models.Model):
    # ~ _name = 'pos.registry.receipt.line'
    # ~ _description = 'POS Registry Receipt Line'

    # ~ name = fields.Char(string='Name')
    # ~ product_id = fields.Many2one(string='Product', comodel_name='product.product')
    # ~ price =

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

    @api.multi
    def get_total_sales_sum_for_different_main_groups_if_main_groups_are_used(self):
        self.ensure_one()
        return 0.0

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

    @api.multi
    def get_number_of_pos_receipts(self):
        self.ensure_one()
        return len(self.env['pos.order.line'].search([('order_id.session_id', '=', self.id)]))

    @api.multi
    def get_number_of_latches(self):
        self.ensure_one()
        return len(self.statement_ids.mapped('line_ids'))

    @api.multi
    def get_number_of_receipt_copies_and_amounts(self):
        self.ensure_one()
        return 0.0

    @api.multi
    def get_number_of_registrations_in_exercise_mode_and_amount(self):
        self.ensure_one()
        return 0.0

    @api.multi
    def get_sales_sum_distributed_by_different_way_of_payment(self):
        self.ensure_one()
        result = ''
        statements = self.statement_ids
        for idx, statement in enumerate(statements):
            result += '%s: %s' %(statement.journal_id.name, statement.balance_end_real - statement.balance_start)
            if idx != len(statements) - 1:
                result += '\n'
        return result

    @api.multi
    def get_number_of_returns_and_amounts(self):
        self.ensure_one()
        return 0.0

    @api.multi
    def get_discount(self):
        self.ensure_one()
        return 0.0

    @api.multi
    def get_other_registrations_that_reduced_todays_sales_and_to_what_amount(self):
        self.ensure_one()
        return 0.0

    @api.multi
    def get_number_of_unfinished_sales(self):
        self.ensure_one()
        return len(self.statement_ids.filtered(lambda s: s.state != 'confirm'))

    @api.multi
    def get_grand_total_sales(self):
        self.ensure_one()
        return sum([(s.balance_end_real - s.balance_start) for s in self.statement_ids])

    @api.multi
    def get_grand_total_return(self):
        self.ensure_one()
        return 0.0

    @api.multi
    def get_grand_total_netto(self):
        self.ensure_one()
        return sum([(s.balance_end_real - s.balance_start) for s in self.statement_ids])

# ~ import jsonrpclib

class fcu_post(object):

    def __init__(self):
        # server proxy object
        url = "http://%s:%s/jsonrpc" % ('localhost', '8069')
        server = jsonrpclib.Server(url)

        # log in the given database
        uid = server.call(service="common", method="login", args=['pos', 'admin', 'admin'])

        # helper function for invoking model methods
        def invoke(model, method, *args):
            args = ['pos', uid, 'admin', model, method] + list(args)
            return server.call(service="object", method="execute", args=args)

        # create a new note
        args = {
            'name' : 'anders',
            'login' : 'This is another note',
            'create_uid': uid,
        }
        note_id = invoke('res.users', 'search', [('name','ilike','Demo User')])
        for u in note_id:
            print u
            print u['name']
        #~ note_id = invoke('note.note', 'create', args)


class pos_fcu_json(http.Controller):

    @http.route(['/pos_fcu/<string:form_name>/add', ], type='json', auth="public",)
    def fcu_add(self, form_name=False, **post):
        return {
            'form_name': form_name,
            #'appcert': appcert,
            'uid': uid,
            'context': context,
#            'request.method': request.method,
#            'request.args': request.args,
            'post': post,
        }
    @http.route(['/post_fcu/<string:contract>/post', ], type='json', auth="public",)
    def fcu_post(self, contract=None, appcert=None, **post):
        contract = request.env['account.analytic.account'].search([('cash_register_id','=',contract)])
        if contract:
            return {
                'control_code': contract.fcu_post(reciept, appcert),
            }
        return {
            'appcert': appcert,
            'contract': contract,
            'uid': uid,
            'context': context,
            'params': request.params,
#            'request.method': request.method,
#            'request.args': request.args,
            'post': post,
        }

# curl -H "Content-type:application/json" -X POST localhost:8069/fcu/kalle/add -d '{"method":"pluyy"}'|python -m json.tool
# openerp-server.conf:
#db_name = pos
#dbfilter = pos
#list_db = false

"""
https://www.skatteverket.se/rattsinformation/arkivforrattsligvagledning/foreskrifter/konsoliderade/2009/skvfs200912.5.2e56d4ba1202f950120800012422.html
http://www4.skatteverket.se/download/18.7d4d4f0515244e542f5a9fd/1453733397842/SKVFS+2009+2.pdf
http://www.skatteverket.se/download/18.76a43be412206334b89800012557/SKVFS+2009.03.pd
https://www.skatteverket.se/foretagochorganisationer/foretagare/kassaregister/anmalakassaregisterandringarochfel.4.69ef368911e1304a62580008748.html
Data    Beskrivning     Format
Datum och tid   Datum och klockslag för försäljning enligt 28 § c SKVFS 2009:1  12 siffror, format YYYYMMDDttmm
Organisationsnummer     Företagets organisationsnummer eller personnummer enligt 28 § a SKVFS 2009:1    10 siffror
Kassabeteckning     Kassabeteckning enligt 10 § SKVFS 2009:3    Maximalt 16 alfanumeriska tecken
Löpnummer   Löpnummer enligt 28 § d SKVFS 2009:1    Maximalt 12 siffror
Kvittotyp   Beroende av kvittotyp ska motsvarande text skapas:  Maximalt 6 alfanumeriska tecken
    - normal
    - kopia
    - ovning
    - profo
Returbelopp     Absolutvärde för summerat belopp returposter på ett kvitto  Maximalt 14 tecken inkl. decimalkomma*)
Försäljningsbelopp  Belopp för kunden att betala enligt 28 § h SKVFS 2009:1     Maximalt 14 tecken inkl. decimalkomma*)
Momssats 1; Momssumma 1     Första momssats i procent; Belopp första momssats enligt 28 § j SKVFS 2009:1    <Procentsats>;<Belopp> Procentsats: maximalt 5 tecken inkl. decimalkomma.*) Belopp: maximalt 14 tecken inkl. decimalkomma.*) Fältlängd: 20 tecken inkl. semikolon.
Momssats 2; Momssumma 2     Andra momssats i procent; Belopp andra momssats enligt 28 § j SKVFS 2009:1  Procentsats: maximalt 5 tecken inkl. decimalkomma.*) Belopp: maximalt 14 tecken inkl. decimalkomma.*) Fältlängd: 20 tecken inkl. semikolon.
Momssats 3; Momssumma 3     Tredje momssats i procent; Belopp tredje momssats enligt 28 § j SKVFS 2009:1    <Procentsats>;<Belopp> Procentsats: maximalt 5 tecken inkl. decimalkomma.*) Belopp: maximalt 14 tecken inkl. decimalkomma.*) Fältlängd: 20 tecken inkl. semikolon.
Momssats 4; Momssumma 4     Fjärde momssats i procent; Belopp fjärde momssats enligt 28 § j SKVFS 2009:1    <Procentsats>;<Belopp> Procentsats: maximalt 5 tecken inkl. decimalkomma.*) Belopp: maximalt 14 tecken inkl. decimalkomma.*) Fältlängd: 20 tecken inkl. semikolon.
*) Det ska alltid vara två siffror efter decimalkommat


5 §    Data ska vara i ASCII teckenformat och högerjusterad, eventuellt ifylld med blanka tecken (mellanslag) för att uppnå angiven fältlängd.


SKVFS 2014:9

5 kap. Funktioner som ska finnas
1 §  Ett kassaregister ska kunna registrera växelkassa och förändring av växelkassa.
2 §  Ett kassaregister ska kunna registrera olika slag av betalningsmedel.
3 §  Om ett kassaregister kan hantera mer än ett företags registreringar ska det ha en funktion som utvisar vilka företag det hanterar. En sådan funktion får endast finnas om kassaregisterprogrammet på ett säkert sätt kan hålla registreringarna åtskilda. Detsamma gäller om ett kassaregister kan hantera registreringar som sker i olika verksamheter inom ett företag eller hanterar flera tunna klienter som ansluts till kass a register pro grammet.
4 §  Det ska ur ett kassaregister kunna tas fram aktuella uppgifter om programmeringar och inställningar som upp fyller kraven på behandlingshistorik enligt 5 kap. 11 § bok föringslagen (1999:1078).
5 §  Om ett kassaregister har en funktion för utskrift av kvittokopia, övningskvitto eller pro forma kvitto ska dessa vara tydligt markerade med orden kopia , övning ( ovning ) respektive ej kvitto. Den markerande texten ska inte kunna ändras och den ska vara minst dubbelt så stor som den text som anger belopp.
6 §  Ett kassaregister som är avsett att användas med ett kontrollsystem ska kunna ta emot och skicka information som kontrollsystemets buffringsprogram skickar eller begär att få från kassaregistret. Ett kassaregister får skicka uppgifter som behövs till buffringsprogrammet.
7 §  Ett kassaregisterprogram ska kunna skicka de kvittodata som en kontrollenhet eller ett kontrollsystem behöver.  Kvittodatabelopp ska vara i svenska kronor och ören.

6 kap. Funktioner som inte är tillåtna
1 § Ett kassaregister får inte ha en funktionsom möjliggör att en användare kan ta bort, förändra eller lägga till uppgifter i redan gjorda registreringar.
2 § Ett kassaregister får inte vara så konstruerat att det är möjligt att registrera försäljningsbelopp utan att kassaregistret samtidigt skriver ut ett kassakvitto i pappersform eller tar fram och skickar ett elektroniskt kassakvitto.
3 § Ett kassaregister får inte kunna skriva ut mer än en kopia av ett kassakvitto. Detta gäller oavsett om kassakvittot är i pappersform eller i elektronisk form.
4 § Ett kassaregister får inte ha en funktion som medger att förprogrammerad text på artiklar och tjänster kan förändras vid registreringen.

"""


class account_analytic_account(models.Model):
    _inherit = "account.analytic.account"

    cash_register_id = fields.Char()
    app_id = fields.Char()

    def fcu_post(self,reciept,app_id):
        return "control_code"
