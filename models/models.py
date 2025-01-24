# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import os
import pysftp
import paramiko
import logging


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


class FileImportQueue(models.Model):
	_name = 'file.import.queue'
	_description = 'Queue pour gérer l\'importation des fichiers'

	name = fields.Char(string='Nom du fichier', required=True)
	stock_reference = fields.Char(string='Référence du fichier', required=True, unique=True)
	status = fields.Selection([
	    ('pending', 'En attente'),
	    ('processing', 'En cours'),
	    ('processed', 'Traité'),
	    ('error', 'Erreur')
	], default='pending', string='Statut', required=True)

_logger = logging.getLogger(__name__)

class StockImport(models.Model):
	_name = 'stock.import'

	def sage_sopro_update_stock(self):
		sage_path_stock = self.env.user.company_id.sage_path_stock

		if sage_path_stock:
			files_tab = self.find_files_subdir(".csv", sage_path_stock, "E")
			entree_files_tab = list(filter(lambda f: f.find(FILE_NAME_ENTREE) >= 0, files_tab))
			sortie_files_tab = list(filter(lambda f: f.find(FILE_NAME_SORTIE) >= 0, files_tab))
			print('files_tab entree : ', entree_files_tab)
			self.sage_sopro_stock_out(sortie_files_tab)

			# SSH
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(hostname=self.env.user.company_id.hostname, username=self.env.user.company_id.hostusername, password=self.env.user.company_id.hostmdp)
			sftp = ssh.open_sftp()
			# END SSH

			for file in entree_files_tab:
				f = sftp.open(file, "r")

				data_file_char = f.read()
				data_file_char = data_file_char.decode('utf-8')

				# Ajout du fichier à la file d'attente
				reference = self.extract_reference_from_file(data_file_char)
				file_queue = self.env['file.import.queue'].create({
					'name': file,
					'reference': reference,  # Utilisation de la référence extraite
					'status': 'pending'
				})

				# Vérification de la référence dans stock.picking
				picking_exists = self.env['stock.picking'].search([('name', '=', reference)], limit=1)

				if picking_exists:
					# Si la référence existe déjà, on marque le fichier comme duplicate
					file_queue.write({'status': 'duplicate'})
					print(f"Le fichier {file} est marqué comme duplicate.")
					sftp.remove(file)  # Suppression du fichier du répertoire distant
				else:
					# Si la référence n'existe pas, on traite le fichier
					data_file = data_file_char.split('\n')
					self.write_stock(data_file)
					file_queue.write({'status': 'processed'})
					print(f"Le fichier {file} a été traité.")

				f.close()

			ssh.close()

	def extract_reference_from_file(self, data_file_char):
		"""
		Fonction pour extraire la référence du fichier CSV.
		Cette fonction est modifiée pour extraire la référence stock.picking du fichier.
		"""
		lines = data_file_char.split("\n")
		if lines:
		    first_line = lines[0].split(';')  # On sépare la première ligne par le caractère ';'
		    reference = first_line[4]  # La référence de stock.picking est dans la 5ème colonne (index 4)
		    return reference
		return None

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
	    if not data or len(data) < 2:
	        _logger.error("Le fichier de données est vide ou incomplet. Aucun traitement effectué.")
	        return

	    stock_picking_ids = self.env['stock.picking'].sudo()
	    stock_picking_id = None
	    l_source = None
	    l_dest = None

	    for i, line in enumerate(data, start=1):
	        line_val = line.split(';')
	        if len(line_val) < 5:  # Vérifier que chaque ligne a au moins 5 colonnes
	            _logger.error(f"Ligne {i} du fichier est incorrecte : {line}. Ignorée.")
	            continue

	        if line_val[0] == 'E':  # Début d'un picking
	            try:
	                date_done = datetime.strptime(line_val[1], "%d/%m/%Y")
	                location_source_name = line_val[3] if xtype == 'in' else line_val[2]
	                location_source = self.env['stock.location'].sudo().search([('name', '=', location_source_name)])
	                if not location_source:
	                    location_source = self.env['stock.location'].sudo().create({"name": location_source_name})

	                stock_picking_vals = {
	                    "date_done": date_done,
	                    "name": line_val[4],
	                    "picking_type_id": self.get_picking_type(xtype).id
	                }

	                if xtype == 'in':
	                    stock_picking_vals.update({
	                        "picking_type_code": 'incoming',
	                        "location_dest_id": location_source.id,
	                        "location_id": self.env['stock.warehouse'].search(
	                            [('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id.id
	                    })
	                    l_dest = location_source
	                    l_source = self.env['stock.warehouse'].search(
	                        [('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id
	                else:
	                    stock_picking_vals.update({
	                        "picking_type_code": 'outgoing',
	                        "location_id": location_source.id,
	                        "location_dest_id": self.get_partner_location().id
	                    })
	                    l_source = location_source
	                    l_dest = self.get_partner_location()

	                # Vérifier si le picking existe déjà
	                search_stock_picking_id = self.env['stock.picking'].search([('name', '=', stock_picking_vals['name'])])
	                if search_stock_picking_id:
	                    _logger.info(f"Ligne {i} : Le picking {search_stock_picking_id.name} existe déjà. Ignoré.")
	                    continue

	                # Créer un nouveau picking
	                stock_picking_id = self.env['stock.picking'].sudo().create(stock_picking_vals)
	                stock_picking_ids |= stock_picking_id
	            except Exception as e:
	                _logger.error(f"Ligne {i} : Erreur lors du traitement du picking : {e}")
	                continue

	        elif stock_picking_id and len(line_val) > 3:  # Ajouter un mouvement au picking
	            try:
	                ref_prod = line_val[1]
	                if not ref_prod:
	                    _logger.error(f"Ligne {i} : Référence produit manquante. Ignorée.")
	                    continue

	                prod_name = line_val[2]
	                qty = line_val[3]
	                price = line_val[4]

	                # Vérifier les données de quantité et de prix
	                try:
	                    qty = float(qty.replace(',', '.'))
	                    price = float(price.replace(',', '.'))
	                    if qty <= 0 or price < 0:
	                        _logger.error(f"Ligne {i} : Quantité ({qty}) ou prix ({price}) invalide(s). Ignorée.")
	                        continue
	                except ValueError:
	                    _logger.error(f"Ligne {i} : Erreur de conversion pour quantité/prix : {qty}, {price}. Ignorée.")
	                    continue

	                # Rechercher ou créer le produit
	                product_tmpl = self.env['product.template'].sudo().search([]).filtered(lambda p: p.ext_id == ref_prod)
	                if not product_tmpl:
	                    product_tmpl = self.env['product.template'].sudo().create({
	                        "name": prod_name,
	                        "standard_price": price,
	                        "type": 'product',
	                        "new_dc": ref_prod,
	                        "available_in_pos": True
	                    })

	                    self.env['ir.model.data'].sudo().create({
	                        "name": ref_prod,
	                        "model": "product.template",
	                        "res_id": product_tmpl.id
	                    })

	                # Créer le mouvement de stock
	                stock_move_vals = {
	                    "product_id": product_tmpl.product_variant_id.id,
	                    "product_uom_qty": qty,
	                    "quantity_done": qty,
	                    "picking_id": stock_picking_id.id,
	                    "location_id": l_source.id,
	                    "location_dest_id": l_dest.id,
	                    "name": product_tmpl.product_variant_id.name,
	                    "product_uom": product_tmpl.uom_id.id
	                }
	                self.env['stock.move'].sudo().create(stock_move_vals)
	            except Exception as e:
	                _logger.error(f"Ligne {i} : Échec de traitement pour le mouvement de stock. Erreur : {e}")
	                continue

	    # Valider les pickings créés
	    if stock_picking_ids:
	        for picking in stock_picking_ids:
	            try:
	                picking.action_confirm()
	                picking.action_assign()
	                picking.button_validate()
	            except Exception as e:
	                _logger.error(f"Erreur lors de la validation du picking {picking.name}. Erreur : {e}")


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