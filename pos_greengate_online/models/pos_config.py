from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    use_greengate = fields.Boolean(
        string="Use GreenGate Integration"
    )

    greengate_mode = fields.Selection(
        string="GreenGate Mode",
        selection=[
            ('test', 'Test (GreenGate Online test)'),
            ('prod', 'Production'),
        ],
        default='test',
        required=True,
        help="Switch between test and production GreenGate endpoints.",
    )
     
    #greengate_url = fields.Char(
    #    string="GreenGate Url"
    #)

    #greengate_test_url = fields.Char(
    #    string="GreenGate Test Url"
    #)

    greengate_username = fields.Char(
        string="GreenGate Username",
    )
    
    greengate_password = fields.Char(
        string="GreenGate Password",
    )

    greengate_serial_no = fields.Integer(
        string="Global SerialNo counter",
        default=1,
        help="Increments for each RegisterReceipt XML message sent (not per receipt).",
    )
    
    greengate_receipt_id = fields.Integer(
        string="Global ReceiptNo counter",
        default=1,
        help="Increments for first time an pos order is sent to greengate (not per attempt).",
    )

    greengate_pos_id = fields.Char(
        string="POS ID for GreenGate",
        size=6,
        help=(
            "POS ID for GreenGate integration (1–6 alphanumeric characters). "
            "Sent as the first part of <PosId><OrgNo> when syncing to GreenGate Online."
        ),
    )
 
    greengate_pos_id_full = fields.Char(
        string="Full POS ID (PosId + OrgNo)",
        compute="_compute_greengate_pos_id_full",
        store=True,
        help="POS ID concatenated with company organisation number (10 digits, no dash).",
    )

    @api.depends("greengate_pos_id", "company_id.company_registry")
    def _compute_greengate_pos_id_full(self):
        for rec in self:
            pos_id = (rec.greengate_pos_id or "").strip()
            org_no_raw = (rec.company_id.company_registry or "").strip()

            # Remove dashes and keep only digits
            org_no_digits = "".join(c for c in org_no_raw if c.isdigit())

            if pos_id and len(org_no_digits) == 10:
                rec.greengate_pos_id_full = pos_id + org_no_digits
            else:
                rec.greengate_pos_id_full = False

    def _get_greengate_api_url(self):
        self.ensure_one()
        return (
            "https://greengateonline.origum.se/xccsp"
            if self.greengate_mode == "prod"
            else "https://greengateonlinetest.origum.se/xccsp"
        )

    def _get_greengate_receipt_type(self):
        self.ensure_one()
        return "normal" if self.greengate_mode == "prod" else "ovning"