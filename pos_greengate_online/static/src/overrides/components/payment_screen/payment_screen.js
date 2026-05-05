import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useState } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.greenGateUi = useState({
            isSigning: false,
        });
    },

    async validateOrder(isForceValidate) {
        if (this.greenGateUi.isSigning) {
            return;
        }

        if (this.pos.config.use_greengate && !this.currentOrder.green_gate_signature) {
            const success = await this._getGreenGateSignature();
            if (!success) {
                return;
            }
        }
        await super.validateOrder(...arguments);
    },

    async _getGreenGateSignature() {
        if (this.greenGateUi.isSigning) {
            return false;
        }

        try {
            this.greenGateUi.isSigning = true;
            this.ui.block();
            this.notification.add(_t("Requesting GreenGate signature before validation..."), {
                title: _t("GreenGate"),
            });
            const result = await this.pos.data.call("pos.order", "register_greengate_signature_from_ui", [
                this.currentOrder.serialize({ orm: true }),
            ]);
            if (result && result.green_gate_signature) {
                this.currentOrder.update({
                    green_gate_signature: result.green_gate_signature,
                    unit_id: result.unit_id,
                });
                return true;
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Validation Blocked"),
                    body: _t(
                        "GreenGate did not return a signature, so this order cannot be validated yet. Please try again."
                    ),
                });
                return false;
            }
        } catch (error) {
            console.error("GreenGate Error:", error);
            this.dialog.add(AlertDialog, {
                title: _t("Validation Blocked"),
                body: _t(
                    "The GreenGate signature request failed, so this order was not validated. Check the connection and try again."
                ),
            });
            return false;
        } finally {
            this.greenGateUi.isSigning = false;
            this.ui.unblock();
        }
    },
});
