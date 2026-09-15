import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import sqlite3
from PySide6.QtWidgets import QApplication, QComboBox

import core
from main_013 import ensure_schema_013
from main_020 import (
    AppWindow, ensure_final_schema, ensure_customer_type_schema,
    ensure_company_schema, ensure_fatturapa_schema, ensure_users_schema,
    calc_line,
)

base = core.DB()
try:
    base.conn.close()
except Exception:
    pass
ensure_schema_013(); ensure_fatturapa_schema(); ensure_company_schema(); ensure_customer_type_schema(); ensure_final_schema(); ensure_users_schema()

# Quote VAT math
net, vat, gross = calc_line(2, 100, 22)
if (net, vat, gross) != (200.0, 44.0, 244.0):
    raise SystemExit(f'FAIL quote VAT math: {(net,vat,gross)}')

conn = sqlite3.connect(core.DB_PATH)
quote_cols = {r[1] for r in conn.execute('PRAGMA table_info(quote_items)').fetchall()}
for col in ('vat_rate','net_total','vat_amount','gross_total'):
    if col not in quote_cols:
        raise SystemExit('FAIL missing quote column: ' + col)
invoice_cols = {r[1] for r in conn.execute('PRAGMA table_info(invoices)').fetchall()}
if 'payment_method' not in invoice_cols:
    raise SystemExit('FAIL invoices.payment_method missing')
conn.close()

app = QApplication([])
w = AppWindow({'id':1,'name':'Test'})
w.show_company_data(); w.show(); app.processEvents()
regime = w.findChild(QComboBox, 'CompanyTaxRegimeCombo')
legal = w.findChild(QComboBox, 'CompanyLegalTypeCombo')
default_payment = w.findChild(QComboBox, 'CompanyDefaultPaymentCombo')
if regime is None or regime.findData('RF19') < 0:
    raise SystemExit('FAIL tax regime selector / RF19 missing')
if legal is None or legal.findData('SOCIETA') < 0 or legal.findData('DITTA') < 0:
    raise SystemExit('FAIL legal type selector missing')
if default_payment is None or default_payment.findData('MP01') < 0 or default_payment.findData('MP08') < 0 or default_payment.findData('MP05') < 0:
    raise SystemExit('FAIL payment choices missing')

print('OK 0.1.10: invoice payment methods, quote VAT and company fiscal regime/type')
