import unittest
from datetime import date
from uniai_connector.balances import summarize

class BalanceTest(unittest.TestCase):
    def test_currency_separation_and_due_today(self):
        rows=[{'party_account_currency':'PKR','outstanding_amount':'0.10','due_date':'2026-09-28'},{'party_account_currency':'PKR','outstanding_amount':'0.20','due_date':'2026-09-29'},{'party_account_currency':'USD','outstanding_amount':'5','due_date':None}]
        result=summarize(rows,date(2026,9,29))
        self.assertEqual(result[0]['outstanding'],'0.30')
        self.assertEqual(result[0]['overdue'],'0.10')
        self.assertEqual(result[0]['overdue_count'],1)
        self.assertEqual(result[1]['outstanding'],'5')
    def test_unknown_currency_fails(self):
        with self.assertRaises(ValueError):summarize([{'party_account_currency':None,'outstanding_amount':2}],date.today())
