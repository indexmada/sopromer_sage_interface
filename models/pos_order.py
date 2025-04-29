# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
import os
import csv
import logging
import tempfile
import paramiko

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = "pos.session"

    reported = fields.Boolean(string="Reported", default=False)
    account_move = fields.Many2one(string="Journal Entry", comodel_name="account.move", compute="_compute_account_move")

    @api.multi
    def sage_sopro_pos_report(self):
        for session in self:
            call_type = self._context.get('call_type', False)
            export_folder = session.env.user.company_id.export_file_path if call_type == 'button' else session.env.user.company_id.sage_sale_export

            if not export_folder:
                _logger.error("No Path Found to export Sale")
                return

            stop_date = session.stop_at.strftime("%d/%m/%Y") if session.stop_at else ''
            date_export = datetime.now().strftime("%d-%m-%Y %H%M%S")
            filename = f"Facture{date_export}.csv"

            # 🔧 Génération du fichier CSV en local (temporaire)
            with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='', encoding='utf-8') as temp_file:
                writer = csv.writer(temp_file, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONE, escapechar='\\')

                writer.writerow([
                    'E',
                    session.account_move.name or '',
                    stop_date,
                    '',
                    session.config_id.code_pdv_sage or '',
                    session.config_id.souche or ''
                ])

                for order in session.order_ids:
                    time_order = order.date_order.strftime("%H:%M:%S")
                    username = order.user_id.name
                    ordername = order.name

                    for line in order.lines:
                        if not line.product_id.product_pack:
                            writer.writerow([
                                'L',
                                self.clean(line.product_id.ext_id),
                                self.clean_qty(line.qty),
                                self.clean_price(line.price_unit),
                                self.clean_price(line.product_id.standard_price),
                                time_order,
                                username,
                                ordername
                            ])
                        else:
                            for p in line.product_id.product_item_ids:
                                writer.writerow([
                                    'L',
                                    self.clean(p.product_id.ext_id),
                                    self.clean_qty(p.quantity * line.qty),
                                    self.clean_price(p.unit_cost),
                                    self.clean_price(p.product_id.standard_price),
                                    time_order,
                                    username,
                                    ordername
                                ])

            # 🔒 Envoi SFTP avec Paramiko
            try:
                hostname = "ftp.tonserveur.com"       # à adapter
                port = 22
                username = "ton_user"
                password = "ton_mot_de_passe"

                transport = paramiko.Transport((hostname, port))
                transport.connect(username=username, password=password)
                sftp = paramiko.SFTPClient.from_transport(transport)

                remote_dir = os.path.join(export_folder, session.config_id.code_pdv_sage)
                remote_path = os.path.join(remote_dir, filename)

                # Crée les dossiers distants si besoin
                try:
                    sftp.chdir(remote_dir)
                except IOError:
                    # Dossier distant n'existe pas, on le crée
                    parts = remote_dir.strip('/').split('/')
                    path = ''
                    for part in parts:
                        path += '/' + part
                        try:
                            sftp.chdir(path)
                        except IOError:
                            sftp.mkdir(path)
                            sftp.chdir(path)

                sftp.put(temp_file.name, remote_path)
                _logger.info(f"CSV transféré avec succès : {remote_path}")
                sftp.close()
                transport.close()

            except Exception as e:
                _logger.exception(f"Erreur lors du transfert SFTP : {e}")

    def clean(self, value):
        if value:
            return str(value).strip()  # Retire les espaces inutiles en début et fin de chaîne
        return ''

    def clean_qty(self, qty):
        return str(qty).replace('.', ',') if qty else '0'

    def clean_price(self, price):
        return f'{price:.2f}' if price else '0.00'

    def _compute_account_move(self):
        for rec in self:
            if rec.order_ids:
                rec.account_move = rec.order_ids[0].account_move
            else:
                rec.account_move = None

    @api.multi
    def action_pos_session_closing_control(self):
        self._check_pos_session_balance()
        for session in self:
            session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
            if not session.config_id.cash_control:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        session.action_pos_session_close()
                        break
                    except Exception as e:
                        if 'could not obtain lock' in str(e) and attempt < max_retries - 1:
                            import time
                            time.sleep(2 * (attempt + 1))  # Délai exponentiel
                            continue
                        raise

            session.sage_sopro_pos_report()  # Réactivation de l'appel à l'exportation

        return True


class posConfig(models.Model):
    _inherit = "pos.config"

    code_pdv_sage = fields.Char("Code Echope")
    souche = fields.Char("Souche")
