from PySide6.QtGui import QPixmap
import resources_rc  # generated from resources.qrc before this script runs

p = QPixmap(':/la_prima/logo.png')
if p.isNull():
    raise SystemExit('ERROR: embedded LA PRIMA logo resource is null')
print(f'OK: embedded logo {p.width()}x{p.height()}')
