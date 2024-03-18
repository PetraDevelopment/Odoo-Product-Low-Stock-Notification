from itertools import product
from odoo import models, fields, api

class MinQty(models.Model):
    _inherit= 'product.template'
    Min_Qty=fields.Float(string='Minimum Quantity',default='50.0')