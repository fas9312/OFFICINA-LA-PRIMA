import os
os.environ['QT_QPA_PLATFORM']='offscreen'

from PySide6.QtWidgets import QApplication, QLabel
from main_013 import AppWindow, ensure_schema_013

ensure_schema_013()
app=QApplication([])
w=AppWindow(); w.resize(1536,960); w.show(); app.processEvents()

brand=w.findChild(QLabel,'ReadableBrandText')
if brand is None or 'LA PRIMA' not in brand.text():
    raise SystemExit('FAIL: readable sidebar brand missing')

svc_cols={r['name'] for r in w.db.q('PRAGMA table_info(services)')}
if not {'status','service_time'}.issubset(svc_cols):
    raise SystemExit('FAIL: service scheduling columns missing')

inv_table=w.db.one("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice_items'")
if not inv_table:
    raise SystemExit('FAIL: invoice_items table missing')

shot=w.grab()
if shot.isNull() or not shot.save('smoke_013.png'):
    raise SystemExit('FAIL: screenshot')
print('OK 0.1.3 brand, service calendar schema, invoice VAT rows')
