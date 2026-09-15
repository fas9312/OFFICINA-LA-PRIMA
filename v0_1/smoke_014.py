import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit
from main_014 import AppWindow
from db_selector import validate_la_prima_database
import core

app = QApplication([])
w = AppWindow()
w.resize(1536, 960)
w.show_settings()
w.show()
app.processEvents()

choose = w.findChild(QPushButton, 'ChooseDatabaseButton')
default = w.findChild(QPushButton, 'DefaultDatabaseButton')
path_field = w.findChild(QLineEdit, 'DatabasePathField')
if choose is None or default is None or path_field is None:
    raise SystemExit('FAIL: database selector controls missing')
if not path_field.text():
    raise SystemExit('FAIL: active database path not displayed')

ok, error = validate_la_prima_database(core.DB_PATH)
if not ok:
    raise SystemExit('FAIL: active database validation: ' + error)

shot = w.grab()
if shot.isNull() or not shot.save('smoke_014.png'):
    raise SystemExit('FAIL: screenshot')
print('OK 0.1.4 database chooser and active database validation')
