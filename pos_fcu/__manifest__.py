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

{
    'name': 'POS Financial Control Unit',
    'version': '0.1',
    'category': 'pos',
    'summary': 'Sends transactions to a FCU',
    'licence': 'AGPL-3',
    'description': """
According to tax regulations in some countries POS and Cash registers has to send
a copy of their transactions to a Financial Control Unit, a sield piece
of harware from Tax Agency (Skatteverket in Sweden).
The POS-system should be connected to a certified control unit that reads the
registrations in the cash register and generates a control code and has
to be declaired by manufacutrer.

https://www.skatteverket.se/rattsinformation/arkivforrattsligvagledning/foreskrifter/konsoliderade/2009/skvfs20091.5.5a4c883511f42795f7c8000651.html
https://www.skatteverket.se/download/18.3810a01c150939e893f20d61/1453380934762/613B02.pdf

To be approved, a cash register needs to meet the following requirements
• It should have a manufacturer’s declaration – note
that a new declaration must also be issued with
each new version of the cash register.
• It should be connected to a certified control unit
that reads the registrations in the cash register and
generates a control code.


https://www.skatteverket.se/foretagochorganisationer/foretagare/kassaregister/anmalakassaregisterandringarochfel.4.69ef368911e1304a62580008748.html

""",
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['point_of_sale',],
    'external_dependencies': {
        'python': ['jsonrpclib'],
    },
    'data': [],
    'application': False,
    'installable': True,
    'demo': [],
}
# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4:
