import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtWidgets import QApplication
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
if w.bg.pixmap.isNull():
    raise SystemExit('FAIL: dashboard background pixmap is null')
if not hasattr(w.bg, 'reload_from_settings'):
    raise SystemExit('FAIL: selectable background support is missing')

w.bg.set_opacity_percent(61)
app.processEvents()
shot = w.grab()
if shot.isNull() or not shot.save('smoke_011.png'):
    raise SystemExit('FAIL: unable to save UI smoke screenshot')

print(f'OK embedded-logo={logo.width()}x{logo.height()} background={w.bg.pixmap.width()}x{w.bg.pixmap.height()} screenshot={shot.width()}x{shot.height()}')
w.hide()
w.deleteLater()
app.quit()
