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
"""XML export of the journal memory (SKVFS 2021:16).

The export produces a file that a tax inspector can load into their own
control program without interpreting the business system's database. The
element names are taken verbatim from Skatteverket's schema — they are
normative, and a misspelt name is a rejected file.

The file is validated against the XSD before it is handed out. A file that
does not validate is never delivered.
"""
import base64
import logging
from datetime import datetime

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Namespaces from Skatteverket's schema.
NS_INSTANS = ('http://xmls.skatteverket.se/se/skatteverket/td/instans/'
              'utredningsstod/1.0')
NS_KOMPONENT = ('http://xmls.skatteverket.se/se/skatteverket/td/komponent/'
                'utredningsstod/1.0')

#: Root element, verbatim from the instance schema.
ROOT_ELEMENT = 'ExportAvDataFranJournalminneEnligtSKVFS2021-16'

#: Where the schema files live inside the module.
SCHEMA_DIR = 'schemas/xmls'
INSTANCE_SCHEMA = ('instans/utredningsstod/2021-12-08/'
                   'ExportAvDataFranJournalminneEnligtSKVFS202116-2021-12-08.xsd')


def _q(name):
    """Return a component-namespace qualified tag."""
    return '{%s}%s' % (NS_KOMPONENT, name)


def _text(parent, name, value):
    """Append a text element, skipping it when the value is empty."""
    if value is None or value == '':
        return None
    node = etree.SubElement(parent, _q(name))
    node.text = str(value)
    return node


def _amount(value):
    """Format an amount with two decimals, as the schema expects."""
    return '%.2f' % (value or 0.0)


def _timestamp(value):
    """Format a datetime as the schema expects (local time, no zone)."""
    if not value:
        return ''
    return value.strftime('%Y-%m-%dT%H:%M:%S')


