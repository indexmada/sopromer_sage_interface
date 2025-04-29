# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
import os
import csv
import logging
import paramiko

class PosSession(models.Model):
    _inherit = "pos.session"

    reported = fields.Boolean(string="Reported", default=False)
    account_move = fields.Many2one(string="Journal Entry", comodel_name="account.move", compute="_compute_account_move")

    @api.multi
    def sage_sopro_pos_report(self):
        for session in self:
            date_today = date.today()
            call_type = self._context.get('call_type', False)

            if call_type == 'button':
                file_path = session.env.user.company_id.export_file_path
            else:
                file_path = session.env.user.company_id.sage_sale_export

            if not file_path:
                _logger.error("No Path Found to export Sale")
                return

            stop_date = session.stop_at.strftime("%d/%m/%Y") if session.stop_at else ''
            date_export = datetime.now().strftime("%d-%m-%Y %H%M%S")
            final_path = os.path.join(file_path, session.config_id.code_pdv_sage, f"Facture{date_export}.csv")

            _logger.error(f"_____________________ file_path : {final_path} ____________________")

            # Création des dossiers si besoin
            os.makedirs(os.path.dirname(final_path), exist_ok=True)

            try:
                with open(final_path, 'a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONE, escapechar='\\')

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
                                    clean(line.product_id.ext_id),
                                    clean_qty(line.qty),
                                    clean_price(line.price_unit),
                                    clean_price(line.product_id.standard_price),
                                    time_order,
                                    username,
                                    ordername
                                ])
                            else:
                                for p in line.product_id.product_item_ids:
                                    writer.writerow([
                                        'L',
                                        clean(p.product_id.ext_id),
                                        clean_qty(p.quantity * line.qty),
                                        clean_price(p.unit_cost),
                                        clean_price(p.product_id.standard_price),
                                        time_order,
                                        username,
                                        ordername
                                    ])
            except Exception as e:
                _logger.exception(f"Erreur lors de l’écriture du fichier CSV : {e}")

    def clean(val):
        return str(val).replace(';', ',') if val else ''

    def clean_qty(val):
        return str(val).replace('.', ',').replace(';', ',') if val else '0'

    def clean_price(val):
        return str(round(val or 0, 2)).replace('.', ',').replace(';', ',')


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
