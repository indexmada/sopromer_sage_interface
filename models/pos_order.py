# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
import os
import csv
import logging
import paramiko
import socket

class PosSession(models.Model):
    _inherit = "pos.session"

    reported = fields.Boolean(string="Reported", default=False)
    account_move = fields.Many2one(string="Journal Entry", comodel_name="account.move", compute="_compute_account_move")



    def sage_sopro_pos_report(self):
        date_today = date.today()
        call_type = self._context.get('call_type', False)
        file_path = self.env.user.company_id.export_file_path if call_type == 'button' else self.env.user.company_id.sage_sale_export

        if not file_path:
            _logger.error("Aucun chemin d'export défini.")
            return

        date_str = datetime.now().strftime("%d-%m-%Y %H%M%S")
        filename = "Facture" + str(date_str) + ".csv"
        full_path = f"{file_path}/{self.config_id.code_pdv_sage}/{filename}"

        _logger.info(f"Chemin complet du fichier CSV : {full_path}")

        ssh = None
        sftp = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.env.user.company_id.hostname,
                username=self.env.user.company_id.hostusername,
                password=self.env.user.company_id.hostmdp,
                timeout=30,
                banner_timeout=30,
                look_for_keys=False,
                allow_agent=False
            )

            sftp = ssh.open_sftp()

            # Création récursive du dossier distant s'il n'existe pas
            remote_folder = os.path.dirname(full_path)
            try:
                sftp.chdir(remote_folder)
            except IOError:
                # Créer récursivement
                parts = remote_folder.strip('/').split('/')
                current_path = ''
                for part in parts:
                    current_path += '/' + part
                    try:
                        sftp.stat(current_path)
                    except FileNotFoundError:
                        sftp.mkdir(current_path)

            with sftp.open(full_path, mode='a') as f:
                writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONE, escapechar='\\')
                stop_date = self.stop_at.strftime("%d/%m/%Y")
                writer.writerow(['E', self.account_move.name, stop_date, '', self.config_id.code_pdv_sage, self.config_id.souche])

                for order in self.order_ids:
                    for line in order.lines:
                        time_order = order.date_order.strftime("%H:%M:%S")
                        if not line.product_id.product_pack:
                            writer.writerow([
                                'L',
                                line.product_id.ext_id,
                                str(line.qty).replace('.', ','),
                                str(line.price_unit).replace('.', ','),
                                str(line.product_id.standard_price).replace('.', ','),
                                time_order,
                                order.user_id.name,
                                order.name
                            ])
                        else:
                            for p in line.product_id.product_item_ids:
                                writer.writerow([
                                    'L',
                                    p.product_id.ext_id,
                                    str(p.quantity * line.qty).replace('.', ','),
                                    str(p.unit_cost).replace('.', ','),
                                    str(p.product_id.standard_price).replace('.', ','),
                                    time_order,
                                    order.user_id.name,
                                    order.name
                                ])
            _logger.info(f"Export CSV terminé avec succès vers {full_path}")

        except socket.timeout:
            _logger.error("⏱️ Connexion SSH expirée (timeout)")
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            _logger.error(f"❌ Connexion refusée : {e}")
        except Exception as e:
            _logger.error(f"❗ Erreur inattendue pendant l'export : {str(e)}")
        finally:
            if sftp:
                sftp.close()
            if ssh:
                ssh.close()


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
