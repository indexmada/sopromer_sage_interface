# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = "res.company"
    sage_path_stock = fields.Char("Entrée Stock")
    sage_sale_export = fields.Char("Export Vente")
    sage_path_tarif = fields.Char("Tarif Article")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sage_path_stock = fields.Char(string="Entrée Stock", related="company_id.sage_path_stock",readonly=False, config_parameter="ftp.stock")
    sage_sale_export = fields.Char(string="Export Vente", related="company_id.sage_sale_export", readonly=False, config_parameter="ftp.sale")
    sage_path_tarif = fields.Char(string="Tarif Article", related="company_id.sage_path_tarif", readonly=False, config_parameter="ftp.tarif")
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('ftp.stock', self.env.user.company_id.sage_path_stock)
        self.env['ir.config_parameter'].sudo().set_param('ftp.sale', self.env.user.company_id.sage_sale_export)
        self.env['ir.config_parameter'].sudo().set_param('ftp.tarif', self.env.user.company_id.sage_path_tarif)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['sage_path_stock'] = self.env.user.company_id.sage_path_stock
        res['sage_sale_export'] = self.env.user.company_id.sage_sale_export
        res['sage_path_tarif'] = self.env.user.company_id.sage_path_tarif
        return res

