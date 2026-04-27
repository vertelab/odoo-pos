# -*- coding: utf-8 -*-

{
    "name": "GreenGate Online POS Integration",
    "version": "18.0.1.0",
    "summary": "POS integration with GreenGate Online",
    "description": """
        This module connects Odoo 18 Point of Sale with GreenGate Online,
    """,
    "category": "Point of Sale",
    "author": "Vertel Sverige AB",
    "website": "https://vertel.se",
    "license": "AGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/pos_config_views.xml",
        "views/green_gate_api_log.xml",
        "views/template.xml",  
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
