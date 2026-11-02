# -*- coding: utf-8 -*-
"""Tests for the control unit bridge (tasks 9.1–9.4)."""
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBlackbox(TransactionCase):
    """The bridge signs receipts through a control unit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        company = cls.env.company
        company.write({
            'vat': 'SE556677889901',
            'company_registry': '556677-8899',
        })
        cls.config = cls.env['pos.config'].create({
            'name': 'Blackbox-kassa',
            'sales_street': 'Storgatan 1',
            'sales_zip': '111 22',
            'sales_city': 'Stockholm',
        })
        cls.unit = cls.config.registration_unit_id
        cls.unit.write({'control_unit_serial': 'CU-99900000000001'})

    _seq = 0

    def _receipt(self):
        """A receipt record with the fields the contract needs.

        Each call gets its own sequence number — (unit, sequence, kind) is
        unique, as it must be for an unbroken series.
        """
        type(self)._seq += 1
        return self.env['pos.receipt'].create({
            'unit_id': self.unit.id,
            'company_id': self.env.company.id,
            'kind': 'sale',
            'sequence': type(self)._seq,
            'produced_at': fields.Datetime.now(),
            'register_name': self.unit.name,
            'company_name': self.env.company.name,
            'company_vat': self.env.company.vat,
            'amount_total': 250.0,
            'amount_tax': 50.0,
            'amount_total_sek': 250.0,
        })

    # ------------------------------------------------------------------
    # 9.1 — the contract exists and fails loudly when unimplemented
    # ------------------------------------------------------------------
    def test_contract_method_exists(self):
        """Kärnmodulen har kontraktet _send_receipt_data."""
        self.assertTrue(
            hasattr(self.env['pos.receipt'], '_send_receipt_data'),
            "Kontraktet _send_receipt_data saknas i kärnmodulen",
        )

    def test_receipt_data_carries_what_the_unit_needs(self):
        """Kvittodatat bär det kontrollenheten behöver för att signera."""
        data = self._receipt()._receipt_data()
        for key in ('control_unit_serial', 'register_name', 'sequence',
                    'kind', 'produced_at', 'amount_total_sek', 'company_vat'):
            self.assertIn(key, data, "Kvittodatat saknar %s" % key)
        self.assertEqual(data['control_unit_serial'], 'CU-99900000000001')

    # ------------------------------------------------------------------
    # 9.2 — the bridge is installed and overrides the contract
    # ------------------------------------------------------------------
    def test_bridge_overrides_the_contract(self):
        """Bryggan implementerar kontraktet."""
        receipt = self._receipt()
        self.assertEqual(
            type(receipt)._send_receipt_data.__qualname__.split('.')[0],
            'PosReceiptBlackbox',
            "Bryggan överskriver inte _send_receipt_data",
        )

    # ------------------------------------------------------------------
    # 9.3 — the control code is produced and stored
    # ------------------------------------------------------------------
    def test_control_code_is_returned(self):
        """Bryggan returnerar en kontrollkod."""
        receipt = self._receipt()
        code = receipt._send_receipt_data(receipt._receipt_data())
        self.assertTrue(code, "Ingen kontrollkod returnerades")
        self.assertEqual(len(code), 16)

    def test_control_code_is_deterministic(self):
        """Samma kvitto ger samma kontrollkod."""
        receipt = self._receipt()
        data = receipt._receipt_data()
        self.assertEqual(
            receipt._send_receipt_data(data),
            receipt._send_receipt_data(data),
        )

    def test_different_receipts_get_different_codes(self):
        """Olika kvitton ger olika kontrollkoder."""
        first = self._receipt()
        second = self._receipt()
        self.assertNotEqual(
            first._send_receipt_data(first._receipt_data()),
            second._send_receipt_data(second._receipt_data()),
        )

    def test_signing_stores_the_code_on_the_receipt(self):
        """Signeringen sparar kontrollkoden på kvittot."""
        receipt = self._receipt()
        code = receipt._sign_with_control_unit()
        self.assertEqual(receipt.control_code, code)
        self.assertTrue(code)

    def test_missing_control_unit_serial_is_refused(self):
        """Utan tillverkningsnummer nekas signeringen."""
        receipt = self._receipt()
        data = receipt._receipt_data()
        data['control_unit_serial'] = False
        with self.assertRaises(UserError):
            receipt._send_receipt_data(data)

    def test_silent_unit_is_refused(self):
        """En kontrollenhet som inte svarar nekar kvittot."""
        receipt = self._receipt()

        class SilentReceipt(receipt.__class__):
            """Same model, but the unit never answers."""

            def _blackbox_transport(self, receipt_dict):
                return False

        silent = receipt.with_env(self.env)
        silent.__class__ = SilentReceipt
        with self.assertRaises(UserError):
            silent._send_receipt_data(silent._receipt_data())


    # ------------------------------------------------------------------
    # 9.4 — a session cannot open without a control unit
    # ------------------------------------------------------------------
    def test_session_refused_without_control_unit(self):
        """Sessionsstart nekas när kontrollenhet saknas."""
        config = self.env['pos.config'].create({
            'name': 'Utan kontrollenhet',
            'sales_street': 'Storgatan 1',
            'sales_city': 'Stockholm',
        })
        config.registration_unit_id.write({'control_unit_serial': False})
        with self.assertRaises(UserError):
            self.env['pos.session'].create({'config_id': config.id})

    def test_session_allowed_with_control_unit(self):
        """Sessionsstart tillåts när kontrollenheten är konfigurerad."""
        session = self.env['pos.session'].create({'config_id': self.config.id})
        self.assertTrue(session, "Sessionen kunde inte öppnas")
