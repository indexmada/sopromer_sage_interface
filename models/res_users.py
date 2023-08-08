# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Users(models.Model):
	_inherit = "res.users"

	pos_access_ids = fields.Many2one(comodel_name = "pos.config", string="Liste Points de Vente")

	@api.model
	def create(self, vals):
	    self.clear_caches()
	    return super(Users, self).create(vals)

	@api.multi
	def write(self, vals):
	    self.clear_caches()
	    return super(Users, self).write(vals)