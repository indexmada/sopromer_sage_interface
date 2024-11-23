from odoo import models, fields
import csv

class FileImportQueue(models.Model):
    _name = 'file.import.queue'
    _description = 'Queue pour gérer l\'importation des fichiers'

    name = fields.Char(string='Emplacement du fichier', required=True)
    reference = fields.Char(string='Nom du fichier', required=True)
    reference_stock = fields.Char(string='Référence Stock', required=True, unique=True)
    status = fields.Selection([
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('processed', 'Traité'),
        ('error', 'Erreur')
    ], default='pending', string='Statut', required=True)

    def process_csv(self, file_path):
        # Ouvrir et lire le fichier CSV
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Supposons que la 5e colonne soit 'name'
                reference_value = row.get('name')  # Utiliser la colonne 'name' du fichier CSV comme référence

                # Créer un enregistrement dans la file d'attente avec la référence du stock.picking
                self.env['file.import.queue'].create({
                    'name': row.get('name'),  # Nom du fichier (ou autre champ qui peut identifier le fichier)
                    'reference_stock': reference_value,  # La référence est maintenant la 5e colonne (name)
                    'status': 'pending',  # Statut initial
                })


