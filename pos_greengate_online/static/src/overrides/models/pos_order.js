import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";

patch(PosOrder.prototype, {
    serialize() {
        const res = super.serialize(...arguments);
        res.green_gate_signature = this.green_gate_signature || false;
        res.unit_id = this.unit_id || false;
        res.first_print_date = this.first_print_date || false;
        return res;
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (!this.config.use_greengate) {
            return result;
        }
        
        result.useGreengate = true
        result.greenGateSignature = this.green_gate_signature
        result.posID = this.config.greengate_pos_id
        result.unitID = this.unit_id
        result.nbPrint = this.nb_print;
        result.firstPrintDate = this.first_print_date ? formatDateTime(deserializeDateTime(this.first_print_date)) : false;
        return result;
    },
});


