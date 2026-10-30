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
"""Journal memory (journalminne).

Append-only log of *all* cash register activity, per 4 kap. 10 § SKVFS 2021:17
and 42 kap. 2 § SFL. Not a filter over ``pos.order``: events such as
``OppnaKassaladaVidNollforsaljning`` and ``StallaOmKlockan`` have no
counterpart in ``pos.order``, and ``pos.order`` can be deleted.

Immutability is enforced in three layers:

1. ORM — ``write`` and ``unlink`` raise ``UserError``.
2. Database — PostgreSQL rules deny UPDATE and DELETE.
3. Integrity — a SHA-256 hash chain over ``previous_hash`` and the entry's
   own fields makes tampering detectable even with database access.
"""
import hashlib
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Event types verified against Skatteverket's XSD
#: ``Utredningsstod-ElementAvSammansattTyp-2021-12-08-COMPONENT.xsd``
#: (retrieved 2026-10-28). All are members of ``HandelseTYPE`` and therefore
#: valid in ``Handelse`` under ``RegistreringLISTA``.
EVENT_TYPES = [
    ('RegistreraArtikel', 'Article registered'),
    ('AndraRegistreradArtikel', 'Article changed before completion'),
    ('RaderaRegistreradArtikel', 'Article deleted before completion'),
    ('ParkeraRegistreradArtikel', 'Article parked'),
    ('OppnaParkering', 'Parking resumed'),
    ('RaderaParkeradArtikel', 'Parked article deleted'),
    ('AndraParkeradArtikel', 'Parked article changed'),
    ('FlyttaParkeradArtikel', 'Parked article moved'),
    ('StangaParkering', 'Parking closed'),
    ('OppnaKassaladaVidNollforsaljning', 'Cash drawer opened without sale'),
    ('AnvandaClear', 'Clear function used'),
    ('StallaPrisforfragan', 'Price inquiry'),
    ('ForandraVaxelkassa', 'Cash float changed'),
    ('Kassakvitto', 'Cash receipt issued'),
    ('Returkvitto', 'Return receipt issued'),
    ('KopiaAvKassakvitto', 'Receipt copy issued'),
    ('ProFormaKvitto', 'Pro forma receipt issued'),
    ('Ovningskvitto', 'Training receipt issued'),
    ('XDagrapport', 'X report issued'),
    ('ZDagrapport', 'Z report issued'),
    ('OvrigRapport', 'Other report issued'),
    ('StartAvKassaregister', 'Cash register started'),
    ('StoppAvKassaregister', 'Cash register stopped'),
    ('OmstartAvKassaregister', 'Cash register restarted'),
    ('InloggningIKassaregister', 'Logged in'),
    ('UtloggningUrKassaregister', 'Logged out'),
    ('StallaOmKlockan', 'Clock adjusted'),
    ('StallaOmTillOvningslage', 'Training mode activated'),
    ('StallaOmTillNormallage', 'Normal mode activated'),
    ('StatuskodFranKontrollprogrammet', 'Status code from control program'),
    ('VerifieringAvKvittodataMellanKontrollprogramOchKontrollserver',
     'Receipt data verification'),
]


