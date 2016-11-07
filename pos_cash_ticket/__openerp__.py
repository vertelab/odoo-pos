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

{
    'name': 'POS Cash Ticket',
    'version': '0.1',
    'category': 'pos',
    'summary': 'Ticket with more information of the buyer',
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



Fakturan ska innehålla

    Datum då fakturan är utställd
    Fakturanummer
    Säljarens och köparens adress
    Säljarens momsregistreringsnummer
    Köparens momsregistreringsnummer i vissa fall (t ex vid EU-handel)
    Transaktionens art och omfattning
    Datum då leverans eller tillhandahållande skett eller a contobetalning (delbetalning, vanligen i form av förskottsbetalning) gjorts om det är annat än fakturadatum
    Specifikation (vad fakturan omfattar)
    Pris
    Beskattningsunderlag för varje momssats eller undantag
    Tillämpad momssats
    Momsbelopp
    Vid befrielse från moms – hänvisning till relevant bestämmelse.

I aktiebolag är följande uppgifter obligatoriska

    I vilken kommun bolaget har sitt säte.
    Bolagets organisationsnummer.
    Bolagets namn.



""",
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['point_of_sale',],
    'external_dependencies': {
        'python': ['jsonrpclib'],
    },
    'data': ['point_of_sale.xml','res_company_view.xml'],
    'qweb': ['static/src/xml/*.xml'],
    'application': False,
    'installable': True,
    'demo': [],
}
# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4:
