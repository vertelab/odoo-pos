import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PosStore.prototype, {
    async printReceipt(options = {}) {
        const order = options.order || this.get_order();
        const isFirstPrint = order.nb_print === 0;
        const result = await super.printReceipt(...arguments);
        
        if (result && isFirstPrint && !options.printBillActionTriggered) {
            const firstPrintDate = serializeDateTime(luxon.DateTime.now());
            order.update({ first_print_date: firstPrintDate });
            if (typeof order.id === "number") {
                await this.data.write("pos.order", [order.id], { first_print_date: firstPrintDate });
            }
        }
        return result;
    },
});
