"""Opt-in database-wide reads. Deliberately bypasses Frappe record permissions."""
import hashlib
import json
import re
import time
from contextlib import contextmanager

import frappe
import pymysql
from uniai_connector.api import authorize
from uniai_connector.sql_policy import validate_sql, verify_grants


def config():
    authorize()
    cfg = frappe.conf.get('uniai_database_reader') or {}
    if not cfg.get('enabled') or frappe.session.user not in cfg.get('allowed_api_users', []):
        frappe.throw('Full database access is disabled for this API user', frappe.PermissionError)
    if not cfg.get('user') or not cfg.get('password') or cfg['user'] in ('root', frappe.conf.get('db_user'), frappe.conf.db_name):
        frappe.throw('Dedicated read-only database credentials are required')
    return cfg




@contextmanager
def reader():
    cfg = config()
    db = frappe.conf.db_name
    conn = pymysql.connect(host=frappe.conf.get('db_host') or '127.0.0.1',
        port=int(frappe.conf.get('db_port') or 3306), database=db,
        user=cfg['user'], password=cfg['password'], connect_timeout=5,
        read_timeout=12, write_timeout=5, charset='utf8mb4', autocommit=False)
    try:
        with conn.cursor(pymysql.cursors.SSCursor) as cur:
            cur.execute('SHOW GRANTS FOR CURRENT_USER')
            verify_grants(cur.fetchall(), db)
            # Fail closed if MariaDB cannot enforce the timeout/read-only transaction.
            cur.execute('SET SESSION max_statement_time=5')
            cur.execute('START TRANSACTION READ ONLY')
            yield cur, db
    finally:
        conn.rollback()
        conn.close()


def audit(operation, started, ok, sql=''):
    frappe.logger('uniai_database', allow_site=True).info(json.dumps({
        'user':frappe.session.user, 'operation':operation, 'ok':ok,
        'ms':round((time.monotonic()-started)*1000),
        'query_hash':hashlib.sha256(sql.encode()).hexdigest() if sql else None}))


def perform(operation, fn, sql=''):
    started=time.monotonic()
    try:
        with frappe.cache.lock('uniai:database-reader', timeout=20, blocking_timeout=0):
            with reader() as (cur, db):
                result=fn(cur,db)
        audit(operation,started,True,sql)
        return result
    except Exception:
        audit(operation,started,False,sql)
        frappe.throw('Database read unavailable or query rejected. Check read-only configuration and query limits.')


@frappe.whitelist(methods=['POST'])
def list_tables(search=''):
    if not isinstance(search,str) or len(search)>80:frappe.throw('Invalid schema search')
    def run(cur,db):
        cur.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_TYPE=%s AND LOCATE(%s,TABLE_NAME)>0 ORDER BY TABLE_NAME LIMIT 61',(db,'BASE TABLE',search))
        rows=cur.fetchall()
        return {'tables':[r[0] for r in rows[:60]],'has_more':len(rows)>60}
    return perform('list_tables',run)


@frappe.whitelist(methods=['POST'])
def describe_table(table):
    if not isinstance(table,str) or len(table)>140:frappe.throw('Invalid table')
    def run(cur,db):
        cur.execute('SELECT COLUMN_NAME,DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION LIMIT 301',(db,table))
        rows=cur.fetchall()
        return {'table':table,'columns':[{'name':r[0],'type':r[1]} for r in rows[:300]],'has_more':len(rows)>300}
    return perform('describe_table',run)


@frappe.whitelist(methods=['POST'])
def run_sql_readonly(sql):
    def run(cur,db):
        query=validate_sql(sql,db)
        cur.execute(query)
        columns=[c[0] for c in cur.description]
        rows=[]; size=0; truncated=False
        for _ in range(101):
            row=cur.fetchone()
            if row is None:break
            values=[None if v is None else str(v) for v in row]
            size+=len(json.dumps(values).encode())
            if len(rows)==100 or size>32000:
                truncated=True;break
            rows.append(values)
        return {'columns':columns,'rows':rows,'truncated':truncated,'scope':'Entire connected database; Frappe record permissions do not apply.'}
    return perform('run_sql_readonly',run,sql if isinstance(sql,str) else '')
