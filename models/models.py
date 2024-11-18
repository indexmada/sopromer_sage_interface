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
    _inherit = "product.template"

    new_dc = fields.Char("New Dc")
    ext_id = fields.Char(string="ext id", compute="_compute_ext_id")

    def _compute_ext_id(self):
        for rec in self:
            val = self.env['ir.model.data'].sudo().search([('model', '=', 'product.template'), ('res_id', '=', rec.id)], limit=1)
            rec.ext_id = val.name or None

	def sage_sopro_update_stock(self):
	    sage_path_stock = self.env.user.company_id.sage_path_stock

	    if sage_path_stock:
	        files_tab = self.find_files_subdir(".csv", sage_path_stock, "E")
	        entree_files_tab = list(filter(lambda f: f.find(FILE_NAME_ENTREE) >= 0, files_tab))
	        sortie_files_tab = list(filter(lambda f: f.find(FILE_NAME_SORTIE) >= 0, files_tab))

	        self.sage_sopro_stock_out(sortie_files_tab)

	        ssh = paramiko.SSHClient()
	        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	        ssh.connect(
	            hostname=self.env.user.company_id.hostname,
	            username=self.env.user.company_id.hostusername,
	            password=self.env.user.company_id.hostmdp
	        )
	        sftp = ssh.open_sftp()

	        for file in entree_files_tab:
	            f = sftp.open(file, "r")
	            data_file_char = f.read().decode('utf-8')

	            # Nouvel emplacement sur le FTP pour sauvegarde
	            destination_directory = '/FTP-SCD/Sortie/output_stock'
	            self.move_file_copy_within_ftp(sftp, file, destination_directory)

	            data_file = data_file_char.split('\n')
	            self.write_stock(data_file)

	            f.close()
	            
	        ssh.close()

