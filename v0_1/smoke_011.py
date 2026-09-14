import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QPixmap
import resources_rc
from main_011 import AppWindow, UI_LOGO

app = QApplication([])
logo = QPixmap(UI_LOGO)
if logo.isNull():
    raise SystemExit('FAIL: Qt embedded logo is null')

w = AppWindow()
w.resize(1536, 960)
w.show()
app.processEvents()

if not getattr(w, '_ui_logo_ok', False):
    raise SystemExit('FAIL: sidebar logo was not initialized')
if w.bg.logo.isNull():
    raise SystemExit('FAIL: background logo is null')

shot = w.grab()
if shot.isNull() or not shot.save('smoke_011.png'):
    raise SystemExit('FAIL: unable to save UI smoke screenshot')

print(f'OK logo={logo.width()}x{logo.height()} screenshot={shot.width()}x{shot.height()}')
w.close()
