from openerp import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class pos_order(model.Models):
    """ POS order  """
    _inherit = 'pos.order'
    
    
    @api.one
    def action_done(self):
        super pos_order(self).action_done()
        raise Warning('Action Done')
        return True
