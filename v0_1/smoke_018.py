import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QLineEdit, QMessageBox

import core
from main_013 import ensure_schema_013
from main_016 import ensure_fatturapa_schema, ensure_users_schema
from main_017 import ensure_company_schema
from main_018 import AppWindow

base = core.DB()
try:
    base.conn.close()
except Exception:
    pass
ensure_schema_013()
ensure_fatturapa_schema()
ensure_company_schema()
ensure_users_schema()

app = QApplication([])
w = AppWindow({'id': 1, 'name': 'Test'})
w.show()
app.processEvents()

nav = w.findChild(QPushButton, 'CompanyDataNavButton')
if nav is None or nav.text().find('Dati Azienda') < 0:
    raise SystemExit('FAIL: Dati Azienda sidebar button missing')

w.show_settings()
app.processEvents()
if w.findChild(QLabel, 'CompanyDataTitle') is not None:
    raise SystemExit('FAIL: Dati Azienda still visible inside Impostazioni')

w.show_company_data()
app.processEvents()
vat = w.findChild(QLineEdit, 'Company_sdi_vat_number')
name = w.findChild(QLineEdit, 'Company_sdi_business_name')
save = w.findChild(QPushButton, 'SaveCompanyDataButton')
if vat is None or name is None or save is None:
    raise SystemExit('FAIL: editable company fields or save button missing')
if vat.isReadOnly() or not vat.isEnabled() or name.isReadOnly() or not name.isEnabled():
    raise SystemExit('FAIL: company fields are not editable')

name.setText('OFFICINA TEST SNC')
vat.setText('12345678901')
old_info = QMessageBox.information
old_warn = QMessageBox.warning
QMessageBox.information = lambda *a, **k: QMessageBox.Ok
QMessageBox.warning = lambda *a, **k: QMessageBox.Ok
try:
    save.click()
    app.processEvents()
finally:
    QMessageBox.information = old_info
    QMessageBox.warning = old_warn

if w.db.setting('sdi_business_name') != 'OFFICINA TEST SNC':
    raise SystemExit('FAIL: company name was not saved')
if w.db.setting('sdi_vat_number') != '12345678901':
    raise SystemExit('FAIL: VAT number was not saved')

shot = w.grab()
if shot.isNull() or not shot.save('smoke_018.png'):
    raise SystemExit('FAIL: screenshot')
print('OK 0.1.8: Dati Azienda is a dedicated editable sidebar page and saves correctly')
