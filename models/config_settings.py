# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = "res.company"
    sage_path_stock = fields.Char("Entrée Stock")
    sage_sale_export = fields.Char("Export Vente")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sage_path_stock = fields.Char(string="Entrée Stock", related="company_id.sage_path_stock",readonly=False, config_parameter="ftp.stock")
    sage_sale_export = fields.Char(string="Export Vente", related="company_id.sage_sale_export", readonly=False, config_parameter="ftp.sale")

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('ftp.stock', self.env.user.company_id.sage_path_stock)
        self.env['ir.config_parameter'].sudo().set_param('ftp.sale', self.env.user.company_id.sage_sale_export)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['sage_path_stock'] = self.env.user.company_id.sage_path_stock
        res['sage_sale_export'] = self.env.user.company_id.sage_sale_export
        return res

