import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ.setdefault('QT_SCALE_FACTOR_ROUNDING_POLICY', 'PassThrough')

from PySide6.QtWidgets import QApplication, QScrollArea, QWidget, QTableWidget

import core
from core import BaseDialog
from main_013 import ensure_schema_013
from main_021r import (
    AppWindow, ensure_recovery_schema, ensure_final_schema,
    ensure_customer_type_schema, ensure_company_schema, ensure_fatturapa_schema,
    ensure_users_schema, set_recovery_code,
)

base = core.DB()
try:
    base.conn.close()
except Exception:
    pass
ensure_schema_013()
ensure_fatturapa_schema()
ensure_company_schema()
ensure_customer_type_schema()
ensure_final_schema()
ensure_users_schema()
ensure_recovery_schema()
set_recovery_code('RESPONSIVE-TEST-123')

app = QApplication([])
w = AppWindow({'id': 1, 'name': 'Test Responsive'})
w.show()
app.processEvents()

sidebar_scroll = w.findChild(QScrollArea, 'ResponsiveSidebarScroll')
if sidebar_scroll is None:
    raise SystemExit('FAIL: responsive sidebar scroll missing')

screen = app.primaryScreen().availableGeometry()
if w.minimumWidth() > screen.width() or w.minimumHeight() > screen.height():
    raise SystemExit('FAIL: main-window minimum size exceeds available screen')

w.show_invoices()
app.processEvents()
page = w.stack.currentWidget()
if page.findChild(QWidget, 'ResponsiveToolbarWrap') is None:
    raise SystemExit('FAIL: wrapping toolbar missing on table page')

table = page.findChild(QTableWidget)
if table is None or table.columnCount() < 8:
    raise SystemExit('FAIL: invoice table not available for compact-layout test')

# Oversized dialogs must be clamped to the usable display instead of extending off-screen.
d = BaseDialog('Responsive dialog test', w)
d.resize(1800, 1200)
d.show()
app.processEvents(); app.processEvents()
if d.width() > screen.width() or d.height() > screen.height():
    raise SystemExit('FAIL: dialog remains larger than the available screen')
d.close()

print('OK 0.1.11-R: responsive sidebar, wrapping toolbars, compact tables and dialog fitting')
