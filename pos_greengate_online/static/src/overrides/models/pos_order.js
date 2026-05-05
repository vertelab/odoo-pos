import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { formatDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { floatIsZero } from "@web/core/utils/numbers";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { lt } from "@point_of_sale/utils";
import { toRaw } from "@odoo/owl";

patch(PosOrder.prototype, {
    get taxTotals() {
        const currency = this.config.currency_id;
        const company = this.company;
        const orderLines = Array.isArray(this.lines) ? this.lines : [];
        const paymentLines = Array.isArray(this.payment_ids) ? this.payment_ids : [];

        const documentSign =
            orderLines.length === 0 ||
            !orderLines.every((line) => lt(line.qty, 0, { decimals: currency.decimal_places }))
                ? 1
                : -1;

        const baseLines = orderLines.map((line) =>
            accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues({
                    quantity: documentSign * line.qty,
                })
            )
        );
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, company);

        const cashRounding =
            !this.config.only_round_cash_method && this.config.cash_rounding
                ? this.config.rounding_method
                : null;

        const taxTotals = accountTaxHelpers.get_tax_totals_summary(baseLines, currency, company, {
            cash_rounding: cashRounding,
        });

        taxTotals.order_sign = documentSign;
        taxTotals.order_total =
            taxTotals.total_amount_currency - (taxTotals.cash_rounding_base_amount_currency || 0.0);

        let order_rounding = 0;
        let remaining = taxTotals.order_total;
        const validPayments = paymentLines.filter((p) => p.is_done() && !p.is_change);
        for (const [payment, isLast] of validPayments.map((p, i) => [
            p,
            i === validPayments.length - 1,
        ])) {
            const paymentAmount = documentSign * payment.get_amount();
            if (isLast && this.config.cash_rounding) {
                const roundedRemaining = this.getRoundedRemaining(
                    this.config.rounding_method,
                    remaining
                );
                if (!floatIsZero(paymentAmount - remaining, this.currency.decimal_places)) {
                    order_rounding = roundedRemaining - remaining;
                }
            }
            remaining -= paymentAmount;
        }

        taxTotals.order_rounding = order_rounding;
        taxTotals.order_remaining = remaining;

        const remainingWithRounding = remaining + order_rounding;
        taxTotals.order_has_zero_remaining = floatIsZero(
            remainingWithRounding,
            currency.decimal_places
        );

        return taxTotals;
    },
    getCustomerDisplayData() {
        const sortedLines = Array.isArray(this.lines) ? this.getSortedOrderlines() : [];
        const paymentLines = Array.isArray(this.payment_ids) ? this.payment_ids : [];

        return {
            lines: sortedLines.map((line) => ({
                ...line.getDisplayData(),
                isSelected: line.isSelected(),
                imageSrc: `/web/image/product.product/${line.product_id.id}/image_128`,
            })),
            finalized: this.finalized,
            amount: formatCurrency(this.get_total_with_tax() || 0, this.currency),
            paymentLines: paymentLines.map((payment) => ({
                name: payment.payment_method_id.name,
                amount: formatCurrency(payment.get_amount(), this.currency),
            })),
            change: this.get_change() && formatCurrency(this.get_change(), this.currency),
            generalNote: this.general_note || "",
            qrPaymentData: toRaw(this.get_selected_paymentline()?.qrPaymentData),
        };
    },
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

        result.useGreengate = true;
        result.greenGateSignature = this.green_gate_signature;
        result.posID = this.config.greengate_pos_id;
        result.unitID = this.unit_id;
        result.nbPrint = this.nb_print;
        result.firstPrintDate = this.first_print_date
            ? formatDateTime(deserializeDateTime(this.first_print_date))
            : false;
        return result;
    },
});
