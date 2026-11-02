# -*- coding: utf-8 -*-
##############################################################################
#
#    POS Kassaregister SE — Swedish cash register compliance
#    Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################
from odoo import _, models
from odoo.exceptions import UserError


class PosOrderLine(models.Model):
    """Protect the article name programmed on the product (6 kap. 4 §).

    The cashier may not replace the article's programmed text with free
    text in the register. The name on the receipt must be the one the
    product carries, so that the same article is always identified the same
    way in the journal memory.
    """
    _inherit = 'pos.order.line'

    def _programmed_name(self):
        """Return the article's programmed text (6 kap. 4 §)."""
        self.ensure_one()
        product = self.product_id
        if not product:
            return ''
        return product.display_name or product.name or ''

    def write(self, vals):
        if 'full_product_name' in vals:
            for line in self:
                if not line.order_id.session_id.config_id.registration_unit_id:
                    continue
                if line.order_id.state in ('paid', 'done'):
                    raise UserError(_(
                        "Artikelns benämning kan inte ändras efter att "
                        "försäljningen registrerats "
                        "(6 kap. 4 § SKVFS 2021:17)."
                    ))
                expected = line._programmed_name()
                if vals['full_product_name'] != expected:
                    raise UserError(_(
                        "Artikelns benämning får inte bytas mot fritext i "
                        "kassaläget. Benämningen ska vara artikelns "
                        "förprogrammerade text: %(name)s "
                        "(6 kap. 4 § SKVFS 2021:17).",
                        name=expected,
                    ))
        return super().write(vals)
