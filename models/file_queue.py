from odoo import models, fields, api
import csv

class FileImportQueue(models.Model):
    _name = 'file.import.queue'
    _description = 'Queue pour gérer l\'importation des fichiers'

    name = fields.Char(string='Nom du fichier', required=True)
    reference = fields.Char(string='Référence du fichier', required=True, unique=True)
    status = fields.Selection([
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('processed', 'Traité'),
        ('duplicate', 'En double'),
        ('error', 'Erreur'),
    ], default='pending', string='Statut', required=True)

    def process_file(self, sftp):
        """
        Traite le fichier dans la file d'attente.
        1. Vérifie si la référence existe déjà dans Odoo.
        2. Si oui, marque comme duplicate et déplace le fichier.
        3. Sinon, importe le fichier et met à jour son statut comme 'processed'.
        """
        self.status = 'processing'  # Indiquer que le fichier est en cours de traitement

        # Lire le fichier depuis le répertoire
        try:
            f = sftp.open(self.name, "r")
            data_file_char = f.read()
            data_file_char = data_file_char.decode('utf-8')
            data_file_lines = data_file_char.split('\n')
            f.close()

            # Vérifier si le fichier n'est pas vide
            if len(data_file_lines) > 1:
                first_data_line = data_file_lines[1].split(';')  # Colonne séparée par ";"
                if len(first_data_line) >= 5:
                    stock_reference = first_data_line[4]  # Référence stock picking

                    # Vérifier si la référence existe déjà dans Odoo
                    existing_picking = self.env['stock.picking'].search([('name', '=', stock_reference)], limit=1)
                    if existing_picking:
                        # Si la référence existe déjà, marquer comme duplicate et déplacer le fichier
                        self.status = 'duplicate'
                        destination_directory = '/opt/odoo/sage_file'
                        self.move_file_to_duplicate(sftp, self.name, destination_directory)
                    else:
                        # Si la référence n'existe pas, importer les données
                        self.env['stock.import'].write_stock(data_file_lines)
                        self.status = 'processed'  # Marquer comme traité
        except Exception as e:
            self.status = 'error'  # En cas d'erreur, mettre à jour le statut
            _logger.error(f"Erreur lors du traitement du fichier {self.name}: {str(e)}")

    def move_file_to_duplicate(self, sftp, file_path, destination_directory):
        """
        Déplace un fichier marqué comme duplicate vers le répertoire désigné.
        """
        try:
            sftp.rename(file_path, f"{destination_directory}/{os.path.basename(file_path)}")
        except Exception as e:
            _logger.error(f"Erreur lors du déplacement du fichier {file_path}: {str(e)}")



