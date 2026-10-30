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
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestJournalEntry(TransactionCase):
    """Covers manual tests T3, T4 and T5 from the use case."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env['pos.config'].create({'name': 'Kassa Journal'})
        cls.unit = cls.env['pos.registration.unit'].search(
            [('config_id', '=', cls.config.id)], limit=1)
        cls.Journal = cls.env['pos.journal.entry']

    def test_t3_sequence_is_unbroken(self):
        """T3 — sequence numbers are 1, 2, 3 … without gaps."""
        for _i in range(5):
            self.Journal._log_event('RegistreraArtikel', unit=self.unit)
        entries = self.Journal.search(
            [('unit_id', '=', self.unit.id)], order='sequence asc')
        self.assertEqual(entries.mapped('sequence'), [1, 2, 3, 4, 5])

    def test_t3_deleted_article_stays_in_journal(self):
        """T3 — a deleted article remains in the journal memory."""
        self.Journal._log_event(
            'RegistreraArtikel', unit=self.unit,
            payload={'product': 'Kaffe', 'qty': 1})
        self.Journal._log_event(
            'RaderaRegistreradArtikel', unit=self.unit,
            payload={'product': 'Kaffe', 'qty': 1})
        deleted = self.Journal.search([
            ('unit_id', '=', self.unit.id),
            ('event_type', '=', 'RaderaRegistreradArtikel'),
        ])
        self.assertEqual(len(deleted), 1,
                         "The deletion event is itself recorded")

    def test_t4_orm_write_blocked(self):
        """T4 — journal entries cannot be modified through the ORM."""
        entry = self.Journal._log_event('Kassakvitto', unit=self.unit,
                                        amount=100.0)
        with self.assertRaises(UserError):
            entry.write({'event_type': 'Returkvitto'})

    def test_t4_orm_unlink_blocked(self):
        """T4 — journal entries cannot be deleted through the ORM."""
        entry = self.Journal._log_event('Kassakvitto', unit=self.unit,
                                        amount=100.0)
        with self.assertRaises(UserError):
            entry.unlink()

    def test_t5_chain_intact(self):
        """T5 — a freshly written chain verifies without errors."""
        for _i in range(4):
            self.Journal._log_event('RegistreraArtikel', unit=self.unit)
        entries = self.Journal.search(
            [('unit_id', '=', self.unit.id)], order='sequence asc')
        self.assertEqual(entries[0].previous_hash, '',
                         "The first entry has no predecessor")
        self.assertEqual(self.unit._check_chain_unit(), [])

    def test_t5_chain_detects_tampering(self):
        """T5 — a changed amount breaks the chain."""
        entry = self.Journal._log_event('Kassakvitto', unit=self.unit,
                                        amount=100.0)
        # Simulate tampering by bypassing the ORM guard.
        self.env.cr.execute(
            "UPDATE pos_journal_entry SET amount = 50.0 WHERE id = %s",
            (entry.id,),
        )
        entry.invalidate_recordset()
        broken = self.unit._check_chain_unit()
        self.assertTrue(broken, "Tampering must be detected")
        self.assertEqual(broken[0]['sequence'], entry.sequence)

    def test_unknown_event_type_rejected(self):
        """Only the 31 verified event types are accepted."""
        with self.assertRaises(UserError):
            self.Journal._log_event('PåhittadHandelse', unit=self.unit)

    def test_amount_and_payload_stored(self):
        """The entry stores amount and payload for the XML export."""
        entry = self.Journal._log_event(
            'Kassakvitto', unit=self.unit, amount=250.0,
            payload={'pos_reference': 'Order 00001-001-0001'})
        self.assertEqual(entry.amount, 250.0)
        self.assertEqual(entry.payload['pos_reference'],
                         'Order 00001-001-0001')

    def test_db_guard_revokes_write_privileges(self):
        """T4 — UPDATE/DELETE are revoked on the journal memory table.

        The local test database runs as a PostgreSQL superuser, which
        bypasses grants, so the direct SQL attempt cannot prove anything
        here. What is verifiable — and what matters in production — is that
        the privileges are gone for the application role.
        """
        self.env.cr.execute("""
            SELECT grantee, privilege_type
            FROM information_schema.role_table_grants
            WHERE table_name = 'pos_journal_entry'
              AND privilege_type IN ('UPDATE', 'DELETE')
        """)
        grants = self.env.cr.fetchall()
        self.assertEqual(
            grants, [],
            "UPDATE/DELETE must be revoked on pos_journal_entry, found: %s"
            % (grants,),
        )
