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
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'POS Kassaregister SE',
    'version': '18.0.1.0.2',
    'category': 'Point of Sale',
    'summary': 'Swedish cash register (kassaregister) per SKVFS 2021:17',
    'description': """
Swedish cash register compliance for Odoo Point of Sale.

Implements the requirements in Skatteverket's regulations:

* SKVFS 2021:17 — krav på kassaregister (technical compliance)
* SKVFS 2021:18 — användning av kassaregister
* SKVFS 2021:16 — standardexport av journalminne (XML)
* SFL 39 kap., BFL 5 kap. 11 § and 42 kap. 2 §

Capabilities
------------
* **Journalminne** — append-only log of *all* cash register activity, not just
  sales. 32 event types, SHA-256 hash chain, PostgreSQL rules denying UPDATE
  and DELETE.
* **Registreringsenhet** — cash register designation, model designation
  (must contain "SE"), serial number, unbroken per-unit sequence.
* **Z-dagrapport** — daily closing report with its own sequence, grand total,
  VAT per rate, receipt count, drawer opening count, payment method split.
* **X-dagrapport** — daily reconciliation that does *not* consume the Z
  sequence number.
* **XML-export** — journal memory export per SKVFS 2021:16, validated against
  Skatteverket's XSD before delivery.
* **Kvittoutskrift** — receipt fields a–m including the point of sale address.
* **Övningsläge** — training mode with "ÖVNING"/"KOPIA"/"EJ KVITTO" marking.
* **Spärrar** — blocks modification of completed sales, registration without
  receipt, more than one copy, and editing of pre-programmed article text.

Deadline
--------
Transitional provision 2 to SKVFS 2021:18 expires 2027-01-01. Cash registers
recording under the older wording of 4 kap. 10 § SKVFS 2021:17 may not be used
after that date. Control fee for deficiencies: SEK 12,500.

Manufacturer
------------
Vertel Sverige AB is the manufacturer per 8 kap. 1 § SKVFS 2021:17. A
manufacturer declaration and journal memory extract must reach Skatteverket no
later than two weeks before market release (8 kap. 4 §).
""",
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'l10n_se',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_registration_unit_views.xml',
        'views/pos_journal_entry_views.xml',
        'views/pos_config_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_kassaregister_se/static/src/**/*',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'application': False,
    'installable': True,
}
