odoo.define("pos_fcu.fcu", function (require) {
"use strict";

    var PosBaseWidget = require('point_of_sale.BaseWidget');
    //~ var gui = require('point_of_sale.gui');
    //~ var models = require('point_of_sale.models');
    var core = require('web.core');
    //~ var Model = require('web.DataModel');
    //~ var utils = require('web.utils');
    //~ var formats = require('web.formats');

    //~ var QWeb = core.qweb;
    var _t = core._t;
    var screens = require('point_of_sale.screens');

    screens.PaymentScreenWidget.include({
        finalize_validation: function() {
            var self = this;
            var order = this.pos.get_order();

            if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) { 

                    this.pos.proxy.open_cashbox();
            }


            order.initialize_validation_date();

            if (order.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;

                invoiced.fail(function(error){
                    self.invoicing = false;
                    if (error.message === 'Missing Customer') {
                        self.gui.show_popup('confirm',{
                            'title': _t('Please select the Customer'),
                            'body': _t('You need to select the customer before you can invoice an order.'),
                            confirm: function(){
                                self.gui.show_screen('clientlist');
                            },
                        });
                    } else if (error.code < 0) {        // XmlHttpRequest Errors
                        self.gui.show_popup('error',{
                            'title': _t('The order could not be sent'),
                            'body': _t('Check your internet connection and try again.'),
                        });
                    } else if (error.code === 200) {    // OpenERP Server Errors
                        self.gui.show_popup('error-traceback',{
                            'title': error.data.message || _t("Server Error"),
                            'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
                        });
                    } else {                            // ???
                        self.gui.show_popup('error',{
                            'title': _t("Unknown Error"),
                            'body':  _t("The order could not be sent to the server due to an unknown error"),
                        });
                    }
                });

                invoiced.done(function(){
                    self.invoicing = false;
                    self.gui.show_screen('receipt');
                });
            } else if (this.pos.config.registry_id) {
                // This POS must contact an FCU
                this.pos.push_order(order)
                    .done(function(){
                        this.gui.show_screen('receipt');
                    })
                    .fail(function(error){
                        console.log(error);
                        self.gui.show_popup('error',{
                            'title': _t('The order could not be sent'),
                            'body': _t('Check your internet connection and try again.')
                        });
                    });
            } else {
                this.pos.push_order(order);
                this.gui.show_screen('receipt');
            }

        }
    });
});
