from odoo import models, fields
import csv

class FileImportQueue(models.Model):
    _name = 'file.import.queue'
    _description = 'Queue pour gérer l\'importation des fichiers'

    name = fields.Char(string='Nom du fichier', required=True)
    reference = fields.Char(string='Référence du fichier', required=True, unique=True)
    transfer_reference = fields.Char(string='Référence transfert')  # Nouveau champ
    status = fields.Selection([
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('processed', 'Traité'),
        ('error', 'Erreur'),
        ('duplicate', 'En double')  # Nouveau statut pour les doublons
    ], default='pending', string='Statut', required=True)

    def process_csv(self, file_path):
        # Ouvrir et lire le fichier CSV
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Supposons que la référence du stock.picking se trouve dans une colonne 'picking_name' du CSV
                picking_name = row.get('picking_name')  # Remplacer 'picking_name' par le nom de colonne réel dans le CSV
                transfer_reference = row.get('transfer_reference')  # Colonne à récupérer pour 'Référence transfert'

                # Vérifier si un fichier avec cette référence existe déjà dans la file d'attente
                existing_entry = self.env['file.import.queue'].search([('reference', '=', picking_name)], limit=1)
                if existing_entry:
                    # Si une entrée existe déjà, la marquer comme 'duplicate'
                    existing_entry.write({'status': 'duplicate'})
                    continue  # Passer à la ligne suivante du fichier

                # Créer une nouvelle entrée dans la file d'attente pour cette référence
                self.env['file.import.queue'].create({
                    'name': row.get('name'),  # Nom du fichier (ou autre champ pour identifier le fichier)
                    'reference': picking_name,  # La référence correspond au 'name' du stock.picking
                    'transfer_reference': transfer_reference,  # Ajouter la Référence transfert
                    'status': 'pending',  # Statut initial
                })
