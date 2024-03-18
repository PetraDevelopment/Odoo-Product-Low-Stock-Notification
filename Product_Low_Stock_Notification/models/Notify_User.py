from dataclasses import field
from tokenize import StringPrefix
from odoo import fields,models

class StockNotification(models.Model):
    _inherit = "res.users"

    Notify=fields.Boolean(string="Notify User")

