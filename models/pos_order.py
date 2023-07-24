# -*- coding: utf-8 -*-

from odoo import models, fields, api

from datetime import datetime,date
import os
import csv

class posSession(models.Model):
	_inherit = "pos.session"

	reported = fields.Boolean(string="Reported", default=False)
	account_move = fields.Many2one(string="Journal Entry", comodel_name="account.move", compute="_compute_account_move")

	def sage_sopro_pos_report(self):
		date_today = date.today()
		# session_ids = self.env['pos.session'].sudo().search([('reported', '=', False), ('state', '=', 'closed')])
		
		sage_sale_export = self.env.user.company_id.sage_sale_export
		session_name = self.name.replace('/', '-')
		if sage_sale_export:
			filename = "sale_export"+session_name+".csv"
			file = sage_sale_export+'/'+filename

			file_found = self.find_files(filename, sage_sale_export)
			if file_found:
				os.remove(file)

			with open(file, mode='a') as f:
				writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONE)

				session_id = self
				stop_date = session_id.stop_at.strftime("%m/%d/%Y")
				# writer.writerow(['E', session_id.config_id.name, stop_date,'',''])
				writer.writerow(['E', session_id.account_move.name, stop_date,'',''])
				for order in session_id.order_ids:
					for line in order.lines:
						time_order = order.date_order.strftime("%H:%M:%S")
						writer.writerow(['L', line.product_id.ext_id,line.qty,line.price_subtotal_incl,line.product_id.standard_price,time_order,order.user_id.name,order.name])
		else:
			print("No Path Found to export Sale")


	def find_files(self, filename, search_path):
		found = False

		for root, dir, files in os.walk(search_path):
			if filename in files:
				found = True
		return found

	def _compute_account_move(self):
		for rec in self:
			if rec.order_ids:
				rec.account_move = rec.order_ids[0].account_move
			else:
				rec.account_move = None

	@api.multi
	def action_pos_session_closing_control(self):
		self._check_pos_session_balance()
		for session in self:
			session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
			if not session.config_id.cash_control:
				session.action_pos_session_close()

		self.sage_sopro_pos_report()
		return True