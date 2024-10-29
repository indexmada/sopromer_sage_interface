# -*- coding: utf-8 -*-

from odoo import models, fields, api

from datetime import datetime,date
import os
import csv

import paramiko

HOSTNAME = "ftp.cluster027.hosting.ovh.net"
USERNAME = "sopemoa"
PWD = "K71xiVEUb9cc12xuscHq"

class posSession(models.Model):
	_inherit = "pos.session"

	reported = fields.Boolean(string="Reported", default=False)
	account_move = fields.Many2one(string="Journal Entry", comodel_name="account.move", compute="_compute_account_move")

	def sage_sopro_pos_report(self, call_type):
		date_today = date.today()
		# session_ids = self.env['pos.session'].sudo().search([('reported', '=', False), ('state', '=', 'closed')])
		file_path = ''
		if call_type == 'button':
			file_path = self.env.user.company_id.export_file_path
		else:
			# sage_sale_export = self.env.user.company_id.sage_sale_export
			file_path = self.env.user.company_id.sage_sale_export
		
		if file_path:
			date_str = datetime.now().strftime("%d-%m-%Y %H%M%S")

			filename = "Facture"+str(date_str)+".csv"
			file = file_path+'/'+str(self.config_id.code_pdv_sage)+'/'+filename

			# SSH
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(hostname=self.env.user.company_id.hostname, username=self.env.user.company_id.hostusername, password=self.env.user.company_id.hostmdp)
			sftp = ssh.open_sftp()
			# END SSH

			with sftp.open(file, mode='a') as f:
				writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONE)

				session_id = self
				stop_date = session_id.stop_at.strftime("%d/%m/%Y")
				# writer.writerow(['E', session_id.config_id.name, stop_date,'',''])
				writer.writerow(['E', session_id.account_move.name, stop_date,'',session_id.config_id.code_pdv_sage,session_id.config_id.souche])
				for order in session_id.order_ids:
					for line in order.lines:
							if not line.product_id.product_pack:
								time_order = order.date_order.strftime("%H:%M:%S")
								xqty = str(line.qty).replace('.', ',')
								xprice_subtot = str(line.price_unit).replace('.', ',')
								xstandard_p = str(line.product_id.standard_price).replace('.', ',')
								writer.writerow(['L', line.product_id.ext_id,xqty,xprice_subtot,xstandard_p,time_order,order.user_id.name,order.name])
							else:
								for p in line.product_id.product_item_ids:
									time_order = order.date_order.strftime("%H:%M:%S")
									xqty = str(p.quantity * line.qty).replace('.', ',')
									xprice_subtot = str(p.unit_cost).replace('.', ',')
									xstandard_p = str(p.product_id.standard_price).replace('.', ',')
									writer.writerow(['L', p.product_id.ext_id,xqty,xprice_subtot,xstandard_p,time_order,order.user_id.name,order.name])

			ssh.close()
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

		self.sage_sopro_pos_report('action')
		return True

class posConfig(models.Model):
	_inherit = "pos.config"

	code_pdv_sage = fields.Char("Code Echope")
	souche = fields.Char("Souche")