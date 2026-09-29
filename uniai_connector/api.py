"""Only explicit read operations. Frappe session permissions apply to every query."""
import frappe
from frappe.utils import getdate, nowdate
from uniai_connector.balances import summarize
from uniai_connector.setup import ROLE


def authorize():
    if frappe.session.user=='Guest' or ROLE not in frappe.get_roles():
        frappe.throw('Connector reader access required',frappe.PermissionError)


def company_access(company):
    if not isinstance(company,str) or not company or len(company)>140:
        frappe.throw('Select a company')
    if not frappe.get_list('Company',filters={'name':company},fields=['name'],limit_page_length=1):
        frappe.throw('Company access denied',frappe.PermissionError)


@frappe.whitelist(methods=['POST'])
def ping():
    authorize()
    return {'connector_version':'0.1.0','capabilities':['search_customers','outstanding_invoices'],'user':frappe.session.user,'companies':frappe.get_list('Company',pluck='name',limit_page_length=100)}


@frappe.whitelist(methods=['POST'])
def search_customers(query,company):
    authorize();company_access(company)
    if not isinstance(query,str) or not 2<=len(query.strip())<=120:
        frappe.throw('Customer search must contain 2 to 120 characters')
    from uniai_connector.matching import rank_customers
    # Scan only permission-visible customer names; normalize locally so punctuation
    # does not exclude the correct candidate before ranking.
    rows=[]
    for start in range(0,10001,200):
        page=frappe.get_list('Customer',filters={'disabled':0},fields=['name','customer_name'],order_by='name asc',limit_start=start,limit_page_length=200)
        rows.extend(page)
        if len(rows)>10000:frappe.throw('Customer directory exceeds this search limit')
        if len(page)<200:break
    ranked=rank_customers(query.strip(),rows)
    return {'customers':ranked[:5],'has_more':len(ranked)>5}


@frappe.whitelist(methods=['POST'])
def outstanding_invoices(customer,company):
    authorize();company_access(company)
    if not isinstance(customer,str) or len(customer)>140:frappe.throw('Invalid customer')
    customers=frappe.get_list('Customer',filters={'name':customer,'disabled':0},fields=['name','customer_name'],limit_page_length=1)
    if not customers:frappe.throw('Customer not accessible',frappe.PermissionError)
    if not frappe.has_permission('Sales Invoice',ptype='read'):frappe.throw('Invoice access denied',frappe.PermissionError)
    rows=[]
    for start in range(0,10001,200):
        page=frappe.get_list('Sales Invoice',filters={'customer':customer,'company':company,'docstatus':1,'outstanding_amount':['>',0]},fields=['name','due_date','outstanding_amount','party_account_currency'],order_by='due_date asc, name asc',limit_start=start,limit_page_length=200)
        rows.extend(page)
        if len(rows)>10000:frappe.throw('Too many invoices for this operation')
        if len(page)<200:break
    as_of=nowdate()
    return {'customer':customers[0],'company':company,'as_of':as_of,'totals':summarize(rows,getdate(as_of)), 'invoices':[dict(name=r.name,due_date=str(r.due_date) if r.due_date else None,outstanding=str(r.outstanding_amount),currency=r.party_account_currency,overdue=bool(r.due_date and getdate(r.due_date)<getdate(as_of))) for r in rows[:10]],'invoice_count':len(rows),'shown':min(len(rows),10),'scope':'Positive outstanding submitted invoices visible to this API user; unallocated credits and advances are excluded.'}