class PosJournalEntry(models.Model):
    """One immutable journal memory entry."""

    _name = 'pos.journal.entry'
    _description = 'Cash Register Journal Memory Entry'
    _order = 'unit_id, sequence'
    _rec_name = 'display_name'

    unit_id = fields.Many2one(
        comodel_name='pos.registration.unit',
        string='Registration Unit',
        required=True,
        ondelete='restrict',
        index=True,
    )
    sequence = fields.Integer(
        string='Sequence Number',
        required=True,
        readonly=True,
        index=True,
        help="Unbroken ascending series per registration unit "
             "(4 kap. 2 § SKVFS 2021:17).",
    )
    event_type = fields.Selection(
        selection=EVENT_TYPES,
        string='Event Type',
        required=True,
        readonly=True,
        index=True,
    )
    occurred_at = fields.Datetime(
        string='Occurred At',
        required=True,
        readonly=True,
        default=fields.Datetime.now,
        help="Stored in UTC; rendered in local Swedish time on receipts and "
             "in the XML export.",
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        readonly=True,
        default=lambda self: self.env.user,
    )
    session_id = fields.Many2one(
        comodel_name='pos.session',
        string='POS Session',
        readonly=True,
        ondelete='set null',
        index=True,
    )
    order_id = fields.Many2one(
        comodel_name='pos.order',
        string='POS Order',
        readonly=True,
        ondelete='set null',
        index=True,
    )
    amount = fields.Monetary(
        string='Amount',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='unit_id.company_id.currency_id',
        store=True,
        readonly=True,
    )
    payload = fields.Json(
        string='Payload',
        readonly=True,
        help="Event specific data as JSON.",
    )
    previous_hash = fields.Char(
        string='Previous Hash',
        readonly=True,
        size=64,
        help="Hash of the preceding entry on the same unit. Empty for the "
             "first entry.",
    )
    entry_hash = fields.Char(
        string='Entry Hash',
        readonly=True,
        size=64,
        index=True,
        help="SHA-256 over previous_hash and this entry's fields.",
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )

    _sql_constraints = [
        ('unit_sequence_uniq', 'unique(unit_id, sequence)',
         'The sequence number must be unique per registration unit.'),
    ]

    @api.depends('unit_id', 'sequence', 'event_type')
    def _compute_display_name(self):
        labels = dict(EVENT_TYPES)
        for entry in self:
            entry.display_name = '%s / %s — %s' % (
                entry.unit_id.name or '',
                entry.sequence,
                labels.get(entry.event_type, entry.event_type or ''),
            )

    def init(self):
        """Make the table append-only at the database level.

        Runs on every module update, not just on install: ``post_init_hook``
        only fires on ``--init``, so an upgraded database would otherwise
        keep UPDATE/DELETE privileges. Revoking from the current role by
        name is required because a table owner keeps its own privileges.
        """
        self._cr.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'pos_journal_entry'
                ) THEN
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

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------
    @api.model
    def _hash_vals(self, vals):
        """Compute the entry hash from a values dict.

        Single source of truth for the hash: both ``_log_event`` (before the
        row exists) and ``_compute_entry_hash`` (to verify a stored row) go
        through here, so the two can never drift apart.

        Only fields that are part of the legal record are included, and they
        are serialised with sorted keys so the hash is reproducible.
        """
        data = {
            'unit': vals.get('unit_id') or 0,
            'sequence': vals.get('sequence') or 0,
            'event_type': vals.get('event_type') or '',
            'occurred_at': fields.Datetime.to_string(
                vals.get('occurred_at')) if vals.get('occurred_at') else '',
            'user': vals.get('user_id') or 0,
            'session': vals.get('session_id') or 0,
            'order': vals.get('order_id') or 0,
            'amount': '%.2f' % (vals.get('amount') or 0.0),
            # Json fields normalise an empty dict to False on read,
            # so both sides of the hash must use the same normalisation.
            'payload': vals.get('payload') or False,
            'previous_hash': vals.get('previous_hash') or '',
        }
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, ensure_ascii=False,
                       separators=(',', ':')).encode('utf-8')
        ).hexdigest()

    def _compute_entry_hash(self):
        """Recompute the hash over the stored row, for chain verification."""
        self.ensure_one()
        return self._hash_vals({
            'unit_id': self.unit_id.id,
            'sequence': self.sequence,
            'event_type': self.event_type,
            'occurred_at': self.occurred_at,
            'user_id': self.user_id.id,
            'session_id': self.session_id.id,
            'order_id': self.order_id.id,
            'amount': self.amount,
            'payload': self.payload,
            'previous_hash': self.previous_hash,
        })

    # ------------------------------------------------------------------
    # Logging API
    # ------------------------------------------------------------------
    @api.model
    def _log_event(self, event_type, payload=None, session=None, order=None,
                   unit=None, amount=None, user=None):
        """Append one event to the journal memory.

        Takes the next sequence number from the unit's no-gap sequence,
        computes the hash chain link and writes the row.

        :param str event_type: one of ``EVENT_TYPES``
        :param dict payload: event specific data, stored as JSON
        :param pos.session session: related POS session
        :param pos.order order: related POS order
        :param pos.registration.unit unit: registration unit; derived from
            the session's config when omitted
        :param float amount: monetary amount for cash-related events
        :param res.users user: acting user, defaults to ``env.user``
        :return: the created ``pos.journal.entry``
        """
        if event_type not in dict(EVENT_TYPES):
            raise UserError(
                "Unknown journal event type: %s" % event_type
            )

        if not unit:
            if session and session.config_id:
                unit = self.env['pos.registration.unit'].search(
                    [('config_id', '=', session.config_id.id)], limit=1)
            elif order and order.session_id and order.session_id.config_id:
                unit = self.env['pos.registration.unit'].search(
                    [('config_id', '=', order.session_id.config_id.id)], limit=1)
        if not unit:
            raise UserError(_(
                "Cannot write to the journal memory: no registration unit "
                "found. Configure a cash register designation for this POS "
                "configuration first."
            ))

        # next_by_id() returns a zero-padded string ('00000001'); the
        # field is an integer, so normalise before hashing.
        sequence = int(unit.sequence_id.next_by_id())
        previous = self.search(
            [('unit_id', '=', unit.id)], order='sequence desc', limit=1)

        # Bind the timestamp once: the hash is computed from vals before
        # create(), so a second now() call would hash a different instant
        # than the one stored and every entry would fail verification.
        occurred_at = fields.Datetime.now()
        vals = {
            'unit_id': unit.id,
            'sequence': sequence,
            'event_type': event_type,
            'occurred_at': occurred_at,
            'user_id': (user or self.env.user).id,
            'session_id': session.id if session else False,
            'order_id': order.id if order else False,
            'amount': amount or 0.0,
            'payload': payload or False,
            'previous_hash': previous.entry_hash or '',
        }
        # The hash must be computed before create(): journal entries are
        # immutable, so there is no second write to attach it afterwards.
        vals['entry_hash'] = self._hash_vals(vals)
        return self.create(vals)

    # ------------------------------------------------------------------
    # Chain verification
    # ------------------------------------------------------------------
    def _check_chain(self):
        """Verify the hash chain for the units in ``self``.

        :return: list of dicts describing broken links; empty when intact
        """
        broken = []
        units = self.mapped('unit_id')
        for unit in units:
            broken += unit._check_chain_unit()
        return broken

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------
    def write(self, vals):
        """Journal entries are immutable — no field may be changed."""
        raise UserError(_(
            "Journal memory entries cannot be modified. The journal memory is "
            "append-only per 4 kap. 10 § SKVFS 2021:17."
        ))

    def unlink(self):
        """Journal entries are immutable — they may not be deleted."""
        raise UserError(_(
            "Journal memory entries cannot be deleted. They must be retained "
            "for seven years per BFL 7 kap."
        ))
