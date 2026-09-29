# UniAI Connector

Frappe/ERPNext v16 app exposing three authenticated POST methods:

- `uniai_connector.api.ping`
- `uniai_connector.api.search_customers(query, company)`
- `uniai_connector.api.outstanding_invoices(customer, company)`

Install on the ERPNext site. Installation adds a **UniAI Connector Reader** role with read-only permission on Customer, Sales Invoice, and Company. Assign it to a dedicated API user, configure Company User Permissions, and store its API key/secret in UniAI's encrypted connection settings. Do not add accounting or administrator roles to that user.

The standard business tools use `frappe.get_list`, preserving user permissions. Operations require the connector role and validate company access. These standard tools accept only their documented parameters.

Balances include positive outstanding amounts on submitted invoices visible to the API user. They are grouped by `party_account_currency`. Credits and unallocated advances are excluded, so this is an invoice-outstanding view rather than a full customer ledger balance. Overdue means due date before the ERP site's current date. A 10,000-invoice safety limit fails explicitly rather than returning partial totals.

Tests: `PYTHONPATH=connector python -m unittest discover -s connector/uniai_connector/tests` from the UniAI repository root.


## Optional full database reader

The `uniai_connector.database` module exposes `list_tables`, `describe_table`, and `run_sql_readonly`. These require explicit site configuration, an allowlisted API identity, and a dedicated SELECT-only database account. They bypass Frappe row/company permissions by design; they are off by default and must only be enabled with informed administrator consent. There are no write endpoints.

Configure the protected site configuration key `uniai_database_reader` with `enabled`, `user`, `password`, and `allowed_api_users`. The account must have only SELECT on this site's database (plus USAGE); no fallback to site credentials is allowed. MariaDB read-only transactions, a five-second statement timeout, bounded results, SQL parsing, and hashed query audit records remain enforced.
