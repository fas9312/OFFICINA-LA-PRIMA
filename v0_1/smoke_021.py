import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import sqlite3
from PySide6.QtWidgets import QApplication, QPushButton

import core
from main_013 import ensure_schema_013
from main_021 import (
    AppWindow, UserLoginDialog, ensure_recovery_schema, ensure_final_schema,
    ensure_customer_type_schema, ensure_company_schema, ensure_fatturapa_schema,
    ensure_users_schema, set_recovery_code, verify_recovery_code,
    reset_user_password, recovery_is_configured,
)
from main_015 import _password_hash

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

# Recovery code must be stored as a hash and verified correctly.
set_recovery_code('RECUPERO-TEST-123')
if not recovery_is_configured():
    raise SystemExit('FAIL: recovery code not configured')
if not verify_recovery_code('RECUPERO-TEST-123'):
    raise SystemExit('FAIL: valid recovery code rejected')
if verify_recovery_code('CODICE-SBAGLIATO'):
    raise SystemExit('FAIL: invalid recovery code accepted')

conn = sqlite3.connect(core.DB_PATH)
row = conn.execute("SELECT id FROM users WHERE name='Utente Recupero Test'").fetchone()
if row:
    uid = row[0]
else:
    cur = conn.execute("INSERT INTO users(name,password_hash) VALUES(?,?)", ('Utente Recupero Test', _password_hash('vecchia-pass')))
    uid = cur.lastrowid
conn.commit(); conn.close()

reset_user_password(uid, 'nuova-pass')
conn = sqlite3.connect(core.DB_PATH)
hash_value = conn.execute('SELECT password_hash FROM users WHERE id=?', (uid,)).fetchone()[0]
stored_recovery = conn.execute("SELECT value FROM settings WHERE key='password_recovery_hash'").fetchone()[0]
conn.close()
if hash_value != _password_hash('nuova-pass'):
    raise SystemExit('FAIL: user password was not reset')
if stored_recovery == 'RECUPERO-TEST-123':
    raise SystemExit('FAIL: recovery code stored in clear text')

app = QApplication([])
login = UserLoginDialog()
if login.findChild(QPushButton, 'ForgotPasswordButton') is None:
    raise SystemExit('FAIL: Password dimenticata button missing')

w = AppWindow({'id': uid, 'name': 'Utente Recupero Test'})
w.show_settings(); app.processEvents()
if w.findChild(QPushButton, 'SetRecoveryCodeButton') is None:
    raise SystemExit('FAIL: recovery settings button missing')
if w.findChild(QPushButton, 'ClearRecoveryCodeButton') is None:
    raise SystemExit('FAIL: clear recovery button missing')

print('OK 0.1.11: password recovery code, reset flow and settings controls')
