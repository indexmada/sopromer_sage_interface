# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import os
from odoo.exceptions import UserError

<<<<<<< HEAD
#import pysftp

#import paramiko
=======
import pysftp
import paramiko
>>>>>>> 576e034b9eb92f056c1254f95cb556ebf0f940fd

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
            val = self.env['ir.model.data'].sudo().search(
                [('model', '=', 'product.template'), ('res_id', '=', rec.id)], limit=1
            )
            rec.ext_id = val.name or None

<<<<<<< HEAD
	def sage_sopro_update_stock(self):
        sage_path_stock = self.env.user.company_id.sage_path_stock

        if sage_path_stock:
            # Récupérer tous les fichiers en attente dans le répertoire
            files_tab = self.find_files_subdir(".csv", sage_path_stock, "E")
            entree_files_tab = list(filter(lambda f: f.find(FILE_NAME_ENTREE) >= 0, files_tab))
            sortie_files_tab = list(filter(lambda f: f.find(FILE_NAME_SORTIE) >= 0, files_tab))
            print('Fichiers d\'entrée : ', entree_files_tab)

            # Traiter les fichiers de sortie (facultatif)
            self.sage_sopro_stock_out(sortie_files_tab)

            # Connexion SSH pour récupérer les fichiers
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.env.user.company_id.hostname,
                username=self.env.user.company_id.hostusername,
                password=self.env.user.company_id.hostmdp
            )
            sftp = ssh.open_sftp()

            # Traitement séquentiel des fichiers d'entrée
            for file in entree_files_tab:
                if self.is_file_processed(file):
                    self.env['mail.message'].create({
                        'body': f"Le fichier {file} a déjà été traité.",
                        'subject': "Fichier déjà traité",
                        'type': 'notification',
                        'author_id': self.env.user.partner_id.id,
                    })
                    continue  # Si le fichier a déjà été traité, on passe au suivant.

                try:
                    f = sftp.open(file, "r")
                    data_file_char = f.read().decode('utf-8')

                    # Déplacement du fichier après traitement réussi
                    destination_directory = '/opt/odoo/sage_file'
                    self.move_file_copy(sftp, file, destination_directory)

                    data_file = data_file_char.split('\n')
                    self.write_stock(data_file)  # Traitement du fichier

                    # Validation des pickings après traitement
                    self.validate_picking_references()

                    # Mettre à jour l'état du fichier comme traité
                    self.update_file_status(file)

                    f.close()
                except Exception as e:
                    self.env.cr.rollback()
                    self.env['mail.message'].create({
                        'body': f"Erreur lors du traitement du fichier {file}: {str(e)}",
                        'subject': "Erreur Sage Stock Update",
                        'type': 'notification',
                        'author_id': self.env.user.partner_id.id,
                    })
                    continue  # Si une erreur survient, on passe au fichier suivant.

            # Fermer la connexion SSH après avoir traité tous les fichiers
            ssh.close()

        return True

    def is_file_processed(self, file_name):
        """
        Vérifie si un fichier a déjà été traité.
        Vous pouvez ajouter des conditions supplémentaires ici pour vérifier l'état du fichier.
        Par exemple, un champ dans la base de données qui indique si le fichier a été correctement traité.
        """
        processed_files = self.env['ir.model.data'].sudo().search([('model', '=', 'product.template'), ('name', '=', file_name)])
        return bool(processed_files)

    def move_file_copy(self, sftp, file, destination_directory):
        """
        Déplace un fichier sur le FTP vers un répertoire de destination spécifié.
        Cette méthode ne déplace que le fichier après le traitement.
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
            raise UserError(f"Erreur lors du déplacement du fichier {file}: {e}")
=======
def sage_sopro_update_stock(self):
    sage_path_stock = self.env.user.company_id.sage_path_stock

    if sage_path_stock:
        files_tab = self.find_files_subdir(".csv", sage_path_stock, "E")
        entree_files_tab = list(filter(lambda f: f.find(FILE_NAME_ENTREE) >= 0, files_tab))
        sortie_files_tab = list(filter(lambda f: f.find(FILE_NAME_SORTIE) >= 0, files_tab))

        self.sage_sopro_stock_out(sortie_files_tab)

        # Connexion SSH pour récupérer les fichiers
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self.env.user.company_id.hostname,
            username=self.env.user.company_id.hostusername,
            password=self.env.user.company_id.hostmdp
        )
        sftp = ssh.open_sftp()

        # Traitement séquentiel des fichiers
        for file in entree_files_tab:
            # Vérifier si le fichier précédent a été traité avant de traiter ce fichier
            if self.is_previous_file_processed():
                try:
                    f = sftp.open(file, "r")
                    data_file_char = f.read().decode('utf-8')

                    # Nouvel emplacement sur le FTP pour sauvegarde
                    destination_directory = '/FTP-SCD/Sortie/output_stock'
                    self.move_file_copy_within_ftp(sftp, file, destination_directory)

                    data_file = data_file_char.split('\n')
                    self.write_stock(data_file)  # Traitement du fichier

                    # Validation des pickings après traitement
                    self.validate_picking_references()
>>>>>>> 576e034b9eb92f056c1254f95cb556ebf0f940fd

                    f.close()

                    # Mettre à jour le statut du fichier après traitement
                    self.update_file_status(file)

                except Exception as e:
                    self.env.cr.rollback()
                    self.env['mail.message'].create({
                        'body': f"Erreur lors du traitement du fichier {file}: {str(e)}",
                        'subject': "Erreur Sage Stock Update",
                        'type': 'notification',
                        'author_id': self.env.user.partner_id.id,
                    })
            else:
                # Si le fichier précédent n'est pas encore traité, le fichier actuel est mis en attente
                self.env['mail.message'].create({
                    'body': f"Le fichier précédent n'est pas encore traité, fichier {file} en attente.",
                    'subject': "Fichier en attente",
                    'type': 'notification',
                    'author_id': self.env.user.partner_id.id,
                })
                break  # Quitter la boucle et attendre la prochaine exécution du cron

        ssh.close()

    return True


def is_previous_file_processed(self):
    # Vérifier que tous les pickings précédemment créés ont une référence valide
    last_picking = self.env['stock.picking'].search([('state', '=', 'done')], order='create_date desc', limit=1)

    if last_picking and last_picking.name:
        # Vérifier si la référence du picking est bien définie
        return True
    return False


def validate_picking_references(self):
    # Vérification de la validité de la référence de chaque picking importé
    pickings = self.env['stock.picking'].search([('state', '=', 'done')])

    for picking in pickings:
        if not picking.name:
            raise UserError(f"Le picking {picking.id} n'a pas de référence assignée.")


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
                try:
                    f = sftp.open(file, "r")
                    data_file_char = f.read().decode('utf-8')

                    destination_directory = '/opt/odoo/sage_file'
                    self.move_file_copy_within_ftp(sftp, file, destination_directory)

                    data_file = data_file_char.split('\n')
                    self.write_stock(data_file, 'out')

                    f.close()
                except Exception as e:
                    self.env.cr.rollback()
                    self.env['mail.message'].create({
                        'body': f"Erreur lors du traitement du fichier {file}: {str(e)}",
                        'subject': "Erreur Sage Stock Out",
                        'type': 'notification',
                        'author_id': self.env.user.partner_id.id,
                    })
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
        if len(line_val) < 5:  # Vérification du format minimal requis
            continue

        # Processus pour créer ou rechercher un picking
        if line_val[0] == 'E':
            try:
                date_done = datetime.strptime(line_val[1], "%d/%m/%Y")
                location_source_name = line_val[3] if xtype == 'in' else line_val[2]
                location_source = self.env['stock.location'].sudo().search([('name', '=', location_source_name)], limit=1)
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
                        "location_id": self.env['stock.warehouse'].search(
                            [('company_id', '=', self.env.user.company_id.id)], limit=1
                        ).lot_stock_id.id
                    })
                else:
                    stock_picking_vals.update({
                        "picking_type_code": 'outgoing',
                        "location_id": location_source.id,
                        "location_dest_id": self.get_partner_location().id
                    })

                search_stock_picking_id = self.env['stock.picking'].search([('name', '=', stock_picking_vals['name'])], limit=1)
                stock_picking_id = search_stock_picking_id or self.env['stock.picking'].sudo().create(stock_picking_vals)
                stock_picking_ids |= stock_picking_id

            except Exception as e:
                self.env.cr.rollback()
                self.env['mail.message'].create({
                    'body': f"Erreur lors de la création du picking : {str(e)}",
                    'subject': "Erreur Picking Stock",
                    'type': 'notification',
                    'author_id': self.env.user.partner_id.id,
                })
                continue

        # Processus pour gérer les lignes de mouvement de stock
        elif stock_picking_id and len(line_val) >= 5:
            try:
                ref_prod, prod_name, qty, price = line_val[1:5]
                qty = float(qty.replace(',', '.'))
                price = float(price.replace(',', '.'))

                product_tmpl = self.env['product.template'].sudo().search([('ext_id', '=', ref_prod)], limit=1)

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

                stock_move_vals = {
                    "product_id": product_tmpl.product_variant_id.id,
                    "product_uom_qty": qty,
                    "quantity_done": qty,
                    "picking_id": stock_picking_id.id,
                    "location_id": stock_picking_id.location_id.id,
                    "location_dest_id": stock_picking_id.location_dest_id.id,
                    "name": product_tmpl.product_variant_id.name,
                    "product_uom": product_tmpl.uom_id.id
                }
                self.env['stock.move'].sudo().create(stock_move_vals)

            except Exception as e:
                self.env.cr.rollback()
                self.env['mail.message'].create({
                    'body': f"Erreur lors de la création de la ligne de stock : {str(e)}",
                    'subject': "Erreur Stock Move",
                    'type': 'notification',
                    'author_id': self.env.user.partner_id.id,
                })
                continue

    # Validation des pickings
    for picking in stock_picking_ids:
        try:
            picking.action_confirm()
            picking.action_assign()
            picking.button_validate()
        except Exception as e:
            self.env.cr.rollback()
            self.env['mail.message'].create({
                'body': f"Erreur lors de la validation du picking {picking.name} : {str(e)}",
                'subject': "Erreur Validation Picking",
                'type': 'notification',
                'author_id': self.env.user.partner_id.id,
            })


def get_partner_location(self):
    customerloc, supplierloc = self.env['stock.warehouse']._get_partner_locations()
    return customerloc

def find_files_subdir(self, ext, search_path, xtype):
    """
    Recherche les fichiers d'une extension donnée dans les sous-répertoires d'un chemin spécifié.
    """
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
            if '.' not in i:  # Exclure les fichiers, garder seulement les dossiers
                dir_tab.append(i)

    for dirname in dir_tab:
        dir_path = os.path.join(search_path, dirname)
        with conn.cd(dir_path):
            files = conn.listdir()
            for file in files:
                if file.endswith(ext):
                    if xtype in ['E', 'S'] and (FILE_NAME_ENTREE in file or FILE_NAME_SORTIE in file):
                        result.append(os.path.join(dir_path, file))
                    elif xtype == 'T' and FILE_NAME_TARIF in file:
                        result.append(os.path.join(dir_path, file))

    conn.close()
    return result

def remove_file_subdir(self, file):
    """
    Supprime un fichier du serveur FTP.
    """
    conn = pysftp.Connection(
        host=self.env.user.company_id.hostname,
        username=self.env.user.company_id.hostusername,
        password=self.env.user.company_id.hostmdp
    )
    try:
        conn.remove(file)
    except Exception as e:
        print(f"Erreur lors de la suppression du fichier {file} : {e}")
    finally:
        conn.close()

def move_file_copy(self, sftp, file, destination_directory):
    """
    Copie un fichier depuis le FTP vers un répertoire local, puis le supprime du FTP.
    """
    try:
        # Créer le dossier destination s'il n'existe pas
        os.makedirs(destination_directory, exist_ok=True)

        destination_file = os.path.join(destination_directory, os.path.basename(file))
        sftp.get(file, destination_file)  # Télécharger le fichier
        self.remove_file_subdir(file)  # Supprimer le fichier source du FTP

    except Exception as e:
        print(f"Erreur lors du déplacement du fichier {file} : {e}")

def update_price(self):
    """
    Met à jour les prix publics des produits à partir des fichiers CSV dans le répertoire Sage.
    """
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
            try:
                f = sftp.open(file, "r")
                data_file_char = f.read().decode('utf-8')
                f.close()

                # Déplacement du fichier pour archivage
                destination_directory = '/opt/odoo/sage_file'
                self.move_file_copy(sftp, file, destination_directory)

                # Mise à jour des prix publics
                data_file = data_file_char.split('\n')
                self.write_public_price(data_file)

            except Exception as e:
                print(f"Erreur lors du traitement du fichier {file} : {e}")
                continue

        ssh.close()

def write_public_price(self, data):
    """
    Écrit le prix public des produits en fonction des données du fichier.
    """
    for i in data:
        val = i.split(';')
        if len(val) < 2:  # Vérifie si les données sont complètes
            continue

        external_id = val[0]
        try:
            public_price = float(val[1].replace('\r', '').replace(',', '.'))
        except (IndexError, ValueError):
            public_price = 0.0

        # Recherche des produits correspondant à l'ID externe
        product_tmpl_ids = self.env['product.template'].sudo().search([('ext_id', '=', external_id)])

        for product_tmpl in product_tmpl_ids:
            try:
                product_tmpl.sudo().write({"list_price": public_price})
            except Exception as e:
                print(f"Erreur lors de la mise à jour du prix du produit {product_tmpl.name} : {e}")

