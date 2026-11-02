# -*- coding: utf-8 -*-
{
    'name': 'POS Kassaregister SE — kontrollenhetsbrygga',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Kopplar kassaregistret till en kontrollenhet eller ett kontrollsystem',
    'description': """
Kontrollenhetsbrygga för det svenska kassaregistret.

Kassaregisterlagen kräver att varje kassakvitto signeras av en
kontrollenhet eller ett kontrollsystem innan det framställs. Den här
modulen är drivrutinen: den tar kvittodata från kärnmodulen, skickar den
till kontrollenheten och skriver tillbaka kontrollkoden.

Utan den här modulen (eller en annan drivrutin) vägrar kassaregistret att
framställa kvitton — det gissar aldrig en kontrollkod.
""",
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se',
    'license': 'LGPL-3',
    'depends': ['pos_kassaregister_se'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
