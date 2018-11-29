# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api, tools, _
import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class pos_order_line(models.Model):
    _inherit = 'pos.order.line'

    margin = fields.Float(string='Margin', compute='_margin', digits=dp.get_precision('Product Price'), store=True)
    margin_ratio = fields.Float(string='Margin Ratio', compute='_margin_ratio', digits=dp.get_precision('Product Price'), store=True)

    @api.depends('product_id', 'qty', 'price_unit', 'price_subtotal')
    def _margin(self):
        for line in self:
            line.margin = round((line.price_subtotal - (line.product_id.standard_price * line.qty)), 2)

    @api.depends('product_id', 'qty', 'price_unit', 'price_subtotal', 'margin')
    def _margin_ratio(self):
        for line in self:
            if line.price_subtotal == 0.0:
                line.margin_ratio = 0.0
            else:
                line.margin_ratio = round(line.margin / line.price_subtotal, 4) * 100


class pos_order(models.Model):
    _inherit = 'pos.order'

    margin = fields.Float(string='Margin', compute='_margin', store=True)

    @api.depends('lines.margin')
    def _margin(self):
        for order in self:
            order.margin = sum(order.filtered(lambda o: o.state != 'cancel').lines.mapped('margin'))


class report_pos_order(models.Model):
    _inherit = 'report.pos.order'

    margin = fields.Float('Margin', readonly=True)

    @api.model_cr
    def init(self):
        super(report_pos_order, self).init()
        tools.drop_view_if_exists(self._cr, 'report_pos_order')
        self._cr.execute("""
            CREATE OR REPLACE VIEW report_pos_order AS (
                SELECT
                    MIN(l.id) AS id,
                    COUNT(*) AS nbr_lines,
                    s.date_order AS date,
                    SUM(l.qty) AS product_qty,
                    SUM(l.qty * l.price_unit) AS price_sub_total,
                    SUM((l.qty * l.price_unit) * (100 - l.discount) / 100) AS price_total,
                    SUM((l.qty * l.price_unit) * (l.discount / 100)) AS total_discount,
                    SUM(l.margin) AS margin,
                    (SUM(l.qty * l.price_unit)/SUM(l.qty * u.factor))::decimal AS average_price,
                    SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
                    s.id as order_id,
                    s.partner_id AS partner_id,
                    s.state AS state,
                    s.user_id AS user_id,
                    s.location_id AS location_id,
                    s.company_id AS company_id,
                    s.sale_journal AS journal_id,
                    l.product_id AS product_id,
                    pt.categ_id AS product_categ_id,
                    p.product_tmpl_id,
                    ps.config_id,
                    pt.pos_categ_id,
                    pc.stock_location_id,
                    s.pricelist_id,
                    s.session_id,
                    s.invoice_id IS NOT NULL AS invoiced
                FROM pos_order_line AS l
                    LEFT JOIN pos_order s ON (s.id=l.order_id)
                    LEFT JOIN product_product p ON (l.product_id=p.id)
                    LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
                    LEFT JOIN product_uom u ON (u.id=pt.uom_id)
                    LEFT JOIN pos_session ps ON (s.session_id=ps.id)
                    LEFT JOIN pos_config pc ON (ps.config_id=pc.id)
                GROUP BY
                    s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
                    s.user_id, s.location_id, s.company_id, s.sale_journal,
                    s.pricelist_id, s.invoice_id, s.create_date, s.session_id,
                    l.product_id,
                    pt.categ_id, pt.pos_categ_id,
                    p.product_tmpl_id,
                    ps.config_id,
                    pc.stock_location_id
                HAVING
                    SUM(l.qty * u.factor) != 0
            )
        """)
