import sys
from PySide6.QtWidgets import QApplication
from core import DB
import main_013 as impl

_original_schema_migration = impl.ensure_schema_013

def safe_schema_migration():
    # On a first install, create the base 0.1 tables before applying 0.1.3 migrations.
    base = DB()
    try:
        base.conn.close()
    except Exception:
        pass
    _original_schema_migration()

impl.ensure_schema_013 = safe_schema_migration
AppWindow = impl.AppWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('LA PRIMA Garage Manager 0.1.3')
    w = AppWindow()
    w.show()
    sys.exit(app.exec())
