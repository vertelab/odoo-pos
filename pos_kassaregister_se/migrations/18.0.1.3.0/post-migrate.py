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
##############################################################################
"""Backfill the receipt sequence added in 18.0.1.2.0.

``receipt_sequence_id`` was introduced together with the kassakvitto
(receipt) model. ``create()`` provisions the three sequences for every new
registration unit, but units that already existed when the field was added
never went through ``create()`` — they keep ``receipt_sequence_id = NULL``.

A NULL receipt sequence is not harmless: the first receipt printed on such a
unit would have no unbroken series, which violates 7 kap. 1 § SKVFS 2021:17.
This script provisions the missing sequence for every unit that lacks one.

The script is idempotent — running it twice provisions nothing the second
time.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        # Fresh install: create() already provisioned every sequence.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    Unit = env['pos.registration.unit']
    Sequence = env['ir.sequence']

    units = Unit.with_context(active_test=False).search([
        ('receipt_sequence_id', '=', False),
    ])
    if not units:
        _logger.info(
            "pos_kassaregister_se: all registration units already have a "
            "receipt sequence"
        )
        return

    for unit in units:
        code = 'pos.receipt.%s' % unit.config_id.id
        sequence = Sequence.search([('code', '=', code)], limit=1)
        if not sequence:
            sequence = Sequence.create({
                'name': 'Kassakvitto: %s' % unit.name,
                'code': code,
                'implementation': 'no_gap',
                'padding': 4,
                'number_next': 1,
                'number_increment': 1,
                'company_id': (unit.config_id.company_id.id
                               or env.company.id),
            })
        unit.receipt_sequence_id = sequence.id

    _logger.info(
        "pos_kassaregister_se: provisioned receipt sequences for %s "
        "registration unit(s)", len(units),
    )
