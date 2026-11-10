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
"""Install and uninstall hooks.

``post_init_hook``
    Creates a ``pos.registration.unit`` for every existing ``pos.config`` so
    that an upgrade of an already running database is compliant immediately.

``uninstall_hook``
    Makes the journal memory table read-only instead of dropping it. The
    journal memory must be preserved for seven years (BFL 7 kap.), so
    uninstalling the module must not destroy the audit trail.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _apply_db_guard(env):
    """Make the journal memory append-only at the database level.

    The ORM blocks write/unlink and the hash chain detects tampering, but a
    database superuser can still UPDATE or DELETE rows directly. Revoking the
    privileges closes that hole: the table becomes append-only for the
    application role (4 kap. 10 § SKVFS 2021:17).
    """
    env.cr.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'pos_journal_entry'
            ) THEN
                -- The application role usually owns the table, and an
                -- owner keeps its privileges unless they are revoked by
                -- name. Revoke from the current role explicitly.
                EXECUTE format(
                    'REVOKE UPDATE, DELETE ON pos_journal_entry FROM %I',
                    current_user);
                REVOKE UPDATE, DELETE ON pos_journal_entry FROM PUBLIC;
                COMMENT ON TABLE pos_journal_entry IS
                    'Journal memory — append only. Retained 7 years per '
                    'BFL 7 kap. and 4 kap. SKVFS 2021:17.';
            END IF;
        END
        $$;
    """)
    _logger.info(
        "pos_kassaregister_se: pos_journal_entry is now append-only "
        "(UPDATE/DELETE revoked)"
    )


def post_init_hook(env):
    """Create a registration unit for every existing POS config."""
    configs = env['pos.config'].search([])
    Unit = env['pos.registration.unit']
    created = 0
    for config in configs:
        if Unit.search_count([('config_id', '=', config.id)]):
            continue
        Unit.create({
            'config_id': config.id,
            'name': config.name,
            'model_designation': 'ODOO18-SE',
            'serial_number': 'PENDING-%s' % config.id,
        })
        created += 1
    _logger.info(
        "pos_kassaregister_se: created %s registration unit(s) for %s POS config(s)",
        created, len(configs),
    )
    _apply_db_guard(env)


def uninstall_hook(env):
    """Keep the journal memory table, but make it read-only.

    The journal memory is an audit trail with a seven year retention
    requirement. Dropping the table on uninstall would destroy evidence that
    Skatteverket may request. We therefore revoke write access instead.
    """
    env.cr.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'pos_journal_entry'
            ) THEN
                REVOKE INSERT, UPDATE, DELETE ON pos_journal_entry FROM PUBLIC;
                COMMENT ON TABLE pos_journal_entry IS
                    'Journal memory retained per BFL 7 kap. (7 years). '
                    'pos_kassaregister_se was uninstalled; table kept read-only.';
            END IF;
        END
        $$;
    """)
    _logger.warning(
        "pos_kassaregister_se uninstalled: pos_journal_entry kept read-only "
        "for the seven year retention requirement (BFL 7 kap.)"
    )
