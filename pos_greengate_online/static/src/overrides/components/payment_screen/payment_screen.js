import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (this.pos.config.use_greengate && !this.currentOrder.green_gate_signature) {
            const success = await this._getGreenGateSignature();
            if (!success) {
                return;
            }
        }
        await super.validateOrder(...arguments);
    },

    async _getGreenGateSignature() {
        try {
            this.ui.block();
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
                    title: _t("GreenGate Error"),
                    body: _t("Failed to get signature from GreenGate. Please try again."),
                });
                return false;
            }
        } catch (error) {
            console.error("GreenGate Error:", error);
            this.dialog.add(AlertDialog, {
                title: _t("GreenGate Error"),
                body: _t("An error occurred while communicating with GreenGate."),
            });
            return false;
        } finally {
            this.ui.unblock();
        }
    },
});
