import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit, QTextEdit,
    QLabel, QPushButton, QMessageBox
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
    """Add an explicit fiscal customer type and infer a sensible value for existing records."""
    conn = sqlite3.connect(core.DB_PATH)
    cols = _columns(conn, 'clients')
    if 'subject_type' not in cols:
        conn.execute("ALTER TABLE clients ADD COLUMN subject_type TEXT DEFAULT 'PF'")
        conn.execute("UPDATE clients SET subject_type='PA' WHERE UPPER(COALESCE(transmission_format,''))='FPA12'")
        conn.execute("UPDATE clients SET subject_type='PG' WHERE COALESCE(vat_number,'')<>'' AND UPPER(COALESCE(transmission_format,''))<>'FPA12'")
        conn.execute("UPDATE clients SET subject_type='PF' WHERE COALESCE(vat_number,'')='' AND UPPER(COALESCE(transmission_format,''))<>'FPA12'")
    conn.commit()
    conn.close()


class AppWindow(AppWindow018):
    def __init__(self, current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")

    # ---------- CLIENTI: TIPO FISCALE ESPLICITO ----------
    def show_clients(self):
        self.set_nav('Clienti')
        p = TablePage(self, 'Clienti', 'Anagrafica clienti con tipo fiscale e dati FatturaPA / SDI')
        p.add_btn('Nuovo', lambda: self.client_dialog(), True)
        p.add_btn('Modifica', lambda: self.client_dialog(p.selected_id()))
        p.add_btn('Elimina', lambda: self.delete_client(p))
        p.add_btn('Stampa situazione PDF', self.print_clients)
        rows = self.db.q('SELECT * FROM clients ORDER BY name')
        type_labels = {'PF': 'Persona fisica', 'PG': 'Impresa / Professionista', 'PA': 'Pubblica Amministrazione'}
        p.populate(
            ['ID','Cliente','Tipo','Telefono','Email','P.IVA','Codice Fiscale','Formato','Codice SDI','PEC'],
            [[
                r['id'], r['name'], type_labels.get(r['subject_type'] or 'PF', r['subject_type'] or 'PF'),
                r['phone'], r['email'], r['vat_number'], r['tax_code'], r['transmission_format'],
                r['recipient_code'], r['pec']
            ] for r in rows]
        )
        p.table.doubleClicked.connect(lambda: self.client_dialog(p.selected_id()))
        self._set_page(p)

    def client_dialog(self, cid=None):
        d = BaseDialog('Cliente - Anagrafica e dati fiscali', self)
        d.resize(780, 800)
        root = QVBoxLayout(d)
        form = QFormLayout()

        subject = QComboBox()
        subject.addItem('Persona fisica / privato (senza Partita IVA)', 'PF')
        subject.addItem('Impresa / professionista (con Partita IVA)', 'PG')
        subject.addItem('Pubblica Amministrazione', 'PA')

        name = QLineEdit(); phone = QLineEdit(); email = QLineEdit()
        vat = QLineEdit(); tax = QLineEdit()
        fmt = QComboBox(); fmt.addItem('Privato / Impresa - FPR12','FPR12'); fmt.addItem('Pubblica Amministrazione - FPA12','FPA12')
        recipient = QLineEdit(); pec = QLineEdit(); address = QLineEdit(); civic = QLineEdit()
        cap = QLineEdit(); city = QLineEdit(); prov = QLineEdit(); country = QLineEdit('IT')
        notes = QTextEdit(); notes.setFixedHeight(70)

        vat.setPlaceholderText('Non obbligatoria per persona fisica; 11 cifre per soggetti IVA')
        tax.setPlaceholderText('Obbligatorio per persona fisica quando si genera FatturaPA')
        recipient.setPlaceholderText('7 caratteri FPR12; 6 per PA; vuoto = 0000000')
        country.setMaxLength(2); prov.setMaxLength(2); cap.setMaxLength(5)

        fields = [
            ('Tipo cliente', subject), ('Nome / Ragione sociale', name), ('Telefono', phone), ('Email', email),
            ('Partita IVA', vat), ('Codice Fiscale', tax), ('Tipo destinatario', fmt),
            ('Codice Destinatario / Ufficio', recipient), ('PEC destinatario', pec),
            ('Indirizzo fiscale', address), ('Numero civico', civic), ('CAP', cap),
            ('Comune', city), ('Provincia', prov), ('Nazione', country), ('Note', notes)
        ]
        for label, widget in fields:
            form.addRow(label, widget)
        root.addLayout(form)

        note = QLabel(
            'FatturaPA: per una persona fisica italiana la Partita IVA NON è obbligatoria. '
            'È però necessario il Codice Fiscale. Per imprese/professionisti viene utilizzata la Partita IVA; '
            'per la Pubblica Amministrazione serve il codice ufficio a 6 caratteri.'
        )
        note.setWordWrap(True)
        note.setStyleSheet('color:#5D6D7E;font-size:11px;')
        root.addWidget(note)

        if cid:
            r = self.db.one('SELECT * FROM clients WHERE id=?', (cid,))
            inferred = r['subject_type'] or ('PA' if (r['transmission_format'] or '').upper() == 'FPA12' else ('PG' if r['vat_number'] else 'PF'))
            subject.setCurrentIndex(max(0, subject.findData(inferred)))
            name.setText(r['name'] or ''); phone.setText(r['phone'] or ''); email.setText(r['email'] or '')
            vat.setText(r['vat_number'] or ''); tax.setText(r['tax_code'] or '')
            fmt.setCurrentIndex(max(0, fmt.findData(r['transmission_format'] or 'FPR12')))
            recipient.setText(r['recipient_code'] or ''); pec.setText(r['pec'] or '')
            address.setText(r['fiscal_address'] or ''); civic.setText(r['street_number'] or '')
            cap.setText(r['zip_code'] or ''); city.setText(r['city'] or ''); prov.setText(r['province'] or '')
            country.setText(r['country'] or 'IT'); notes.setPlainText(r['notes'] or '')

        def sync_subject_type():
            st = subject.currentData()
            if st == 'PA':
                fmt.setCurrentIndex(max(0, fmt.findData('FPA12')))
                vat.setPlaceholderText('Partita IVA ente, se prevista')
                tax.setPlaceholderText('Codice Fiscale ente')
            elif st == 'PF':
                fmt.setCurrentIndex(max(0, fmt.findData('FPR12')))
                vat.setPlaceholderText('Non obbligatoria per persona fisica')
                tax.setPlaceholderText('Codice Fiscale obbligatorio per FatturaPA')
            else:
                fmt.setCurrentIndex(max(0, fmt.findData('FPR12')))
                vat.setPlaceholderText('Partita IVA - 11 cifre')
                tax.setPlaceholderText('Codice Fiscale, se disponibile')

        subject.currentIndexChanged.connect(sync_subject_type)
        sync_subject_type()

        row = QHBoxLayout(); row.addStretch()
        cancel = QPushButton('Annulla'); save = QPushButton('Salva')
        save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:9px 18px;border-radius:6px;')
        row.addWidget(cancel); row.addWidget(save); root.addLayout(row)
        cancel.clicked.connect(d.reject)

        def do_save():
            if not name.text().strip():
                return QMessageBox.warning(d, 'Cliente', 'Inserisci nome o ragione sociale.')
            st = subject.currentData()
            fmt_value = 'FPA12' if st == 'PA' else 'FPR12'
            code = recipient.text().strip().upper()
            if code:
                expected = 6 if fmt_value == 'FPA12' else 7
                if len(code) != expected:
                    return QMessageBox.warning(d, 'Codice destinatario', f'Il codice deve avere {expected} caratteri per {fmt_value}.')
            vals = (
                name.text().strip(), phone.text().strip(), email.text().strip(), notes.toPlainText().strip(),
                digits(vat.text()), alnum(tax.text()), fmt_value, code, pec.text().strip(), address.text().strip(),
                civic.text().strip(), cap.text().strip(), city.text().strip(), prov.text().strip().upper(),
                country.text().strip().upper() or 'IT', st
            )
            if cid:
                self.db.ex('''UPDATE clients SET name=?,phone=?,email=?,notes=?,vat_number=?,tax_code=?,transmission_format=?,recipient_code=?,pec=?,fiscal_address=?,street_number=?,zip_code=?,city=?,province=?,country=?,subject_type=? WHERE id=?''', vals + (cid,))
            else:
                self.db.ex('''INSERT INTO clients(name,phone,email,notes,vat_number,tax_code,transmission_format,recipient_code,pec,fiscal_address,street_number,zip_code,city,province,country,subject_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', vals)
            d.accept(); self.show_clients()

        save.clicked.connect(do_save)
        d.exec()

    def _fatturapa_context(self, iid):
        seller, customer, invoice, items, progressivo = super()._fatturapa_context(iid)
        row = self.db.one('''SELECT c.subject_type FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''', (iid,))
        customer['subject_type'] = (row['subject_type'] if row else '') or 'PF'
        return seller, customer, invoice, items, progressivo

    def export_invoice_fatturapa(self, iid):
        if not iid:
            return QMessageBox.information(self, 'FatturaPA', 'Seleziona prima una fattura.')
        try:
            seller, customer, invoice, items, progressivo = self._fatturapa_context(iid)
        except Exception as exc:
            return QMessageBox.critical(self, 'FatturaPA', str(exc))

        st = (customer.get('subject_type') or 'PF').upper()
        cf = alnum(customer.get('tax_code'))
        vat = digits(customer.get('vat_number'))
        country = (customer.get('country') or 'IT').upper()

        # Crucial rule: an Italian private individual does not need a VAT number.
        # For FatturaPA we require the fiscal code instead.
        if st == 'PF' and country == 'IT':
            if not cf:
                return QMessageBox.warning(
                    self, 'FatturaPA - Persona fisica',
                    'Per una persona fisica la Partita IVA NON è richiesta.\n\n'
                    'Inserisci però il Codice Fiscale del cliente nell’anagrafica e riprova.'
                )
            if len(cf) != 16:
                return QMessageBox.warning(
                    self, 'FatturaPA - Persona fisica',
                    'Per una persona fisica italiana il Codice Fiscale deve essere di 16 caratteri.\n\n'
                    'La Partita IVA non è richiesta.'
                )
        elif st == 'PG' and country == 'IT' and not vat:
            return QMessageBox.warning(
                self, 'FatturaPA - Impresa / Professionista',
                'Per il cliente selezionato come Impresa / Professionista inserisci la Partita IVA.'
            )

        # The inherited exporter performs all remaining FatturaPA checks and writes the XML.
        return super().export_invoice_fatturapa(iid)


__all__ = [
    'AppWindow', 'APP_VERSION', 'ensure_customer_type_schema',
    'ensure_company_schema', 'ensure_fatturapa_schema', 'ensure_users_schema'
]
