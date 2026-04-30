import logging
import time

from odoo import fields, models, api

_logger = logging.getLogger(__name__)

BUSY_FAULT_CODES = {"5", "97"}
MAX_RETRIES_BUSY = 5
MAX_RETRIES_TIMEOUT = 2


class PosOrder(models.Model):
    _inherit = "pos.order"

    green_gate_signature = fields.Char(readonly=True)
    unit_id = fields.Char(readonly=True)
    first_print_date = fields.Datetime(string="First Print Date", readonly=True, copy=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ["green_gate_signature", "unit_id", "first_print_date"]
        return params

    greengate_receipt_id = fields.Integer(
        string="GreenGate ReceiptId",
        readonly=True,
        copy=False,
        help="Unbroken ascending number series for this POS (1, 2, 3, ...).",
    )

    greengate_log_ids = fields.One2many(
        "greengate.api.log",
        "pos_order_id",
        string="GreenGate API Log",
        readonly=True,
    )

    green_gate_api_log_count = fields.Integer(
        string="GreenGate Log Count",
        compute="_compute_green_gate_api_log_count",
    )


    def _compute_green_gate_api_log_count(self):
        counts = self.env["greengate.api.log"].read_group(
            domain=[("pos_order_id", "in", self.ids)],
            fields=["pos_order_id"],
            groupby=["pos_order_id"],
        )
        count_map = {row["pos_order_id"][0]: row["pos_order_id_count"] for row in counts}
        for order in self:
            order.green_gate_api_log_count = count_map.get(order.id, 0)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if self.state == "paid" and not self.green_gate_signature:
            self._greengate_register_receipt()
        return res

    @api.model
    def register_greengate_signature_from_ui(self, order_vals):
        """
        Create/Update a draft order and register it with GreenGate to get a signature.
        Called from the POS UI before final validation.
        """
        # Ensure we have a draft order first
        order_vals['state'] = 'draft'
        # We use sync_from_ui logic to create/update the order
        pos_order_id = self.sync_from_ui([order_vals])
        order = self.browse(pos_order_id['pos.order'][0]['id'])
        
        # Register with GreenGate
        order._greengate_register_receipt()
        
        if order.green_gate_signature:
            return {
                'green_gate_signature': order.green_gate_signature,
                'unit_id': order.unit_id,
            }
        return False

    def action_view_green_gate_api_log(self):
        self.ensure_one()
        return {
            "name": "GreenGate API Logs",
            "type": "ir.actions.act_window",
            "res_model": "greengate.api.log",
            "view_mode": "list,form",
            "context": {"search_default_pos_order_id": self.id},
            "domain": [("pos_order_id", "=", self.id)],
        }

    def _get_next_greengate_receipt_id(self):
        """
        Allocate a ReceiptId for this order, if not already set.
        SELECT FOR UPDATE locks the config row to prevent race conditions
        between concurrent cashier sessions.
        """
        self.ensure_one()
        if self.greengate_receipt_id:
            return self.greengate_receipt_id

        self.env.cr.execute(
            "SELECT greengate_receipt_id FROM pos_config WHERE id = %s FOR UPDATE",
            (self.config_id.id,),
        )
        next_id = self.env.cr.fetchone()[0]
        self.env.cr.execute(
            "UPDATE pos_config SET greengate_receipt_id = %s WHERE id = %s",
            (next_id + 1, self.config_id.id),
        )
        self.config_id.invalidate_recordset(["greengate_receipt_id"])
        self.greengate_receipt_id = next_id
        return next_id

    def _get_next_greengate_serial_no(self):
        """
        Allocate the next SerialNo. Each retry gets a fresh one per GreenGate spec.
        SELECT FOR UPDATE prevents concurrent allocation.
        """
        self.ensure_one()
        self.env.cr.execute(
            "SELECT greengate_serial_no FROM pos_config WHERE id = %s FOR UPDATE",
            (self.config_id.id,),
        )
        current = self.env.cr.fetchone()[0]
        self.env.cr.execute(
            "UPDATE pos_config SET greengate_serial_no = %s WHERE id = %s",
            (current + 1, self.config_id.id),
        )
        self.config_id.invalidate_recordset(["greengate_serial_no"])
        return current

    def _should_attempt_be_new_session(self, attempt: int) -> int:
        return 1 if attempt == 0 and not self.greengate_log_ids else 0

    def _create_attempt_log(self, *, attempt, greengate_receipt_id, greengate_serial_no):
        cfg = self.config_id
        return self.env["greengate.api.log"].create({
            "pos_order_id": self.id,
            "pos_config_id": cfg.id,
            "receipt_type": cfg._get_greengate_receipt_type(),
            "url": cfg._get_greengate_api_url(),
            "greengate_is_new_session": self._should_attempt_be_new_session(attempt),
            "greengate_receipt_id": greengate_receipt_id,
            "greengate_serial_no": greengate_serial_no,
        })


    def _greengate_register_receipt(self):
        """
        Register this order with GreenGate, following §8.6 retry rules:
        - Already signed → skip.
        - Timeout → retry up to 2 times.
        - UNIT_BUSY (5) / SERVER_BUSY (97) → wait 1s, retry up to 5 times.
        - Each retry gets a fresh SerialNo; ReceiptId stays the same.
        """
        self.ensure_one()

        if not self.config_id.use_greengate:
            return

        if self.green_gate_signature:
            _logger.info("Order %s already has a GreenGate signature, skipping.", self.id)
            return

        greengate_receipt_id = self._get_next_greengate_receipt_id()
        timeout_attempts = 0
        busy_attempts = 0
        attempt = 0

        while True:
            greengate_serial_no = self._get_next_greengate_serial_no()
            log = self._create_attempt_log(
                attempt=attempt,
                greengate_receipt_id=greengate_receipt_id,
                greengate_serial_no=greengate_serial_no,
            )
            log.greengate_register_receipt()

            # Success
            if log.status_code == "200" and log.response_type != "Fault":
                break

            # UNIT_BUSY / SERVER_BUSY
            if log.status_code == "200" and log.fault_code in BUSY_FAULT_CODES:
                if busy_attempts < MAX_RETRIES_BUSY:
                    busy_attempts += 1
                    attempt += 1
                    time.sleep(1)
                    continue
                _logger.error("GreenGate: order %s hit BUSY limit.", self.id)
                break

            # Timeout
            if log.status_code == "Timeout":
                if timeout_attempts < MAX_RETRIES_TIMEOUT:
                    timeout_attempts += 1
                    attempt += 1
                    continue
                _logger.error("GreenGate: order %s hit Timeout limit.", self.id)
                break

            # Non-retryable
            _logger.error(
                "GreenGate: order %s non-retryable error — status %s, fault %s.",
                self.id, log.status_code, log.fault_code,
            )
            break

    def action_greengate_register_receipt(self):
        self.ensure_one()
        self._greengate_register_receipt()