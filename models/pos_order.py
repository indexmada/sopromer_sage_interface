# -*- coding: utf-8 -*-

from odoo import models, fields, api

from datetime import datetime,date
import os
import csv

class posOrder(models.Model):
	_inherit = "pos.order"


	def sage_sopro_pos_report(self):
		date_today = date.today()
		session_ids = self.env['pos.session'].sudo().search([('reported', '=', False), ('state', '=', 'closed')])
		
		sage_sale_export = self.env.user.company_id.sage_sale_export
		if sage_sale_export:
			filename = "sale_export.csv"
			file = sage_sale_export+'/'+filename

			file_found = self.find_files(filename, sage_sale_export)
			if file_found:
				os.remove(file)

			with open(file, mode='a') as f:
				writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONE)

				for session_id in session_ids:
					stop_date = session_id.stop_at.strftime("%m/%d/%Y")
					writer.writerow(['E', session_id.config_id.name, stop_date,'',''])
					for order in session_id.order_ids:
						for line in order.lines:
							time_order = order.date_order.strftime("%H:%M:%S")
							writer.writerow(['L', line.product_id.default_code,line.qty,line.price_subtotal_incl,'',time_order,order.user_id.name,order.name])
		else:
			print("No Path Found to export Sale")


	def find_files(self, filename, search_path):
		found = False

		for root, dir, files in os.walk(search_path):
		      if filename in files:
		      	found = True
		return found

class posSession(models.Model):
	_inherit = "pos.session"

	reported = fields.Boolean(string="Reported", default=False)