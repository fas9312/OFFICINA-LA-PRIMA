import sys
from PySide6.QtWidgets import QApplication, QDialog

from main_015 import ensure_users_schema, UserLoginDialog
from main_013 import ensure_schema_013

# Build the base/migrated schema before 0.1.6 adds fiscal fields.
ensure_users_schema()
ensure_schema_013()

from main_016 import ensure_fatturapa_schema, AppWindow, APP_VERSION

ensure_fatturapa_schema()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName(f'LA PRIMA Garage Manager {APP_VERSION}')
    login = UserLoginDialog()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)
    window = AppWindow(login.selected_user)
    window.show()
    sys.exit(app.exec())
