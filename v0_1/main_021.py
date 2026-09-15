import hashlib
import sqlite3

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QMessageBox, QInputDialog, QGroupBox
)

import core
from main_020 import (
    AppWindow as AppWindow020, ensure_final_schema, ensure_customer_type_schema,
    ensure_company_schema, ensure_fatturapa_schema, ensure_users_schema,
)
from main_015 import UserLoginDialog as UserLoginDialog015, UserEditDialog, _password_hash
from core import GlassFrame, RED

APP_VERSION = '0.1.11'
RECOVERY_SETTING = 'password_recovery_hash'


def _recovery_hash(code):
    return hashlib.sha256((code or '').strip().encode('utf-8')).hexdigest() if (code or '').strip() else ''


def ensure_recovery_schema():
    # The recovery secret is stored only as a hash in the currently selected database.
    conn = sqlite3.connect(core.DB_PATH)
    conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (RECOVERY_SETTING, ''))
    conn.commit(); conn.close()


def set_recovery_code(code):
    code = (code or '').strip()
    if len(code) < 6:
        raise ValueError('Il codice di recupero deve contenere almeno 6 caratteri.')
    conn = sqlite3.connect(core.DB_PATH)
    conn.execute(
        'INSERT INTO settings(key,value) VALUES(?,?) '
        'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
        (RECOVERY_SETTING, _recovery_hash(code))
    )
    conn.commit(); conn.close()


def clear_recovery_code():
    conn = sqlite3.connect(core.DB_PATH)
    conn.execute(
        'INSERT INTO settings(key,value) VALUES(?,?) '
        'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
        (RECOVERY_SETTING, '')
    )
    conn.commit(); conn.close()


def recovery_is_configured():
    conn = sqlite3.connect(core.DB_PATH)
    try:
        row = conn.execute('SELECT value FROM settings WHERE key=?', (RECOVERY_SETTING,)).fetchone()
        return bool(row and row[0])
    finally:
        conn.close()


def verify_recovery_code(code):
    conn = sqlite3.connect(core.DB_PATH)
    try:
        row = conn.execute('SELECT value FROM settings WHERE key=?', (RECOVERY_SETTING,)).fetchone()
        expected = row[0] if row else ''
        return bool(expected) and _recovery_hash(code) == expected
    finally:
        conn.close()


def reset_user_password(user_id, new_password):
    conn = sqlite3.connect(core.DB_PATH)
    try:
        conn.execute('UPDATE users SET password_hash=? WHERE id=?', (_password_hash(new_password), user_id))
        conn.commit()
    finally:
        conn.close()


class NewPasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Reimposta password')
        self.setMinimumWidth(440)
        root = QVBoxLayout(self)
        title = QLabel(f'Reimposta password per {username}')
        title.setStyleSheet('font-size:18px;font-weight:850;color:#10233B;')
        root.addWidget(title)
        form = QFormLayout()
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText('Puoi lasciare vuoto per accesso senza password')
        self.confirm.setPlaceholderText('Ripeti la nuova password')
        form.addRow('Nuova password', self.password)
        form.addRow('Conferma password', self.confirm)
        root.addLayout(form)
        note = QLabel('La password può essere vuota. In questo caso l’utente potrà entrare senza password.')
        note.setWordWrap(True); note.setStyleSheet('color:#5D6D7E;font-size:11px;')
        root.addWidget(note)
        row = QHBoxLayout(); row.addStretch()
        cancel = QPushButton('Annulla'); save = QPushButton('Reimposta')
        save.setStyleSheet(f'background:{RED};color:white;font-weight:800;padding:9px 17px;border-radius:6px;')
        cancel.clicked.connect(self.reject); save.clicked.connect(self._accept_if_valid)
        row.addWidget(cancel); row.addWidget(save); root.addLayout(row)

    def _accept_if_valid(self):
        if self.password.text() != self.confirm.text():
            return QMessageBox.warning(self, 'Password', 'Le due password non coincidono.')
        self.accept()


class UserLoginDialog(UserLoginDialog015):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('LA PRIMA - Accesso utente / recupero password')
        forgot = QPushButton('Password dimenticata?')
        forgot.setObjectName('ForgotPasswordButton')
        forgot.setMinimumHeight(34)
        forgot.setStyleSheet('background:#E7EDF2;color:#20364C;font-weight:700;border-radius:6px;padding:7px 12px;')
        # Insert before the final database-info label.
        layout = self.layout()
        insert_at = max(0, layout.count() - 1)
        layout.insertWidget(insert_at, forgot)
        forgot.clicked.connect(self.forgot_password)

    def _authorize_existing_user_change(self, user):
        if not user or not user['password_hash']:
            return True
        password, ok = QInputDialog.getText(
            self, 'Conferma password',
            f"Per modificare l’utente {user['name']}, inserisci la password attuale:",
            QLineEdit.Password
        )
        if not ok:
            return False
        if _password_hash(password) != user['password_hash']:
            QMessageBox.warning(
                self, 'Password',
                'Password non corretta. Se non la ricordi usa “Password dimenticata?”.'
            )
            return False
        return True

    def edit_user(self):
        user = self.current()
        if not user or not self._authorize_existing_user_change(user):
            return
        d = UserEditDialog(self, user['name'])
        if d.exec() != QDialog.Accepted:
            return
        try:
            self.store.save(d.name.text(), d.password.text(), user['id'])
        except ValueError as exc:
            return QMessageBox.warning(self, 'Utente', str(exc))
        self.refresh(user['id'])

    def delete_user(self):
        user = self.current()
        if not user or not self._authorize_existing_user_change(user):
            return
        return super().delete_user()

    def forgot_password(self):
        user = self.current()
        if not user:
            return
        if not recovery_is_configured():
            return QMessageBox.warning(
                self, 'Recupero password',
                'Non è ancora stato configurato un codice di recupero.\n\n'
                'Accedi con un altro utente e vai in Impostazioni → Sicurezza e recupero password. '
                'È consigliato configurarlo subito e conservarlo in un luogo sicuro.'
            )
        code, ok = QInputDialog.getText(
            self, 'Codice di recupero',
            'Inserisci il codice di recupero del gestionale:',
            QLineEdit.Password
        )
        if not ok:
            return
        if not verify_recovery_code(code):
            return QMessageBox.warning(self, 'Recupero password', 'Codice di recupero non corretto.')
        d = NewPasswordDialog(user['name'], self)
        if d.exec() != QDialog.Accepted:
            return
        reset_user_password(user['id'], d.password.text())
        self.refresh(user['id'])
        QMessageBox.information(
            self, 'Recupero password',
            f"Password di {user['name']} reimpostata correttamente. Ora puoi accedere con la nuova password."
        )


