import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (!this.config.use_greengate) {
            console.log("Enter if case")
            return result;
        }
        
        const order = this;
        result.useGreengate = true
        result.greenGateSignature = order.green_gate_signature
        result.posID = order.config.greengate_pos_id
        result.unitID = order.unit_id
        return result;
    },
});


