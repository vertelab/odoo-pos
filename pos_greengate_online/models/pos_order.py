from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
from xml.etree import ElementTree as ET
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import fields
import logging
_logger = logging.getLogger(__name__)


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
        readonly=False,
    )
    
    fault_code = fields.Char(
        readonly=False,
    )
    
    fault_message = fields.Char(
        readonly=False,
    )
    
    firmware = fields.Char(
        readonly=False
    )
    
    unit_id = fields.Char(readonly=False, String="UnitId")
    
    unit_main_status = fields.Char(readonly=False, String="UnitMainStatus")
    
    unit_storage_status = fields.Char(readonly=False, String="UnitStorageStatus")

    pos_order_id = fields.Many2one(
        'pos.order',
        string="POS Order",
        ondelete='set null',
        readonly=False,
    )

    pos_config_id = fields.Many2one(
        'pos.config',
        string="POS",
        readonly=False,
    )

    receipt_type = fields.Selection(
        selection=[
            ('normal', 'A normal sales or refund receipt.'),
            ('kopia', 'A copy of a normal receipt.'),
            ('profo', 'A table bill or other receipt that counts as a pro forma receipt according to Skatteverkets regulations.'),
            ('ovning', 'Any receipt produced in training mode.'),
        ],
        string="GreenGate Receipt Type",
        readonly=False,
    )

    greengate_receipt_id = fields.Integer(
        string="ReceiptId",
        readonly=False,
    )
    greengate_serial_no = fields.Integer(
        string="SerialNo",
        readonly=False,
    )
    greengate_is_new_session = fields.Integer(
        string="IsNewSession",
        readonly=False,
    )

    url = fields.Char(
        string="Called URL",
        readonly=False,
    )
    
    xml_payload = fields.Char(
        string="Xml Payload",
        readonly=False,
    )
    
    status_code = fields.Char(
        readonly=False,
    )
    
    
    response = fields.Char(
        readonly=False,
    )
    
    green_gate_signature = fields.Char(
        readonly=False,
    )
    
    def _format_receipt_amount(self, amount):
        #Format: 1-11 digits, comma, 2 digits. E.g “10,00”, “-10,00” 
        #19.38 -> 19,38
        return f"{amount:.2f}".replace(".", ",")
        
    def parse_and_save_response(self):
        self.ensure_one()
        if not self.response:
            return

        clean_xml = self.response.replace('”', '"').replace('“', '"')

        try:
            root = ET.fromstring(clean_xml)
            
            def find_tag(element, tag_name):
                for child in element.iter():
                    if child.tag.endswith(f"}}{tag_name}") or child.tag == tag_name:
                        return child
                return None

            def get_text(element, tag_name):
                found = find_tag(element, tag_name)
                return found.text if found is not None else ""
                
            type_tag = find_tag(root, "type")
            resp_type = type_tag.text if type_tag is not None else ""
            self.response_type = resp_type

            if resp_type == 'RegisterReceiptResponse':
                res = find_tag(root, "RegisterResult")
                if res is not None:
                    self.write({
                        'green_gate_signature': get_text(res, "Code"),
                        'unit_id': get_text(res, "UnitId"),
                        'unit_main_status': get_text(res, "UnitMainStatus"),
                        'unit_storage_status': get_text(res, "UnitStorageStatus"),
                    })

            elif resp_type == 'Fault':
                fault = find_tag(root, "FaultInfo")
                if fault is not None:
                    self.write({
                        'fault_code': get_text(fault, "Code"),
                        'fault_message': get_text(fault, "Message"),
                    })

            elif resp_type == 'StatusResponse':
                status = find_tag(root, "Status")
                if status is not None:
                    self.write({
                        'unit_id': get_text(status, "Id"),
                        'firmware': get_text(status, "Firmware"),
                        'unit_main_status': get_text(status, "MainStatus"),
                        'unit_storage_status': get_text(status, "StorageStatus"),
                    })
                    
            if self.receipt_type == "ovning" and self.response_type == 'RegisterReceiptResponse' and not self.green_gate_signature:
                self.green_gate_signature = f"Test Mode: {self.pos_config_id.name}"
                
        except Exception as e:
            _logger.error(f"Failed to parse XML: {e}")
        
    def GreenGateRegisterReceipt(self):
        NS = "http://www.retailinnovation.se/xccsp"

        headers = {
            "Accept-Charset": "iso-8859-1",
            "Content-Type": "text/xml; charset=iso-8859-1",
            "Accept": "text/xml",
            "User-Agent": "MySuperPos/1.0",
        }
        VatList = [
            {"Class": 1, "Percentage": "25,00", "Amount": self.pos_order_id.amount_tax},
        ]
        
        dt_local = fields.datetime.now()
        date = f"{dt_local.year:04}{dt_local.month:02}{dt_local.day:02}{dt_local.hour:02}{dt_local.minute:02}"
        receipt_total = self._format_receipt_amount(self.pos_order_id.amount_total)
        amount_tax = self._format_receipt_amount(self.pos_order_id.amount_tax)
        xml_body = f'''<?xml version="1.0" encoding="ISO-8859-1"?>
        <request xmlns="{NS}">
          <type>RegisterReceipt</type>
          <data>
            <Receipt>
              <IsNewSession>0</IsNewSession>
              <SerialNo>{self.greengate_serial_no}</SerialNo>
              <PosId>{self.pos_config_id.greengate_pos_id_full}</PosId>
              <OrgNo>{self.pos_config_id.company_id.company_registry.replace("-","")}</OrgNo>
              <Date>{date}</Date>
              <ReceiptId>{self.greengate_receipt_id}</ReceiptId>
              <ReceiptType>{self.receipt_type}</ReceiptType>
              <ReceiptTotal>{receipt_total}</ReceiptTotal>
              <NegativeTotal>{"0,00"}</NegativeTotal>
              <VatList>
              <Vat>
                <Class>1</Class>                  
                <Percentage>25,00</Percentage>
                <Amount>{amount_tax}</Amount>
                </Vat>
              </VatList>
            </Receipt>
          </data>
        </request>'''.strip()
        self.xml_payload = xml_body
        body_bytes = xml_body.encode("iso-8859-1")
        resp = requests.post(
            self.url,
            data=body_bytes,
            headers=headers,
            auth=(self.pos_config_id.greengate_username, self.pos_config_id.greengate_password),
            timeout=30,
        )
        self.response = resp.text
        self.status_code = resp.status_code
        

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    #green_gate_signature = fields.Char()

    greengate_log_ids = fields.One2many(
        'greengate.api.log',
        'pos_order_id',
        string="GreenGate API Log",
        readonly=False,
    )
    
    green_gate_api_log_count = fields.Integer(
        string="GreenGate Log Count",
        compute='_compute_green_gate_api_log_count',
    )

    def _compute_green_gate_api_log_count(self):
        for order in self:
            order.green_gate_api_log_count = len(order.greengate_log_ids)
            
    def action_view_green_gate_api_log(self):
        self.ensure_one()

        return {
            'name': 'GreenGate API Logs',
            'type': 'ir.actions.act_window',
            'res_model': 'greengate.api.log',
            'view_mode': 'list,form',
            'context': {
                'search_default_pos_order_id': self.id,
            },
            'domain': [
                ('pos_order_id', '=', self.id),
            ],
        }
    
    greengate_receipt_id = fields.Integer(
        string="GreenGate ReceiptId",
        readonly=False,
        copy=False,
        help="Unbroken ascending number series for this POS (1, 2, 3, ...).",
    )
    
    def _get_next_greengate_receipt_id(self):
        #Should i lock it so no other adds before i can return value?
        if not self.greengate_receipt_id:
            self.greengate_receipt_id = self.config_id.greengate_receipt_id
            self.config_id.greengate_receipt_id += 1
        return self.greengate_receipt_id
        
    def _get_next_greengate_serial_no(self):
        #Should i lock it so no other adds before i can return value?
        current_serial_no = self.config_id.greengate_serial_no
        self.config_id.greengate_serial_no += 1
        return current_serial_no
        
    def greenGateRegisterReceipt(self):
        greengate_receipt_id = self._get_next_greengate_receipt_id()
        greengate_serial_no = self._get_next_greengate_serial_no()
        receipt_type = "normal" if self.config_id.greengate_mode == "prod" else "ovning"
        url = self.config_id.greengate_url if self.config_id.greengate_mode == "prod" else self.config_id.greengate_test_url
        session = self.env['greengate.api.log'].create({
        "pos_order_id":self.id,
        "pos_config_id":self.config_id.id,
        "receipt_type":receipt_type,
        "url":url,
        "greengate_is_new_session": 0 if self.greengate_log_ids else 1,
        "greengate_receipt_id":greengate_receipt_id,
        "greengate_serial_no":greengate_serial_no,
        })
        session.GreenGateRegisterReceipt()
        
        
