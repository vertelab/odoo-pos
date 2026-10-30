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
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestRegistrationUnit(TransactionCase):
    """Covers manual tests T1, T2 and T6 from the use case.

    Note: ``pos.registration.unit`` has ``unique(config_id)`` — one unit per
    POS config. Tests that need several units therefore create additional
    POS configs, not additional units on the same config.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Unit = cls.env['pos.registration.unit']
        cls.config_1 = cls.env['pos.config'].create({'name': 'Kassa 1'})
        cls.config_2 = cls.env['pos.config'].create({'name': 'Kassa 2'})

    def _new_config(self, name):
        """Create a POS config and return its auto-created unit."""
        config = self.env['pos.config'].create({'name': name})
        return self.Unit.search([('config_id', '=', config.id)], limit=1)

    def test_t1_unit_created_per_config(self):
        """T1 — a registration unit exists for every POS config."""
        for config in (self.config_1, self.config_2):
            unit = self.Unit.search([('config_id', '=', config.id)])
            self.assertEqual(len(unit), 1,
                             "Exactly one registration unit per POS config")

    def test_t1_unit_has_sequence(self):
        """T1 — the auto-created unit gets a no-gap sequence."""
        unit = self.Unit.search([('config_id', '=', self.config_1.id)], limit=1)
        self.assertTrue(unit.sequence_id)
        self.assertEqual(unit.sequence_id.implementation, 'no_gap')

    def test_t2_model_designation_requires_se(self):
        """T2 — model designation must contain 'SE' (4 kap. 6 §)."""
        unit = self.Unit.search([('config_id', '=', self.config_1.id)], limit=1)
        with self.assertRaises(ValidationError):
            unit.model_designation = 'ODOO-18'

    def test_t2_model_designation_se_accepted(self):
        """T2 — a designation containing 'SE' is accepted."""
        unit = self.Unit.search([('config_id', '=', self.config_1.id)], limit=1)
        unit.model_designation = 'ODOO18-SE'
        self.assertEqual(unit.model_designation, 'ODOO18-SE')

    def test_t2_model_designation_case_insensitive(self):
        """T2 — the check is case insensitive."""
        unit = self.Unit.search([('config_id', '=', self.config_1.id)], limit=1)
        unit.model_designation = 'odoo18-se'
        self.assertEqual(unit.model_designation, 'odoo18-se')

    def test_t6_separate_series_per_unit(self):
        """T6 — two units have independent sequence series."""
        unit_1 = self.Unit.search([('config_id', '=', self.config_1.id)], limit=1)
        unit_2 = self.Unit.search([('config_id', '=', self.config_2.id)], limit=1)
        Journal = self.env['pos.journal.entry']
        entry_1 = Journal._log_event('StartAvKassaregister', unit=unit_1)
        entry_2 = Journal._log_event('StartAvKassaregister', unit=unit_2)
        self.assertEqual(entry_1.sequence, 1)
        self.assertEqual(entry_2.sequence, 1,
                         "Both units start at 1 — the series are separate")
        self.assertNotEqual(entry_1.unit_id, entry_2.unit_id)

    def test_session_blocked_without_complete_unit(self):
        """3.5 — session creation is blocked without a complete unit."""
        config = self.env['pos.config'].create({'name': 'Kassa utan serienr'})
        unit = self.Unit.search([('config_id', '=', config.id)], limit=1)
        # serial_number is required at the database level, so simulate a
        # half-configured register by blanking it through the ORM instead.
        unit.serial_number = ''
        self.assertFalse(unit.serial_number)
        self.assertFalse(config.registration_unit_ready)
        with self.assertRaises(UserError):
            self.env['pos.session'].create({'config_id': config.id})
