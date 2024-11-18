# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = "res.company"
    sage_path_stock = fields.Char("Entrée Stock")
    sage_stock_out = fields.Char("Sortie Stock")
    sage_sale_export = fields.Char("Export Vente")
    sage_path_tarif = fields.Char("Tarif Article")
    export_file_path = fields.Char("Export Vente via Bouton")

    hostname = fields.Char("Nom d'hôte")
    hostusername = fields.Char("Nom d'utilisateur")
    hostmdp = fields.Char("Mot de passe")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sage_path_stock = fields.Char(string="Entrée Stock", related="company_id.sage_path_stock",readonly=False, config_parameter="ftp.stock")
    sage_stock_out = fields.Char(string="Sortie Stock", related="company_id.sage_stock_out",readonly=False, config_parameter="ftp.stock_out")
    sage_sale_export = fields.Char(string="Export Vente", related="company_id.sage_sale_export", readonly=False, config_parameter="ftp.sale")
    sage_path_tarif = fields.Char(string="Tarif Article", related="company_id.sage_path_tarif", readonly=False, config_parameter="ftp.tarif")
    export_file_path = fields.Char(string="Export Vente via Bouton", related="company_id.export_file_path", readonly=False, config_parameter="ftp.file_export")

    hostname = fields.Char(string="Nom d'hôte", related="company_id.hostname", readonly=False, config_parameter="ftp.hostname")
    hostusername = fields.Char(string="Nom d'utilisateur", related="company_id.hostusername", readonly=False, config_parameter="ftp.hostusername")
    hostmdp = fields.Char(string="Mot de passe", related="company_id.hostmdp", readonly=False, config_parameter="ftp.hostmdp")
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('ftp.stock', self.env.user.company_id.sage_path_stock)
        self.env['ir.config_parameter'].sudo().set_param('ftp.stock_out', self.env.user.company_id.sage_stock_out)
        self.env['ir.config_parameter'].sudo().set_param('ftp.sale', self.env.user.company_id.sage_sale_export)
        self.env['ir.config_parameter'].sudo().set_param('ftp.tarif', self.env.user.company_id.sage_path_tarif)
        self.env['ir.config_parameter'].sudo().set_param('ftp.file_export', self.env.user.company_id.export_file_path)

        self.env['ir.config_parameter'].sudo().set_param('ftp.hostname', self.env.user.company_id.hostname)
        self.env['ir.config_parameter'].sudo().set_param('ftp.hostusername', self.env.user.company_id.hostusername)
        self.env['ir.config_parameter'].sudo().set_param('ftp.hostmdp', self.env.user.company_id.hostmdp)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['sage_path_stock'] = self.env.user.company_id.sage_path_stock
        res['sage_stock_out'] = self.env.user.company_id.sage_stock_out
        res['sage_sale_export'] = self.env.user.company_id.sage_sale_export
        res['sage_path_tarif'] = self.env.user.company_id.sage_path_tarif
        res['export_file_path'] = self.env.user.company_id.export_file_path

        res['hostname'] = self.env.user.company_id.hostname
        res['hostusername'] = self.env.user.company_id.hostusername
        res['hostmdp'] = self.env.user.company_id.hostmdp
        return res