def move_file_copy_within_ftp(self, sftp, file, destination_directory):
    """
    Déplace un fichier sur le FTP vers un répertoire de destination spécifié.
    """
    try:
        # Crée le répertoire destination s'il n'existe pas
        try:
            sftp.stat(destination_directory)
        except FileNotFoundError:
            sftp.mkdir(destination_directory)

        # Générer le chemin complet vers le fichier de destination
        destination_file = f"{destination_directory}/{os.path.basename(file)}"
        
        # Déplacer le fichier sur le FTP
        sftp.rename(file, destination_file)
        print(f"Fichier déplacé avec succès vers : {destination_file}")
    except Exception as e:
        print(f"Erreur lors du déplacement du fichier {file} vers {destination_directory} : {e}")


    def sage_sopro_stock_out(self, files_tab):
        sage_stock_out = self.env.user.company_id.sage_stock_out

        if sage_stock_out and files_tab:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.env.user.company_id.hostname,
                username=self.env.user.company_id.hostusername,
                password=self.env.user.company_id.hostmdp
            )
            sftp = ssh.open_sftp()

            for file in files_tab:
                f = sftp.open(file, "r")
                data_file_char = f.read().decode('utf-8')

                destination_directory = '/opt/odoo/sage_file'
                self.move_file_copy(sftp, file, destination_directory)

                data_file = data_file_char.split('\n')
                self.write_stock(data_file, 'out')

                f.close()

            ssh.close()

    def get_picking_type(self, xtype):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.user.company_id.id
        ptype = 'incoming' if xtype == 'in' else 'outgoing'

        types = type_obj.search([('code', '=', ptype), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', ptype), ('warehouse_id', '=', False)])
        return types[:1]

    def write_stock(self, data, xtype='in'):
        stock_picking_ids = self.env['stock.picking'].sudo()

        for i in data:
            line_val = i.split(';')
            if line_val[0] == 'E':
                date_done = datetime.strptime(line_val[1], "%d/%m/%Y")
                location_source_name = line_val[3] if xtype == 'in' else line_val[2]
                location_source = self.env['stock.location'].sudo().search([('name', '=', location_source_name)])
                if not location_source:
                    location_source = self.env['stock.location'].sudo().create({"name": location_source_name})

                stock_picking_vals = {
                    "date_done": date_done,
                    "name": line_val[4],
                    "picking_type_id": self.get_picking_type(xtype).id,
                }

                if xtype == 'in':
                    stock_picking_vals.update({
                        "picking_type_code": 'incoming',
                        "location_dest_id": location_source.id,
                        "location_id": self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id.id
                    })
                else:
                    stock_picking_vals.update({
                        "picking_type_code": 'outgoing',
                        "location_id": location_source.id,
                        "location_dest_id": self.get_partner_location().id
                    })

                search_stock_picking_id = self.env['stock.picking'].search([('name', '=', stock_picking_vals['name'])])
                stock_picking_id = search_stock_picking_id or self.env['stock.picking'].sudo().create(stock_picking_vals)
                stock_picking_ids |= stock_picking_id

            elif stock_picking_id and len(line_val) > 3:
                ref_prod, prod_name, qty, price = line_val[1], line_val[2], line_val[3], line_val[4]
                product_tmpl = self.env['product.template'].sudo().search([]).filtered(lambda p: p.ext_id == ref_prod)

                if not product_tmpl:
                    product_tmpl = self.env['product.template'].sudo().create({
                        "name": prod_name,
                        "standard_price": float(price.replace(',', '.')),
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
                    "product_uom_qty": float(qty.replace(',', '.')),
                    "quantity_done": float(qty.replace(',', '.')),
                    "picking_id": stock_picking_id.id,
                    "location_id": l_source.id,
                    "location_dest_id": l_dest.id,
                    "name": product_tmpl.product_variant_id.name,
                    "product_uom": product_tmpl.uom_id.id
                }
                self.env['stock.move'].sudo().create(stock_move_vals)

        for picking in stock_picking_ids:
            picking.action_confirm()
            picking.action_assign()
            picking.button_validate()

    def get_partner_location(self):
        customerloc, supplierloc = self.env['stock.warehouse']._get_partner_locations()
        return customerloc

    def find_files_subdir(self, ext, search_path, xtype):
        conn = pysftp.Connection(
            host=self.env.user.company_id.hostname,
            username=self.env.user.company_id.hostusername,
            password=self.env.user.company_id.hostmdp
        )
        result = []
        dir_tab = []

        with conn.cd(search_path):
            content = conn.listdir()
            for i in content:
                if i.find('.') < 0:
                    dir_tab.append(i)

        for dirname in dir_tab:
            dir_path = search_path + '/' + dirname
            with conn.cd(dir_path):
                files = conn.listdir()
                for file in files:
                    if xtype in ['E', 'S']:
                        if file[-4:] == ext and (file.find(FILE_NAME_ENTREE) >= 0 or file.find(FILE_NAME_SORTIE) >= 0):
                            result.append(dir_path + '/' + file)
                    else:
                        if file[-4:] == ext and file.find(FILE_NAME_TARIF) >= 0:
                            result.append(dir_path + '/' + file)
        return result

    def remove_file_subdir(self, file):
        conn = pysftp.Connection(
            host=self.env.user.company_id.hostname,
            username=self.env.user.company_id.hostusername,
            password=self.env.user.company_id.hostmdp
        )
        conn.remove(file)

    def move_file_copy(self, sftp, file, destination_directory):
        destination_file = os.path.join(destination_directory, file.split('/')[-1])
        sftp.get(file, destination_file)
        self.remove_file_subdir(file)

    def update_price(self):
        sage_path_tarif = self.env.user.company_id.sage_path_tarif

        if sage_path_tarif:
            files_tab = self.find_files_subdir(".csv", sage_path_tarif, "T")

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.env.user.company_id.hostname,
                username=self.env.user.company_id.hostusername,
                password=self.env.user.company_id.hostmdp
            )
            sftp = ssh.open_sftp()

            for file in files_tab:
                f = sftp.open(file, "r")
                data_file_char = f.read().decode('utf-8')

                destination_directory = '/opt/odoo/sage_file'
                self.move_file_copy(sftp, file, destination_directory)

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
            except IndexError:
                public_price = 0

            product_tmpl_ids = self.env['product.template'].sudo().search([]).filtered(lambda p: p.ext_id == external_id)

            for product_tmpl in product_tmpl_ids:
                product_tmpl.sudo().write({"list_price": float(public_price)})
