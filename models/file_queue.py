from odoo import models, fields, api
import csv

class FileImportQueue(models.Model):
    _name = 'file.import.queue'
    _description = 'Queue pour gérer l\'importation des fichiers'

    name = fields.Char(string='Nom du fichier', required=True)
    create_date = fields.Datetime(string='Date de création', default=fields.Datetime.now)
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
                # Supposons que la référence du stock.picking se trouve dans la 4ème colonne du CSV
                picking_name = row.get('name')  # Ici, on récupère la référence du stock.picking

                # Si la référence picking est vide ou invalide, ignorer cette ligne
                if not picking_name:
                    continue

                # Créer une nouvelle entrée dans stock.picking si la référence n'existe pas déjà
                existing_picking = self.env['stock.picking'].search([('name', '=', picking_name)], limit=1)
                if not existing_picking:
                    # Si la référence picking n'existe pas encore, créer un nouveau picking
                    # (Supposons que d'autres données comme 'date_done' soient aussi présentes dans le CSV)
                    date_done = row.get('date_done')  # Exemple d'autre colonne à utiliser, à adapter
                    self.env['stock.picking'].create({
                        'name': picking_name,
                        'date_done': date_done,
                        'picking_type_id': self.get_picking_type('out').id,  # Exemple pour type de picking
                    })
                # Si la référence picking existe déjà, on passe à la ligne suivante (pas de traitement supplémentaire)
                else:
                    continue


