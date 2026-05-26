import logging

from odoo import api, models

_logger = logging.getLogger(__name__)
_logger.info("=== report_sale_details.py MODULE LOADED ===")


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("=== _get_report_values override CALLED for docids=%s ===", docids)
        res = super()._get_report_values(docids, data=data)
        _logger.info("=== _get_report_values context keys: %s ===", list(res.keys()))
        configs = self.env['pos.config']
        session_ids = data.get('session_ids') if data else None
        config_ids = data.get('config_ids') if data else None
        if not config_ids and not session_ids:
            session_ids = docids
        if config_ids:
            configs = self.env['pos.config'].search([('id', 'in', config_ids)])
        elif session_ids:
            sessions = self.env['pos.session'].search([('id', 'in', session_ids)])
            if sessions:
                configs = sessions.mapped('config_id')
        res['config_id'] = configs[:1] if configs else False
        _logger.info("=== config_id set to: %s ===", res['config_id'])
        return res
