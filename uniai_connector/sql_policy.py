import re
"""Conservative SELECT-only grammar; DB grants remain the primary write barrier."""
import sqlglot
from sqlglot import exp

FUNCTIONS = {'AND','OR','CASE','ABS','AVG','CAST','CEIL','CEILING','COALESCE','CONCAT','CONCAT_WS',
 'COUNT','CURDATE','CURRENT_DATE','DATE','DATEDIFF','DATE_ADD','DATE_SUB','DAY',
 'EXTRACT','FLOOR','IF','IFNULL','LOWER','MAX','MIN','MONTH','NULLIF','ROUND',
 'SUM','TRIM','UPPER','YEAR','DATE_FORMAT','TIMESTAMPDIFF','CURRENT_TIMESTAMP',
 'TS_OR_DS_TO_DATE'}


def validate_sql(sql, database):
    if not isinstance(sql, str) or not 1 <= len(sql) <= 12000:
        raise ValueError('Invalid query size')
    trees = sqlglot.parse(sql, read='mysql')
    if len(trees) != 1 or not isinstance(trees[0], (exp.Select, exp.Union)):
        raise ValueError('Only SELECT queries are supported')
    tree = trees[0]
    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop,
                             exp.Command, exp.Into, exp.Lock, exp.Set, exp.PropertyEQ,
                             exp.Parameter, exp.SessionParameter)):
            raise ValueError('Unsupported SQL operation')
        if isinstance(node, exp.Func):
            name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
            if name not in FUNCTIONS:
                raise ValueError('Unsupported SQL function')
        if isinstance(node, exp.Table) and (node.catalog or (node.db and node.db != database)):
            raise ValueError('Queries must stay within the connected database')
        if isinstance(node, exp.With) and node.args.get('recursive'):
            raise ValueError('Recursive queries are not supported')
    # Re-serialize parsed SQL; original comments and dialect tricks are not executed.
    limit = tree.args.get('limit')
    if not limit or not isinstance(limit.expression, exp.Literal) or not limit.expression.is_int or int(limit.expression.this)>101:
        tree = tree.limit(101)
    return tree.sql(dialect='mysql', comments=False)


def verify_grants(grants, database):
    """Reject roles, global/table-extra privileges and access to other databases."""
    found = False
    for row in grants:
        grant = row[0]
        if re.match(r'^GRANT USAGE ON \*\.\* TO ', grant) and 'WITH GRANT OPTION' not in grant:
            continue
        prefix = 'GRANT SELECT ON `' + database.replace('`', '``') + '`.* TO '
        if not grant.startswith(prefix) or 'WITH GRANT OPTION' in grant:
            raise ValueError('Database account must have only SELECT on this database')
        found = True
    if not found:
        raise ValueError('SELECT grant missing')