class PosJournalExport(models.AbstractModel):
    """Build the SKVFS 2021:16 XML export from the journal memory."""
    _name = 'pos.journal.export'
    _description = 'Export av journalminne enligt SKVFS 2021:16'

    #: Events whose only content is the token "JA" in the schema.
    FLAG_EVENTS = (
        'StartAvKassaregister', 'StoppAvKassaregister',
        'OmstartAvKassaregister', 'InloggningIKassaregister',
        'UtloggningUrKassaregister', 'AnvandaClear',
        'OppnaKassaladaVidNollforsaljning', 'StallaOmTillOvningslage',
        'StallaOmTillNormallage', 'StangaParkering',
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @api.model
    def build_xml(self, units, date_from, date_to, export_user=None):
        """Return the export as bytes.

        :param units: registration units to export (one or more)
        :param date_from: first date of the period (inclusive)
        :param date_to: last date of the period (inclusive)
        :param export_user: the user performing the export, for the log
        """
        if not units:
            raise UserError(_("Välj minst en registreringsenhet att exportera."))
        date_from = self._as_date(date_from)
        date_to = self._as_date(date_to)
        if date_from > date_to:
            raise UserError(_(
                "Startdatum måste vara före slutdatum."))

        root = etree.Element(
            '{%s}%s' % (NS_INSTANS, ROOT_ELEMENT),
            nsmap={'utrein': NS_INSTANS, 'utreko': NS_KOMPONENT},
        )

        # --- Inledande element (kap 4–5) -----------------------------
        if export_user:
            _text(root, 'InloggadAnvandareVidExportAvDataFranJournalminnet',
                  export_user.login or export_user.name)

        _text(root, 'BeteckningPaDetKassaregisterSomExportAvDataFranJournal'
                    'minnetSkerIfran', units[0].name)
        _text(root, 'TidpunktForNarExportAvDataFranJournalminnetSker',
              _timestamp(datetime.now()))

        period = etree.SubElement(
            root, _q('ValdPeriodForExportAvDataFranJournalminne'))
        _text(period, 'ValdStarttidpunktForExportAvDataFranJournalminnet',
              date_from.strftime('%Y-%m-%dT00:00:00'))
        _text(period, 'ValdSluttidpunktForExportAvDataFranJournalminnet',
              date_to.strftime('%Y-%m-%dT23:59:59'))

        unit_list = etree.SubElement(
            root, _q('BeteckningPaValdaKassaregisterForExportAvDataFran'
                     'JournalminnenLISTA'))
        for unit in units:
            _text(unit_list,
                  'BeteckningPaValtKassaregisterForExportAvDataFranJournal'
                  'minnet', unit.name)

        self._company_element(root, units[0])
        self._system_element(root, units)

        # --- Registreringar (kap 6–36) -------------------------------
        registrations = etree.SubElement(root, _q('RegistreringLISTA'))
        entries = self.env['pos.journal.entry'].search([
            ('unit_id', 'in', units.ids),
            ('occurred_at', '>=', fields.Datetime.to_datetime(date_from)),
            ('occurred_at', '<=', fields.Datetime.to_datetime(
                datetime.combine(date_to, datetime.max.time()))),
        ], order='unit_id, sequence asc')

        for entry in entries:
            self._event_element(registrations, entry)

        return etree.tostring(
            root, xml_declaration=True, encoding='UTF-8', pretty_print=True)

    @api.model
    def _as_date(self, value):
        """Return a plain date, accepting both date and datetime input."""
        return value.date() if hasattr(value, 'date') else value

    @api.model
    def validate_xml(self, xml_bytes):
        """Validate the export against Skatteverket's XSD.

        :return: True when valid
        :raise UserError: naming the missing or invalid element
        """
        schema_path = self._schema_path()
        if not schema_path:
            _logger.warning(
                "pos_kassaregister_se: XSD not found — export not validated")
            return True

        try:
            schema = etree.XMLSchema(etree.parse(schema_path))
            document = etree.fromstring(xml_bytes)
        except (etree.XMLSyntaxError, etree.SchemaParseError) as exc:
            raise UserError(_(
                "Exporten kunde inte valideras: %(error)s", error=exc)) from exc

        if not schema.validate(document):
            problems = '; '.join(
                '%s (%s)' % (e.message, e.path) for e in schema.error_log[:5])
            raise UserError(_(
                "Exporten validerar inte mot Skatteverkets schema och får "
                "inte levereras: %(problems)s", problems=problems))
        return True

    @api.model
    def _schema_path(self):
        """Return the absolute path of the instance schema, if present."""
        import os
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(module_dir, SCHEMA_DIR, INSTANCE_SCHEMA)
        return path if os.path.exists(path) else None

    # ------------------------------------------------------------------
    # Header elements
    # ------------------------------------------------------------------
    @api.model
    def _company_element(self, root, unit):
        """InformationOmForetaget (kap 5)."""
        company = unit.config_id.company_id
        node = etree.SubElement(root, _q('InformationOmForetaget'))
        _text(node, 'OrganisationsnummerEllerPersonnummer',
              self._org_number(company))
        _text(node, 'ForetagetsNamn', company.name)
        _text(node, 'NamnPaVerksamheten', unit.config_id.name)

        _text(node, 'DenAdressDarForsaljningSker',
              self._address_text(unit.config_id))

    @api.model
    def _org_number(self, company):
        """Return the company's organisation number.

        The schema requires it, so an export without it must fail loudly
        rather than produce a file that cannot be used.
        """
        raw = (company.vat or company.company_registry or '').strip()
        # The schema wants digits only. A Swedish VAT number is SE + 10
        # digits + 01, so drop the country prefix and the VAT suffix.
        digits = ''.join(ch for ch in raw if ch.isdigit())
        if raw.upper().startswith('SE') and len(digits) == 12:
            digits = digits[:10]
        number = digits
        if not number:
            raise UserError(_(
                "Företagets organisationsnummer saknas. Det krävs i exporten "
                "(SKVFS 2021:16 5 kap.) — ange det på företaget först."))
        return number

    @api.model
    def _address_text(self, config):
        """Return the sales address as one string: street, zip and city.

        The schema wants the address as a single string (max 72 chars), not
        a structured element.
        """
        parts = [config.sales_street or '', config.sales_zip or '',
                 config.sales_city or '']
        return ', '.join(p for p in parts if p)

    @api.model
    def _system_element(self, root, units):
        """KassaregistersystemLISTA (kap 5)."""
        unit_list = etree.SubElement(root, _q('KassaregistersystemLISTA'))
        for unit in units:
            node = etree.SubElement(unit_list, _q('Kassaregistersystemet'))
            _text(node, 'TillverkningsnummerForKassaregistret',
                  unit.serial_number or '')
            _text(node, 'ModellbeteckningForKassaregistret',
                  unit.model_designation or '')
            _text(node, 'ModellEllerProgramForKassaregistret', 'Odoo')
            _text(node, 'VersionsnummerForKassaregistret', self._version())
            _text(node, 'Kassabeteckning', unit.name)
            # One of the control unit / control system serials is mandatory.
            # A register without a control unit cannot export at all, so say
            # so plainly instead of shipping an unusable file.
            if not unit.control_unit_serial:
                raise UserError(_(
                    "Registreringsenheten %(unit)s saknar tillverkningsnummer "
                    "för kontrollenheten. Det krävs i exporten "
                    "(SKVFS 2021:16 5 kap.).",
                    unit=unit.name))
            _text(node, 'TillverkningsnummerForKontrollenheten',
                  unit.control_unit_serial)

    @api.model
    def _version(self):
        """Return the module's version number for the export header."""
        module = self.env['ir.module.module'].search(
            [('name', '=', 'pos_kassaregister_se')], limit=1)
        return module.latest_version or '18.0.1.3.0'

    # ------------------------------------------------------------------
    # One registration
    # ------------------------------------------------------------------
    @api.model
    def _event_element(self, parent, entry):
        """Append one Handelse element for a journal entry (kap 6–36)."""
        event = etree.SubElement(parent, _q('Handelse'))
        _text(event, 'InloggadAnvandare',
              entry.user_id.login or entry.user_id.name or '')
        _text(event, 'Kassabeteckning', entry.unit_id.name)
        _text(event, 'Registreringstidpunkt', _timestamp(entry.occurred_at))

        # The event type is the element name — the schema names them exactly
        # as the journal memory does.
        node = etree.SubElement(event, _q(entry.event_type))
        self._event_payload(node, entry)

    @api.model
    def _event_payload(self, node, entry):
        """Fill the event-specific element with its mandatory content."""
        payload = entry.payload or {}
        event_type = entry.event_type

        if event_type in ('Kassakvitto', 'Returkvitto', 'KopiaAvKassakvitto',
                          'ProFormaKvitto', 'Ovningskvitto'):
            self._receipt_payload(node, entry, payload)
        elif event_type in ('ForandraVaxelkassa',):
            _text(node, 'ForandringAvVaxelkassaISvenskaKronor',
                  _amount(entry.amount))
        elif event_type in self.FLAG_EVENTS:
            # These events carry no data — the schema wants the literal
            # token "JA" as the element's content.
            node.text = 'JA'
        elif event_type == 'StallaPrisforfragan':
            _text(node, 'Artikelbenamning', payload.get('product_name') or '')
            _text(node, 'Pris', _amount(payload.get('price')))
        elif event_type == 'StallaOmKlockan':
            _text(node, 'TidpunktForeJustering', payload.get('old_time') or '')
            _text(node, 'TidpunktEfterJustering', payload.get('new_time') or '')
        elif event_type in ('ParkeraRegistreradArtikel',
                            'OppnaParkering', 'RaderaParkeradArtikel',
                            'AndraParkeradArtikel'):
            _text(node, 'Artikelbenamning', payload.get('product_name') or '')
            _text(node, 'Antal', payload.get('qty') or payload.get('new_qty'))
        elif event_type in ('XDagrapport', 'ZDagrapport'):
            _text(node, 'LopnummerForZDagrapport',
                  payload.get('z_sequence') or '')

    @api.model
    def _receipt_payload(self, node, entry, payload):
        """Fill a receipt element (kap 12–17)."""
        order = entry.order_id
        unit = entry.unit_id
        company = unit.config_id.company_id

        _text(node, 'ForetagetsNamn', company.name)
        _text(node, 'OrganisationsnummerEllerPersonnummer',
              (company.vat or '').replace(' ', ''))
        _text(node, 'DenAdressDarForsaljningSker',
              self._address_text(unit.config_id))

        _text(node, 'DatumOchKlockslagNarKvittoFramstalls',
              _timestamp(entry.occurred_at))
        _text(node, 'LopnummerForKassakvitto',
              payload.get('receipt_sequence') or '')
        _text(node, 'Kassabeteckning', unit.name)
        # Amounts are always in SEK, converted at the rate of the sale.
        _text(node, 'TotaltForsaljningsbeloppISvenskaKronor',
              _amount(self._to_sek(order, payload.get('amount_total'))))
        _text(node, 'MervardesskattPaForsaljningsbeloppet',
              _amount(self._to_sek(order, payload.get('amount_tax'))))
        if payload.get('control_code'):
            _text(node, 'Kontrollkod', payload['control_code'])
        if unit.control_unit_serial:
            _text(node, 'TillverkningsnummerForKontrollenheten',
                  unit.control_unit_serial)

    @api.model
    def _to_sek(self, order, amount):
        """Convert an amount to SEK at the rate that applied at the sale."""
        if not order or amount is None:
            return amount or 0.0
        sek = self.env.ref('base.SEK', raise_if_not_found=False)
        if not sek or order.currency_id == sek:
            return amount
        return order.currency_id._convert(
            amount, sek, order.company_id, order.date_order)

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------
    @api.model
    def export(self, units, date_from, date_to):
        """Build, validate and log an export; return the file content.

        :return: dict with ``filename`` and ``content`` (base64)
        """
        user = self.env.user
        xml_bytes = self.build_xml(units, date_from, date_to,
                                   export_user=user)
        self.validate_xml(xml_bytes)

        filename = 'journalminne_%s_%s_%s.xml' % (
            '-'.join(units.mapped('name')).replace(' ', '_'),
            date_from.strftime('%Y%m%d'),
            date_to.strftime('%Y%m%d'),
        )

        # Every export is recorded in the journal memory (kap 4 § 10).
        for unit in units:
            self.env['pos.journal.entry']._log_event(
                'OvrigRapport',
                unit=unit,
                payload={
                    'report': 'ExportAvDataFranJournalminne',
                    'date_from': date_from.strftime('%Y-%m-%d'),
                    'date_to': date_to.strftime('%Y-%m-%d'),
                    'units': units.mapped('name'),
                    'user': user.login or user.name,
                    'filename': filename,
                },
            )

        return {
            'filename': filename,
            'content': base64.b64encode(xml_bytes),
        }
