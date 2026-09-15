import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit, QTextEdit,
    QLabel, QPushButton, QMessageBox, QDialog
)

import core
from main_018 import AppWindow as AppWindow018
from main_018 import ensure_company_schema, ensure_fatturapa_schema, ensure_users_schema
from core import TablePage, BaseDialog, RED
from fatturapa_017 import digits, alnum

APP_VERSION = '0.1.9'


def _columns(conn, table):
    return {r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}


def ensure_customer_type_schema():
    conn = sqlite3.connect(core.DB_PATH)
    cols = _columns(conn, 'clients')
    if 'subject_type' not in cols:
        conn.execute("ALTER TABLE clients ADD COLUMN subject_type TEXT DEFAULT 'PF'")
        conn.execute("UPDATE clients SET subject_type='PA' WHERE UPPER(COALESCE(transmission_format,''))='FPA12'")
        conn.execute("UPDATE clients SET subject_type='PG' WHERE COALESCE(vat_number,'')<>'' AND UPPER(COALESCE(transmission_format,''))<>'FPA12'")
        conn.execute("UPDATE clients SET subject_type='PF' WHERE COALESCE(vat_number,'')='' AND UPPER(COALESCE(transmission_format,''))<>'FPA12'")
    conn.commit(); conn.close()


class AppWindow(AppWindow018):
    def __init__(self, current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")

    def _fatturapa_context(self, iid):
        seller, customer, invoice, items, progressivo = super()._fatturapa_context(iid)
        row = self.db.one('''SELECT c.subject_type FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''', (iid,))
        customer['subject_type'] = (row['subject_type'] if row else '') or 'PF'
        return seller, customer, invoice, items, progressivo

    def _choose_invoice_subject_type(self, iid):
        row = self.db.one('''SELECT c.id client_id,c.name,c.subject_type,c.vat_number,c.tax_code
                             FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id
                             JOIN clients c ON c.id=v.client_id WHERE i.id=?''', (iid,))
        if not row:
            return None

        d = BaseDialog('Tipo destinatario FatturaPA', self)
        d.setMinimumWidth(540)
        root = QVBoxLayout(d)
        title = QLabel('A chi stai fatturando?')
        title.setStyleSheet('font-size:20px;font-weight:900;color:#10233B;')
        root.addWidget(title)
        info = QLabel(f"Cliente: {row['name']}\nScegli il tipo fiscale da usare per questa esportazione FatturaPA.")
        info.setWordWrap(True); info.setStyleSheet('color:#405468;'); root.addWidget(info)

        combo = QComboBox()
        combo.setObjectName('InvoiceSubjectTypeCombo')
        combo.addItem('Persona fisica', 'PF')
        combo.addItem('Società / Impresa / Professionista', 'PG')
        current = (row['subject_type'] or '').upper()
        if current not in ('PF','PG'):
            current = 'PG' if row['vat_number'] else 'PF'
        combo.setCurrentIndex(max(0, combo.findData(current)))
        root.addWidget(combo)

        hint = QLabel()
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#5D6D7E;font-size:11px;')
        root.addWidget(hint)

        def refresh_hint():
            if combo.currentData() == 'PF':
                hint.setText('Persona fisica: la Partita IVA NON è obbligatoria. Per l’XML FatturaPA italiano viene usato il Codice Fiscale del cliente.')
            else:
                hint.setText('Società / Impresa / Professionista: per l’XML FatturaPA è richiesta la Partita IVA del cliente.')
        combo.currentIndexChanged.connect(refresh_hint); refresh_hint()

        buttons = QHBoxLayout(); buttons.addStretch()
        cancel = QPushButton('Annulla'); ok = QPushButton('Continua')
        ok.setStyleSheet(f'background:{RED};color:white;font-weight:800;padding:9px 18px;border-radius:6px;')
        cancel.clicked.connect(d.reject); ok.clicked.connect(d.accept)
        buttons.addWidget(cancel); buttons.addWidget(ok); root.addLayout(buttons)
        if d.exec() != QDialog.Accepted:
            return None

        selected = combo.currentData()
        self.db.ex('UPDATE clients SET subject_type=? WHERE id=?', (selected, row['client_id']))
        return selected

    def export_invoice_fatturapa(self, iid):
        if not iid:
            return QMessageBox.information(self, 'FatturaPA', 'Seleziona prima una fattura.')

        selected_type = self._choose_invoice_subject_type(iid)
        if selected_type is None:
            return

        try:
            seller, customer, invoice, items, progressivo = self._fatturapa_context(iid)
        except Exception as exc:
            return QMessageBox.critical(self, 'FatturaPA', str(exc))

        cf = alnum(customer.get('tax_code'))
        vat = digits(customer.get('vat_number'))
        country = (customer.get('country') or 'IT').upper()

        if selected_type == 'PF' and country == 'IT':
            if not cf:
                return QMessageBox.warning(
                    self, 'FatturaPA - Persona fisica',
                    'Hai scelto Persona fisica.\n\nLa Partita IVA NON è obbligatoria. '
                    'Inserisci però il Codice Fiscale del cliente nell’anagrafica e riprova.'
                )
            if len(cf) != 16:
                return QMessageBox.warning(
                    self, 'FatturaPA - Persona fisica',
                    'Hai scelto Persona fisica.\n\nIl Codice Fiscale italiano deve avere 16 caratteri. '
                    'La Partita IVA non è richiesta.'
                )
        elif selected_type == 'PG' and country == 'IT' and not vat:
            return QMessageBox.warning(
                self, 'FatturaPA - Società / Impresa',
                'Hai scelto Società / Impresa / Professionista.\n\nInserisci la Partita IVA del cliente prima di esportare la FatturaPA.'
            )

        return super().export_invoice_fatturapa(iid)


__all__ = [
    'AppWindow', 'APP_VERSION', 'ensure_customer_type_schema',
    'ensure_company_schema', 'ensure_fatturapa_schema', 'ensure_users_schema'
]
