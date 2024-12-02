from odoo import models, fields, api
import csv
import os
import logging

_logger = logging.getLogger(__name__)

class FileImportQueue(models.Model):
    _name = 'file.import.queue'
    _description = 'Queue pour gérer l\'importation des fichiers'

    name = fields.Char(string='Nom du fichier', required=True)
    reference = fields.Char(string='Référence Stock', required=True, unique=True)
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
        2. Si oui, marque comme duplicate, déplace et supprime le fichier.
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
                        # Si la référence existe déjà, marquer comme duplicate
                        _logger.info(f"Doublon trouvé pour le fichier {self.name} avec la référence {stock_reference}")
                        self.write({'status': 'duplicate'})  # Mise à jour du statut du fichier
                        
                        # Déplacer le fichier vers un répertoire de doublons et le supprimer immédiatement
                        destination_directory = '/opt/odoo/sage_file'  # Répertoire pour les doublons
                        self.move_file_to_duplicate(sftp, self.name, destination_directory)
                        sftp.remove(self.name)  # Supprimer le fichier du répertoire SFTP
                    else:
                        # Si la référence n'existe pas, importer les données
                        self.env['stock.import'].write_stock(data_file_lines)
                        self.write({'status': 'processed'})  # Marquer comme traité
        except Exception as e:
            self.write({'status': 'error'})  # En cas d'erreur, mettre à jour le statut
            _logger.error(f"Erreur lors du traitement du fichier {self.name}: {str(e)}")

    def move_file_to_duplicate(self, sftp, file_path, destination_directory):
        """
        Déplace un fichier marqué comme duplicate vers le répertoire désigné.
        """
        try:
            sftp.rename(file_path, f"{destination_directory}/{os.path.basename(file_path)}")
            _logger.info(f"Fichier {file_path} déplacé vers {destination_directory}")
        except Exception as e:
            _logger.error(f"Erreur lors du déplacement du fichier {file_path}: {str(e)}")


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