class AppWindow(AppWindow020):
    def __init__(self, current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")
        if not recovery_is_configured():
            QTimer.singleShot(900, self._suggest_recovery_setup)

    def _suggest_recovery_setup(self):
        if recovery_is_configured():
            return
        answer = QMessageBox.question(
            self, 'Recupero password',
            'Non hai ancora impostato un codice di recupero password.\n\n'
            'Vuoi configurarlo adesso? Ti permetterà di reimpostare una password dimenticata anche senza Internet.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if answer == QMessageBox.Yes:
            self._set_recovery_code_dialog()

    def _set_recovery_code_dialog(self):
        first, ok = QInputDialog.getText(
            self, 'Codice di recupero',
            'Scegli un codice di recupero di almeno 6 caratteri:\n'
            '(conservalo fuori dal PC, ad esempio su carta o in un password manager)',
            QLineEdit.Password
        )
        if not ok:
            return False
        second, ok = QInputDialog.getText(
            self, 'Conferma codice di recupero',
            'Ripeti il codice di recupero:',
            QLineEdit.Password
        )
        if not ok:
            return False
        if first != second:
            QMessageBox.warning(self, 'Codice di recupero', 'I due codici non coincidono.')
            return False
        try:
            set_recovery_code(first)
        except ValueError as exc:
            QMessageBox.warning(self, 'Codice di recupero', str(exc))
            return False
        QMessageBox.information(
            self, 'Codice di recupero',
            'Codice di recupero salvato. Nel database viene memorizzato soltanto il suo hash, non il codice in chiaro.'
        )
        return True

    def show_settings(self):
        super().show_settings()
        page = self.stack.currentWidget()
        if not page or not page.layout():
            return
        root = page.layout()
        card = GlassFrame(220)
        box = QVBoxLayout(card)
        title = QLabel('Sicurezza e recupero password')
        title.setObjectName('PasswordRecoverySettingsTitle')
        title.setStyleSheet('font-size:19px;font-weight:850;color:#10233B;')
        box.addWidget(title)
        status = QLabel(
            'Codice di recupero configurato.' if recovery_is_configured()
            else 'Codice di recupero NON configurato.'
        )
        status.setObjectName('RecoveryStatusLabel')
        status.setStyleSheet(
            'color:#087A52;font-weight:700;' if recovery_is_configured()
            else 'color:#B45A00;font-weight:700;'
        )
        box.addWidget(status)
        info = QLabel(
            'Il codice di recupero serve soltanto se dimentichi la password di un utente. '
            'Il programma resta completamente offline: non vengono inviate email e il codice non viene caricato su Internet.'
        )
        info.setWordWrap(True); info.setStyleSheet('color:#405468;font-size:12px;')
        box.addWidget(info)
        row = QHBoxLayout()
        set_btn = QPushButton('Imposta / cambia codice di recupero')
        set_btn.setObjectName('SetRecoveryCodeButton')
        set_btn.setStyleSheet(f'background:{RED};color:white;font-weight:800;padding:9px 14px;border-radius:7px;')
        clear_btn = QPushButton('Rimuovi codice')
        clear_btn.setObjectName('ClearRecoveryCodeButton')
        clear_btn.setStyleSheet('background:#E7EDF2;color:#20364C;font-weight:700;padding:9px 14px;border-radius:7px;')
        row.addWidget(set_btn); row.addWidget(clear_btn); row.addStretch(); box.addLayout(row)

        def update_status():
            configured = recovery_is_configured()
            status.setText('Codice di recupero configurato.' if configured else 'Codice di recupero NON configurato.')
            status.setStyleSheet('color:#087A52;font-weight:700;' if configured else 'color:#B45A00;font-weight:700;')

        def set_code():
            if self._set_recovery_code_dialog():
                update_status()

        def clear_code():
            if QMessageBox.question(
                self, 'Rimuovi codice di recupero',
                'Senza codice di recupero non potrai reimpostare una password dimenticata. Continuare?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            ) == QMessageBox.Yes:
                clear_recovery_code(); update_status()

        set_btn.clicked.connect(set_code); clear_btn.clicked.connect(clear_code)
        root.insertWidget(max(0, root.count() - 1), card)


__all__ = [
    'AppWindow', 'UserLoginDialog', 'APP_VERSION', 'ensure_recovery_schema',
    'ensure_final_schema', 'ensure_customer_type_schema', 'ensure_company_schema',
    'ensure_fatturapa_schema', 'ensure_users_schema', 'set_recovery_code',
    'verify_recovery_code', 'reset_user_password', 'recovery_is_configured'
]
