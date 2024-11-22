from odoo import models, fields
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
        ('error', 'Erreur')
    ], default='pending', string='Statut', required=True)

    def process_csv(self, file_path):
        # Ouvrir et lire le fichier CSV
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Supposons que le 'name' du stock.picking se trouve dans une colonne 'picking_name' du CSV
                picking_name = row.get('picking_name')  # Remplacer 'picking_name' par le nom de colonne réel dans le CSV

                # Créer un enregistrement dans la file d'attente avec la référence du stock.picking
                self.env['file.import.queue'].create({
                    'name': row.get('name'),  # Nom du fichier (ou autre champ qui peut identifier le fichier)
                    'reference': picking_name,  # La référence correspond au 'name' du stock.picking
                    'status': 'pending',  # Statut initial
                })
