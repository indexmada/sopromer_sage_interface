from odoo import models, api
from psycopg2 import OperationalError
import time

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def button_confirm_bank(self):
        for attempt in range(3):
            try:
                return super().button_confirm_bank()
            except OperationalError as e:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
                self.env.cr.execute("ROLLBACK TO SAVEPOINT retry_point")