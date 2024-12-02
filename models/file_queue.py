from odoo import models, fields, api

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

    # Cette méthode n'effectue que la gestion de la file d'attente, sans duplicata du traitement
    def manage_import_queue(self):
        """
        Méthode pour gérer la file d'attente des fichiers.
        Cette méthode vérifie les fichiers en attente et les traite, mais ne gère pas le téléchargement via SFTP.
        """
        # Recherche des fichiers en statut 'pending'
        pending_files = self.search([('status', '=', 'pending')])

        for file in pending_files:
            try:
                # Ici, nous supposons que le fichier est déjà récupéré via SFTP dans Code 1
                # Nous mettons simplement à jour le statut en 'processing' et procédons au traitement
                file.status = 'processing'
                # Appel d'une méthode pour traiter le fichier une fois qu'il est en 'processing'
                self.process_file(file)

            except Exception as e:
                _logger.error(f"Erreur lors du traitement du fichier {file.name} : {e}")
                file.status = 'error'

    def process_file(self, file):
        """
        Méthode pour traiter un fichier de la file d'attente.
        :param file: l'objet fichier à traiter
        """
        # Logique pour traiter le fichier, par exemple marquer comme traité
        # Une fois le traitement terminé, mettre à jour le statut à 'processed'
        file.status = 'processed'
        _logger.info(f"Fichier {file.name} traité avec succès.")
