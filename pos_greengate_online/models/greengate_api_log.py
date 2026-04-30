import logging
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from odoo import fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

GREENGATE_NS = "http://www.retailinnovation.se/xccsp"

GREENGATE_HEADERS = {
    "Accept-Charset": "iso-8859-1",
    "Content-Type": "text/xml; charset=iso-8859-1",
    "Accept": "text/xml",
    "User-Agent": "MySuperPos/1.0",
}

DEFAULT_RETRY = Retry(
    total=3,
    backoff_factor=0.5,          # 0.5s, 1s, 2s
    status_forcelist={429, 500, 502, 503, 504},
    allowed_methods={"POST"},
    raise_on_status=False,
)

def _build_http_session() -> requests.Session:
    """Return a requests.Session pre-configured with retry + timeout adapter."""
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=DEFAULT_RETRY)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def _format_amount(amount: float) -> str:
    return f"{amount:.2f}".replace(".", ",") # return formatted decimal string

def _find_tag(element, tag_name):
    for child in element.iter():
        if child.tag.endswith(f"}}{tag_name}") or child.tag == tag_name:
            return child
    return None

def _get_text(element, tag_name: str) -> str:
    found = _find_tag(element, tag_name)
    return found.text if found is not None else ""

def _pretty_xml(xml_string: str) -> str:
    try:
        root = ET.fromstring(xml_string)
        ET.indent(root, space="    ")
        return ET.tostring(root, encoding="unicode")
    except ET.ParseError:
        return xml_string


