from dataclasses import field
from tokenize import StringPrefix
from odoo import fields,models

class ResCompany(models.Model):
    _inherit = "res.company"

    lowStock=fields.Boolean(string='Low Stock Notification?')
