import sys
from PySide6.QtWidgets import QApplication, QDialog

import core
from main_013 import ensure_schema_013
from main_020 import (
    AppWindow, APP_VERSION, ensure_final_schema, ensure_customer_type_schema,
    ensure_company_schema, ensure_fatturapa_schema, ensure_users_schema,
)
from main_015 import UserLoginDialog


def prepare_database():
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


if __name__ == '__main__':
    prepare_database()
    app = QApplication(sys.argv)
    app.setApplicationName(f'LA PRIMA Garage Manager {APP_VERSION}')
    login = UserLoginDialog()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)
    w = AppWindow(login.selected_user)
    w.show()
    sys.exit(app.exec())
