"""Pure deterministic aggregation; currencies are never mixed."""
from decimal import Decimal
from datetime import date

def summarize(rows, as_of):
    totals={}
    for row in rows:
        currency=row['party_account_currency']
        if not currency:raise ValueError('Missing account currency')
        amount=Decimal(str(row['outstanding_amount']))
        if amount<=0:continue
        bucket=totals.setdefault(currency,{'outstanding':Decimal(0),'overdue':Decimal(0),'invoice_count':0,'overdue_count':0})
        bucket['outstanding']+=amount;bucket['invoice_count']+=1
        due=row.get('due_date')
        if due and date.fromisoformat(str(due))<as_of:
            bucket['overdue']+=amount;bucket['overdue_count']+=1
    return [{**b,'currency':c,'outstanding':str(b['outstanding']),'overdue':str(b['overdue'])} for c,b in sorted(totals.items())]