class GreenGateApiLog(models.Model):
    _name = 'greengate.api.log'
    _description = 'GreenGate API Attempt Log'
    _order = 'create_date desc'

    response_type = fields.Selection(
        selection=[
            ('RegisterReceiptResponse', 'Register Receipt'),
            ('StatusResponse', 'Status'),
            ('Fault', 'Fault/Error'),
        ],
        string="Response Type",
        readonly=True,
    )

    fault_code = fields.Char(readonly=True)
    fault_message = fields.Char(readonly=True)
    firmware = fields.Char(readonly=True)
    unit_id = fields.Char(readonly=True, string="UnitId")
    unit_main_status = fields.Char(readonly=True, string="UnitMainStatus")
    unit_storage_status = fields.Char(readonly=True, string="UnitStorageStatus")

    pos_order_id = fields.Many2one(
        "pos.order", string="POS Order", ondelete="set null", readonly=True
    )
    pos_config_id = fields.Many2one("pos.config", string="POS", readonly=True)

    receipt_type = fields.Selection(
        selection=[
            ("normal", "A normal sales or refund receipt."),
            ("kopia", "A copy of a normal receipt."),
            ("profo", "A pro forma receipt (table bill etc.)."),
            ("ovning", "Any receipt produced in training mode."),
        ],
        string="GreenGate Receipt Type",
        readonly=True,
    )

    greengate_receipt_id = fields.Integer(string="ReceiptId", readonly=True)
    greengate_serial_no = fields.Integer(string="SerialNo", readonly=True)
    greengate_is_new_session = fields.Integer(string="IsNewSession", readonly=True)

    url = fields.Char(string="Called URL", readonly=True)
    xml_payload = fields.Text(string="XML Payload", readonly=True)
    status_code = fields.Char(readonly=True)
    response = fields.Text(readonly=True)
    green_gate_signature = fields.Char(readonly=True)

    def _build_vat_list_element(self) -> ET.Element: # build vat list from order's tax lines
        self.ensure_one()
        vat_list_el = ET.Element("VatList")

        tax_lines = self.pos_order_id.lines.filtered(lambda l: l.tax_ids)
        seen_classes = set()

        for line in tax_lines:
            for tax in line.tax_ids:
                vat_class = self._resolve_vat_class(tax.amount)
                if vat_class in seen_classes:
                    continue
                seen_classes.add(vat_class)

                tax_amount = sum(
                    l.price_subtotal * (tax.amount / 100)
                    for l in self.pos_order_id.lines
                    if tax in l.tax_ids
                )

                vat_el = ET.SubElement(vat_list_el, "Vat")
                ET.SubElement(vat_el, "Class").text = str(vat_class)
                ET.SubElement(vat_el, "Percentage").text = _format_amount(tax.amount)
                ET.SubElement(vat_el, "Amount").text = _format_amount(tax_amount)

        if not len(vat_list_el):
            vat_el = ET.SubElement(vat_list_el, "Vat")
            ET.SubElement(vat_el, "Class").text = "1"
            ET.SubElement(vat_el, "Percentage").text = "25,00"
            ET.SubElement(vat_el, "Amount").text = _format_amount(
                self.pos_order_id.amount_tax
            )

        return vat_list_el

    def _resolve_vat_class(self, tax_amount: float) -> int:
        mapping = {25.0: 1, 12.0: 2, 6.0: 3, 0.0: 4}
        return mapping.get(float(tax_amount), 1)

    def _build_receipt_xml(self) -> bytes:
        """
        Construct the RegisterReceipt XML payload using ElementTree
        (no f-string injection risk) and return ISO-8859-1–encoded bytes.
        """
        self.ensure_one()
        cfg = self.pos_config_id
        order = self.pos_order_id

        dt_local = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        date_str = dt_local.strftime("%Y%m%d%H%M")
        print(cfg)
        print(cfg.company_id)
        print(cfg.company_id.company_registry)
        if not cfg.company_id.company_registry:
            raise ValidationError("Company registry not configured")
        org_no = cfg.company_id.company_registry.replace("-", "")

        root = ET.Element("request", xmlns=GREENGATE_NS)
        ET.SubElement(root, "type").text = "RegisterReceipt"
        data_el = ET.SubElement(root, "data")
        receipt_el = ET.SubElement(data_el, "Receipt")

        fields_map = [
            ("IsNewSession", "0"),
            ("SerialNo", str(self.greengate_serial_no)),
            ("PosId", cfg.greengate_pos_id_full),
            ("OrgNo", org_no),
            ("Date", date_str),
            ("ReceiptId", str(self.greengate_receipt_id)),
            ("ReceiptType", self.receipt_type),
            ("ReceiptTotal", _format_amount(order.amount_total)),
            ("NegativeTotal", "0,00"),
        ]
        for tag, value in fields_map:
            ET.SubElement(receipt_el, tag).text = value

        receipt_el.append(self._build_vat_list_element())

        xml_declaration = b'<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        body = ET.tostring(root, encoding="unicode")
        payload = xml_declaration + body.encode("iso-8859-1")
        return payload

    def _parse_register_receipt_response(self, root):
        res = _find_tag(root, "RegisterResult")
        if res is None:
            return
        self.write({
            "green_gate_signature": _get_text(res, "Code"),
            "unit_id": _get_text(res, "UnitId"),
            "unit_main_status": _get_text(res, "UnitMainStatus"),
            "unit_storage_status": _get_text(res, "UnitStorageStatus"),
        })

    def _parse_fault_response(self, root):
        fault = _find_tag(root, "FaultInfo")
        if fault is None:
            return
        self.write({
            "fault_code": _get_text(fault, "Code"),
            "fault_message": _get_text(fault, "Message"),
        })

    def _parse_status_response(self, root):
        status = _find_tag(root, "Status")
        if status is None:
            return
        self.write({
            "unit_id": _get_text(status, "Id"),
            "firmware": _get_text(status, "Firmware"),
            "unit_main_status": _get_text(status, "MainStatus"),
            "unit_storage_status": _get_text(status, "StorageStatus"),
        })

    def _apply_training_mode_signature(self):
        if (
                self.receipt_type == "ovning"
                and self.response_type == "RegisterReceiptResponse"
                and not self.green_gate_signature
        ):
            self.green_gate_signature = f"Test Mode: {self.pos_config_id.name}"

    def parse_and_save_response(self):
        self.ensure_one()
        if not self.response:
            return

        clean_xml = self.response.replace("\u201c", '"').replace("\u201d", '"')
        try:
            root = ET.fromstring(clean_xml)
        except ET.ParseError as e:
            _logger.error("GreenGate: failed to parse XML response: %s", e)
            return

        type_tag = _find_tag(root, "type")
        resp_type = type_tag.text if type_tag is not None else ""
        self.response_type = resp_type

        parsers = {
            "RegisterReceiptResponse": self._parse_register_receipt_response,
            "Fault": self._parse_fault_response,
            "StatusResponse": self._parse_status_response,
        }
        parser = parsers.get(resp_type)
        if parser:
            parser(root)

        self._apply_training_mode_signature()

    def _sync_order_fields(self):
        """Push signature and unit_id back to the POS order if not already set."""
        self.ensure_one()
        order = self.pos_order_id
        if (
                self.response_type == "RegisterReceiptResponse"
                and self.green_gate_signature
                and not order.green_gate_signature
        ):
            order.green_gate_signature = self.green_gate_signature

        if self.unit_id and not order.unit_id:
            order.unit_id = self.unit_id

    def _post_to_greengate(self, payload: bytes) -> None:
        """
        Send `payload` to GreenGate, store raw response + status code.
        Retries are handled by the session adapter (up to 3×, exponential backoff).
        Timeouts and connection errors are caught and stored without raising,
        so the log record is always saved.
        """
        self.ensure_one()
        session = _build_http_session()
        cfg = self.pos_config_id

        try:
            resp = session.post(
                self.url,
                data=payload,
                headers=GREENGATE_HEADERS,
                auth=(cfg.greengate_username, cfg.greengate_password),
                timeout=(5, 30),
            )
            self.status_code = str(resp.status_code)
            self.response = _pretty_xml(resp.text)

        except requests.exceptions.Timeout:
            self.status_code = "Timeout"
            self.response = "The connection timed out."
            _logger.error("GreenGate Timeout for order %s", self.pos_order_id.id)

        except requests.exceptions.RequestException as e:
            self.status_code = "Error"
            self.response = str(e)
            _logger.error("GreenGate connection error: %s", e)


    def greengate_register_receipt(self):
        """
        Build the XML, post it, parse the response, and sync back to the order.
        This is the only public method callers need.
        """
        self.ensure_one()
        payload = self._build_receipt_xml()
        self.xml_payload = _pretty_xml(payload.decode("iso-8859-1"))
        self._post_to_greengate(payload)
        self.parse_and_save_response()
        self._sync_order_fields()


