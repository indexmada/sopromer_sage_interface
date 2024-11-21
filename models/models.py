# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import os

import pysftp

import paramiko

# HOSTNAME = "ftp.cluster027.hosting.ovh.net"
# USERNAME = "sopemoa"
# PWD = "K71xiVEUb9cc12xuscHq"

FILE_NAME_TARIF = "Tarif"
FILE_NAME_ENTREE = "EntrerStoc"
FILE_NAME_SORTIE = "SortieStoc"

class productTemplate(models.Model):
	_inherit="product.template"

	new_dc = fields.Char("New Dc")
	ext_id = fields.Char(string="ext id", compute="_compute_ext_id")

	def _compute_ext_id(self):
		for rec in self:
			val = self.env['ir.model.data'].sudo().search([('model', '=', 'product.template'), ('res_id', '=', rec.id)], limit=1)
			rec.ext_id = val.name or None

	def sage_sopro_update_stock(self):
	    sage_path_stock = self.env.user.company_id.sage_path_stock

	    # Initialiser la liste des transferts réussis
	    successful_transfers = []  

	    if sage_path_stock:
	        # Recherche des fichiers CSV
	        files_tab = self.find_files_subdir(".csv", sage_path_stock, "E")
	        entree_files_tab = list(filter(lambda f: f.find(FILE_NAME_ENTREE) >= 0, files_tab))
	        sortie_files_tab = list(filter(lambda f: f.find(FILE_NAME_SORTIE) >= 0, files_tab))
	        print('files_tab entree : ', entree_files_tab)
	        
	        # Traite les fichiers de sortie
	        self.sage_sopro_stock_out(sortie_files_tab)

	        # Connexion SSH avec Paramiko
	        ssh = paramiko.SSHClient()
	        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	        ssh.connect(
	            hostname=self.env.user.company_id.hostname,
	            username=self.env.user.company_id.hostusername,
	            password=self.env.user.company_id.hostmdp
	        )
	        sftp = ssh.open_sftp()

	        for file in entree_files_tab:
	            try:
	                f = sftp.open(file, "r")
	                data_file_char = f.read()
	                data_file_char = data_file_char.decode('utf-8')

	                # Tentative d'importation du fichier dans Odoo
	                data_file = data_file_char.split('\n')
	                references = self.write_stock(data_file)  # Supposons que cette méthode retourne les références des transferts créés
	                successful_transfers.extend(references)

	                # Si l'importation a réussi, déplacer le fichier
	                destination_directory = '/FTP-SCD/stock_file'  # Répertoire de destination
	                self.move_file_copy(sftp, file, destination_directory)
	                print(f"Le fichier {file} a été traité et déplacé.")

	                f.close()
	            except Exception as e:
	                # Si une erreur se produit, afficher un message et laisser le fichier pour la prochaine récupération
	                print(f"Erreur lors du traitement du fichier {file}: {e}")
	                # Ne pas déplacer le fichier, il restera dans son répertoire d'origine pour être traité à nouveau
	                f.close()

	        # Fermeture de la connexion SSH
	        ssh.close()

	        # Envoi d'un message dans le canal Odoo après traitement des transferts
	        if successful_transfers:
	            channel = self.env.ref('mail.channel_all_employees')  # Récupère le canal global
	            if channel:
	                message_body = (
	                    "Les références suivantes ont été importées avec succès et ont le statut **Done** :\n"
	                    + "\n".join(f"- {ref}" for ref in successful_transfers)
	                )
	                channel.message_post(
	                    body=message_body,
	                    subtype_xmlid="mail.mt_note",  # Type de message
	                    author_id=self.env.ref("base.partner_root").id,  # Envoyé par Odoobot
	                )



	def sage_sopro_stock_out(self, files_tab):
		sage_stock_out = self.env.user.company_id.sage_stock_out

		print('#_*' * 30)
		print('files_tab sortie: ', files_tab)

		if sage_stock_out and files_tab:
			# SSH
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(hostname=self.env.user.company_id.hostname, username=self.env.user.company_id.hostusername, password=self.env.user.company_id.hostmdp)
			sftp = ssh.open_sftp()
			# END SSH

			for file in files_tab:
				f = sftp.open(file, "r")

				data_file_char = f.read()
				data_file_char = data_file_char.decode('utf-8')

				# Déplacer le fichier vers le répertoire de destination et le supprimer du FTP
				destination_directory = '/opt/odoo/sage_file'  # Répertoire de destination
				self.move_file_copy(sftp, file, destination_directory)  # Déplace le fichier
				# Ajout de la suppression du fichier sur le serveur FTP après traitement
				# sftp.remove(file)  # Suppression du fichier sur le serveur FTP après traitement

				data_file = data_file_char.split('\n')
				self.write_stock(data_file, 'out')

				f.close()

			ssh.close()

	def get_picking_type(self, xtype):
		type_obj = self.env['stock.picking.type']
		company_id = self.env.user.company_id.id

		if xtype == 'in':
			ptype = 'incoming'
		else:
			ptype = 'outgoing'

		types = type_obj.search([('code', '=', ptype), ('warehouse_id.company_id', '=', company_id)])
		if not types:
			types = type_obj.search([('code', '=', ptype), ('warehouse_id', '=', False)])
		val = types[:1]
		return val

	def write_stock(self, data, xtype='in'):
		stock_picking_id = False
		stock_picking_ids = self.env['stock.picking'].sudo()
		print('----------',stock_picking_ids)

		for i in data:
			line_val = i.split(';')
			if line_val[0] == 'E':
				print('***E')
				date_done = datetime.strptime(line_val[1], "%d/%m/%Y")
				# location_source
				if xtype == 'in':
					location_source_name = line_val[3]
				else:
					location_source_name = line_val[2]
				location_source = self.env['stock.location'].sudo().search([('name', '=', location_source_name)])
				if not location_source:
					location_source = self.env['stock.location'].sudo().create({
						"name": location_source_name
						})

				# Depot destination
				# location_dest_name = line_val[3]
				# location_dest = self.env['stock.location'].sudo().search([('name', '=', location_dest_name)])
				# if not location_dest:
				# 	location_dest = self.env['stock.location'].sudo().create({
				# 		"name": location_dest_name
				# 		})

				# stock_picking
				stock_picking_vals = {
					"date_done": date_done,
					"name": line_val[4],
					"picking_type_id": self.get_picking_type(xtype).id
				}

				if xtype == 'in':
					stock_picking_vals["picking_type_code"] = 'incoming'
					stock_picking_vals["location_dest_id"] = location_source.id
					l_dest = location_source
					stock_picking_vals["location_id"] = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id.id
					l_source = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id
				else:
					stock_picking_vals["picking_type_code"] = 'outgoing'
					stock_picking_vals["location_id"] = location_source.id
					l_source = location_source
					stock_picking_vals["location_dest_id"] = self.get_partner_location().id
					l_dest = self.get_partner_location()


				# check if picking already exists
				search_stock_picking_id = self.env['stock.picking'].search([('name', '=', stock_picking_vals['name'])])
				if search_stock_picking_id:
					stock_picking_id = search_stock_picking_id
				else:
					stock_picking_id = self.env['stock.picking'].sudo().create(stock_picking_vals)
				stock_picking_ids |= stock_picking_id
			elif stock_picking_id and len(line_val)>3:
				print('**L')
				ref_prod = line_val[1]
				prod_name = line_val[2]
				qty = line_val[3]
				price = line_val[4]
				product_tmpl = self.env['product.template'].sudo().search([]).filtered(lambda p: p.ext_id == ref_prod)
				if not product_tmpl:
					product_tmpl = self.env['product.template'].sudo().create({
						"name": prod_name,
						# "default_code": ref_prod,
						"standard_price": float(price.replace(',','.')),
						"type": 'product',
						"new_dc": ref_prod,
						"available_in_pos": True
						})

					self.env['ir.model.data'].sudo().create({
						"name": ref_prod,
						"model": "product.template",
						"res_id": product_tmpl.id
						})

				stock_move_vals = {
					"product_id": product_tmpl.product_variant_id.id,
					"product_uom_qty": float(qty.replace(',','.')),
					"quantity_done": float(qty.replace(',','.')),
					"picking_id": stock_picking_id.id,
					"location_id": l_source.id,
					"location_dest_id": l_dest.id,
					"name": product_tmpl.product_variant_id.name,
					"product_uom": product_tmpl.uom_id.id
				}
				stock_move = self.env['stock.move'].sudo().create(stock_move_vals)

		if stock_picking_ids and len(stock_picking_ids)>0:
			for picking in stock_picking_ids:
				picking.action_confirm()
				# print('*'*30)
				# print(picking.move_lines)
				picking.action_assign()
				picking.button_validate()

	def get_partner_location(self):
		customerloc, supplierloc = self.env['stock.warehouse']._get_partner_locations()
		return customerloc

	def find_files_subdir(self, ext, search_path, xtype):
		conn = pysftp.Connection(host=self.env.user.company_id.hostname,username=self.env.user.company_id.hostusername, password=self.env.user.company_id.hostmdp)

		result = []
		dir_tab = []
		with conn.cd(search_path):
			content = conn.listdir()
			for i in content:
				if i.find('.') <0:
					dir_tab.append(i)

		print(dir_tab)
		for dirname in dir_tab:
			dir_path = search_path+'/'+dirname
			print(dirname)
			with conn.cd(dir_path):
				files = conn.listdir()
				for file in files:
					if xtype in ['E', 'S']:
						if (file[-4:]==ext and (file.find(FILE_NAME_ENTREE) >= 0 or file.find(FILE_NAME_SORTIE) >= 0)):
							print('file (y): ',file)
							fn = dir_path+'/'+file
							result.append(fn)
					else:
						if (file[-4:]==ext and file.find(FILE_NAME_TARIF) >= 0):
							print('file (y): ',file)
							fn = dir_path+'/'+file
							result.append(fn)
		return result

	def remove_file_subdir(self, file):
		print('removing file: ', file)
		conn = pysftp.Connection(host=self.env.user.company_id.hostname,username=self.env.user.company_id.hostusername, password=self.env.user.company_id.hostmdp)
		conn.remove(file)

	def move_file_copy(self, sftp, file, destination_directory):
		print('copying file to: ', destination_directory)
		destination_file = os.path.join(destination_directory, file.split('/')[-1])  # Get the file name from the path
		sftp.get(file, destination_file)  # Copy the file to the destination directory
		self.remove_file_subdir(file)  # Delete the file from the FTP server after copying

	def update_price(self):
		sage_path_tarif = self.env.user.company_id.sage_path_tarif
		print('*_' * 50)
		if sage_path_tarif:
			files_tab = self.find_files_subdir(".csv", sage_path_tarif, "T")
			print('####')
			print(files_tab)
			# SSH
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(hostname=self.env.user.company_id.hostname, username=self.env.user.company_id.hostusername, password=self.env.user.company_id.hostmdp)
			sftp = ssh.open_sftp()
			# END SSH

			for file in files_tab:
				print('f')
				f = sftp.open(file, "r")

				data_file_char = f.read()
				data_file_char = data_file_char.decode('utf-8')

				# Déplacer le fichier vers le répertoire de destination et le supprimer du FTP
				destination_directory = '/opt/odoo/sage_file'  # Répertoire de destination
				self.move_file_copy(sftp, file, destination_directory)  # Déplace le fichier
				# Ajout de la suppression du fichier sur le serveur FTP après traitement
				#sftp.remove(file)  # Suppression du fichier sur le serveur FTP après traitement

				data_file = data_file_char.split('\n')
				self.write_public_price(data_file)

				f.close()
			ssh.close()

	def write_public_price(self, data):
		for i in data:
			val = i.split(';')
			external_id = val[0]
			try:
				public_price = val[1].replace('\r', '').replace(',', '.')
			except:
				public_price = 0

			product_tmpl_ids = self.env['product.template'].sudo().search([]).filtered(lambda prod: prod.ext_id == external_id)
			print(val, '___  ___', product_tmpl_ids)
			for prod in product_tmpl_ids:
				prod.write({'list_price': float(public_price)})