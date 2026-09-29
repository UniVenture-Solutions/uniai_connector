import frappe
from frappe.permissions import add_permission

ROLE = 'UniAI Connector Reader'

def install():
    if not frappe.db.exists('Role', ROLE):
        frappe.get_doc({'doctype':'Role','role_name':ROLE,'desk_access':0}).insert(ignore_permissions=True)
    for dt in ('Customer','Sales Invoice','Company'):
        add_permission(dt, ROLE, ptype='read')
    frappe.clear_cache()
