import unittest
from uniai_connector.sql_policy import validate_sql

class SQLPolicyTests(unittest.TestCase):
    def test_select_and_aggregates(self):
        sql=validate_sql('SELECT SUM(outstanding_amount) FROM `tabSales Invoice` WHERE docstatus=1','erp')
        self.assertIn('LIMIT 101',sql)
    def test_combined_filters(self):
        sql=validate_sql("SELECT COUNT(name) FROM `tabSales Invoice` WHERE company='UniVenture Traders' AND docstatus=1",'erp')
        self.assertIn('AND',sql)
    def test_small_limit_preserved(self):
        self.assertIn('LIMIT 5',validate_sql('SELECT name FROM `tabCustomer` LIMIT 5','erp'))
    def test_rejects_unsafe_queries(self):
        for sql in ['DELETE FROM x','SELECT 1; SELECT 2',"SELECT * FROM mysql.user",
                    "SELECT LOAD_FILE('/etc/passwd')",'SELECT SLEEP(5)',
                    "SELECT * FROM x INTO OUTFILE '/tmp/x'",'SELECT * FROM x FOR UPDATE',
                    'CALL something()', 'SELECT @a := 2',
                    'WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT 1 FROM x) SELECT * FROM x']:
            with self.subTest(sql=sql),self.assertRaises(Exception):validate_sql(sql,'erp')
    def test_large_limit_capped(self):
        self.assertIn('LIMIT 101',validate_sql('SELECT * FROM x LIMIT 999999','erp'))

class GrantsTest(unittest.TestCase):
    def test_select_only(self):
        from uniai_connector.sql_policy import verify_grants
        verify_grants([('GRANT USAGE ON *.* TO `reader`@`host`',),('GRANT SELECT ON `erp`.* TO `reader`@`host`',)],'erp')
    def test_extra_privileges_and_roles_rejected(self):
        from uniai_connector.sql_policy import verify_grants
        for grant in ['GRANT ALL PRIVILEGES ON `erp`.* TO x','GRANT SELECT ON *.* TO x',
                      'GRANT SELECT ON `other`.* TO x','GRANT `admin` TO x',
                      'GRANT SELECT ON `erp`.* TO x WITH GRANT OPTION']:
            with self.subTest(grant=grant),self.assertRaises(ValueError):verify_grants([(grant,)],'erp')
