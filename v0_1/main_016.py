import sys, sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QComboBox, QLineEdit, QTextEdit, QMessageBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QAbstractItemView
)

import core
from main_015 import AppWindow as AppWindow015, UserLoginDialog, ensure_users_schema
from core import TablePage, BaseDialog, GlassFrame, RED
from fatturapa import write_xml, validate_context, NATURE_CODES, digits, alnum

APP_VERSION = '0.1.6'


def _columns(conn, table):
    return {r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}


def ensure_fatturapa_schema():
    conn = sqlite3.connect(core.DB_PATH)
    client_columns = {
        'vat_number': "TEXT DEFAULT ''",
        'tax_code': "TEXT DEFAULT ''",
        'transmission_format': "TEXT DEFAULT 'FPR12'",
        'recipient_code': "TEXT DEFAULT ''",
        'pec': "TEXT DEFAULT ''",
        'fiscal_address': "TEXT DEFAULT ''",
        'street_number': "TEXT DEFAULT ''",
        'zip_code': "TEXT DEFAULT ''",
        'city': "TEXT DEFAULT ''",
        'province': "TEXT DEFAULT ''",
        'country': "TEXT DEFAULT 'IT'",
    }
    cols = _columns(conn, 'clients')
    for name, ddl in client_columns.items():
        if name not in cols:
            conn.execute(f'ALTER TABLE clients ADD COLUMN {name} {ddl}')

    invoice_cols = _columns(conn, 'invoices')
    if 'sdi_document_type' not in invoice_cols:
        conn.execute("ALTER TABLE invoices ADD COLUMN sdi_document_type TEXT DEFAULT 'TD01'")

    item_cols = _columns(conn, 'invoice_items')
    if 'nature' not in item_cols:
        conn.execute("ALTER TABLE invoice_items ADD COLUMN nature TEXT DEFAULT ''")

    defaults = {
        'sdi_business_name': '',
        'sdi_vat_number': '',
        'sdi_tax_code': '',
        'sdi_tax_regime': 'RF01',
        'sdi_address': '',
        'sdi_street_number': '',
        'sdi_zip_code': '',
        'sdi_city': '',
        'sdi_province': '',
        'sdi_country': 'IT',
        'sdi_email': '',
        'sdi_phone': '',
    }
    for key, value in defaults.items():
        conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (key, value))
    conn.commit(); conn.close()


class AppWindow(AppWindow015):
    def __init__(self, current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")

    # ---------- ANAGRAFICA CLIENTE CON DATI FISCALI / SDI ----------
    def show_clients(self):
        self.set_nav('Clienti')
        p = TablePage(self, 'Clienti', 'Anagrafica clienti con dati fiscali per FatturaPA / SDI')
        p.add_btn('Nuovo', lambda: self.client_dialog(), True)
        p.add_btn('Modifica', lambda: self.client_dialog(p.selected_id()))
        p.add_btn('Elimina', lambda: self.delete_client(p))
        p.add_btn('Stampa situazione PDF', self.print_clients)
        rows = self.db.q('SELECT * FROM clients ORDER BY name')
        p.populate(
            ['ID','Cliente','Telefono','Email','P.IVA','Codice Fiscale','Formato','Codice SDI','PEC'],
            [[r['id'],r['name'],r['phone'],r['email'],r['vat_number'],r['tax_code'],r['transmission_format'],r['recipient_code'],r['pec']] for r in rows]
        )
        p.table.doubleClicked.connect(lambda: self.client_dialog(p.selected_id()))
        self._set_page(p)

    def client_dialog(self, cid=None):
        d = BaseDialog('Cliente - Anagrafica e dati fiscali', self)
        d.resize(760, 760)
        root = QVBoxLayout(d)
        form = QFormLayout()
        name=QLineEdit(); phone=QLineEdit(); email=QLineEdit()
        vat=QLineEdit(); tax=QLineEdit(); fmt=QComboBox(); fmt.addItem('Privato / Impresa - FPR12','FPR12'); fmt.addItem('Pubblica Amministrazione - FPA12','FPA12')
        recipient=QLineEdit(); pec=QLineEdit(); address=QLineEdit(); civic=QLineEdit(); cap=QLineEdit(); city=QLineEdit(); prov=QLineEdit(); country=QLineEdit('IT'); notes=QTextEdit(); notes.setFixedHeight(70)
        recipient.setPlaceholderText('7 caratteri per FPR12; 6 per PA; lascia vuoto per 0000000')
        vat.setPlaceholderText('11 cifre per soggetti IVA italiani')
        tax.setPlaceholderText('Codice fiscale cliente')
        country.setMaxLength(2); prov.setMaxLength(2); cap.setMaxLength(5)
        fields = [
            ('Nome / Ragione sociale',name),('Telefono',phone),('Email',email),
            ('Partita IVA',vat),('Codice Fiscale',tax),('Tipo destinatario',fmt),
            ('Codice Destinatario / Ufficio',recipient),('PEC destinatario',pec),
            ('Indirizzo fiscale',address),('Numero civico',civic),('CAP',cap),
            ('Comune',city),('Provincia',prov),('Nazione',country),('Note',notes)
        ]
        for label, widget in fields: form.addRow(label, widget)
        root.addLayout(form)
        note=QLabel('Per esportare un XML FatturaPA/SDI, i dati fiscali obbligatori del cliente devono essere completi. Per privati/B2B senza codice destinatario il programma usa 0000000; per PA serve il codice ufficio a 6 caratteri.')
        note.setWordWrap(True); note.setStyleSheet('color:#5D6D7E;font-size:11px;'); root.addWidget(note)

        if cid:
            r=self.db.one('SELECT * FROM clients WHERE id=?',(cid,))
            name.setText(r['name'] or ''); phone.setText(r['phone'] or ''); email.setText(r['email'] or '')
            vat.setText(r['vat_number'] or ''); tax.setText(r['tax_code'] or '')
            fmt.setCurrentIndex(max(0,fmt.findData(r['transmission_format'] or 'FPR12')))
            recipient.setText(r['recipient_code'] or ''); pec.setText(r['pec'] or '')
            address.setText(r['fiscal_address'] or ''); civic.setText(r['street_number'] or '')
            cap.setText(r['zip_code'] or ''); city.setText(r['city'] or ''); prov.setText(r['province'] or '')
            country.setText(r['country'] or 'IT'); notes.setPlainText(r['notes'] or '')

        row=QHBoxLayout(); row.addStretch(); cancel=QPushButton('Annulla'); save=QPushButton('Salva'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:9px 18px;border-radius:6px;'); row.addWidget(cancel); row.addWidget(save); root.addLayout(row)
        cancel.clicked.connect(d.reject)

        def do_save():
            if not name.text().strip():
                return QMessageBox.warning(d,'Cliente','Inserisci nome o ragione sociale.')
            fmt_value=fmt.currentData()
            code=recipient.text().strip().upper()
            if code:
                expected=6 if fmt_value=='FPA12' else 7
                if len(code)!=expected:
                    return QMessageBox.warning(d,'Codice destinatario',f'Il codice deve avere {expected} caratteri per {fmt_value}.')
            vals=(name.text().strip(),phone.text().strip(),email.text().strip(),notes.toPlainText().strip(),digits(vat.text()),alnum(tax.text()),fmt_value,code,pec.text().strip(),address.text().strip(),civic.text().strip(),cap.text().strip(),city.text().strip(),prov.text().strip().upper(),country.text().strip().upper() or 'IT')
            if cid:
                self.db.ex('''UPDATE clients SET name=?,phone=?,email=?,notes=?,vat_number=?,tax_code=?,transmission_format=?,recipient_code=?,pec=?,fiscal_address=?,street_number=?,zip_code=?,city=?,province=?,country=? WHERE id=?''', vals+(cid,))
            else:
                self.db.ex('''INSERT INTO clients(name,phone,email,notes,vat_number,tax_code,transmission_format,recipient_code,pec,fiscal_address,street_number,zip_code,city,province,country) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', vals)
            d.accept(); self.show_clients()
        save.clicked.connect(do_save); d.exec()

    # ---------- IMPOSTAZIONI FISCALI OFFICINA ----------
    def show_settings(self):
        super().show_settings()
        page=self.stack.currentWidget()
        if not page or not page.layout(): return
        root=page.layout()
        card=GlassFrame(220); box=QVBoxLayout(card)
        title=QLabel('FatturaPA / Sistema di Interscambio (SDI)'); title.setStyleSheet('font-size:19px;font-weight:800;color:#10233B;'); box.addWidget(title)
        intro=QLabel('Inserisci qui i dati fiscali reali dell’officina. Questi valori vengono usati per creare l’XML FatturaPA. Prima del primo utilizzo reale verifica i dati con il commercialista.'); intro.setWordWrap(True); intro.setStyleSheet('color:#405468;'); box.addWidget(intro)
        form=QFormLayout(); widgets={}
        specs=[
            ('sdi_business_name','Ragione sociale esatta'),('sdi_vat_number','Partita IVA'),('sdi_tax_code','Codice Fiscale'),('sdi_tax_regime','Regime fiscale (es. RF01)'),
            ('sdi_address','Indirizzo'),('sdi_street_number','Numero civico'),('sdi_zip_code','CAP'),('sdi_city','Comune'),('sdi_province','Provincia'),('sdi_country','Nazione'),
            ('sdi_email','Email'),('sdi_phone','Telefono')
        ]
        for key,label in specs:
            w=QLineEdit(self.db.setting(key)); widgets[key]=w; form.addRow(label,w)
        widgets['sdi_country'].setText(widgets['sdi_country'].text() or 'IT'); widgets['sdi_country'].setMaxLength(2); widgets['sdi_province'].setMaxLength(2); widgets['sdi_zip_code'].setMaxLength(5)
        box.addLayout(form)
        save=QPushButton('Salva dati fiscali FatturaPA'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:9px 14px;border-radius:7px;'); box.addWidget(save,0,Qt.AlignLeft)
        foot=QLabel('L’app genera il file XML nel formato FPR12 per privati/imprese e FPA12 per Pubblica Amministrazione. L’invio allo SDI non è automatico: il file può essere consegnato al commercialista o caricato nei canali abilitati.'); foot.setWordWrap(True); foot.setStyleSheet('color:#607487;font-size:11px;'); box.addWidget(foot)

        def store():
            for key,w in widgets.items(): self.db.set_setting(key,w.text().strip())
            QMessageBox.information(self,'FatturaPA','Dati fiscali salvati.')
        save.clicked.connect(store)
        root.insertWidget(max(0,root.count()-1),card)

    # ---------- FATTURE / FATTURAPA ----------
    def show_invoices(self):
        self.set_nav('Fatture')
        p=TablePage(self,'Fatture','Fatture a righe con PDF, XML gestionale e FatturaPA / SDI')
        p.add_btn('Nuova',lambda:self.invoice_dialog(),True)
        p.add_btn('Modifica',lambda:self.invoice_dialog(p.selected_id()))
        p.add_btn('Elimina',lambda:self.delete_invoice(p))
        p.add_btn('Stampa PDF',lambda:self.print_invoice_selected(p.selected_id()))
        p.add_btn('Dati FatturaPA',lambda:self.fatturapa_options_dialog(p.selected_id()))
        p.add_btn('Esporta FatturaPA/SDI',lambda:self.export_invoice_fatturapa(p.selected_id()))
        p.add_btn('XML gestionale',lambda:self.export_invoice_xml(p.selected_id()))
        p.add_btn('Stampa situazione PDF',self.print_invoices)
        rows=self.db.q('''SELECT i.*,v.plate,c.name client FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY i.id DESC''')
        p.populate(['ID','Numero','Data','Targa','Cliente','Stato','Tipo SDI','Totale lordo €','Note'],[[r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],r['sdi_document_type'] or 'TD01',f"{r['total']:.2f}",r['notes']] for r in rows])
        p.table.doubleClicked.connect(lambda:self.invoice_dialog(p.selected_id())); self._set_page(p)

    def fatturapa_options_dialog(self, iid):
        if not iid: return QMessageBox.information(self,'FatturaPA','Seleziona prima una fattura.')
        inv=self.db.one('SELECT * FROM invoices WHERE id=?',(iid,))
        if not inv: return
        zero=self.db.q('SELECT id,description,vat_rate,nature FROM invoice_items WHERE invoice_id=? AND ABS(vat_rate)<0.0001 ORDER BY id',(iid,))
        d=BaseDialog('Dati FatturaPA',self); d.setMinimumWidth(650); root=QVBoxLayout(d); form=QFormLayout(); doc=QComboBox(); doc.setEditable(True)
        for code,label in [('TD01','Fattura'),('TD04','Nota di credito'),('TD05','Nota di debito'),('TD24','Fattura differita'),('TD25','Fattura differita triangolare')]: doc.addItem(f'{code} - {label}',code)
        current=inv['sdi_document_type'] or 'TD01'; idx=doc.findData(current)
        if idx>=0: doc.setCurrentIndex(idx)
        else: doc.setEditText(current)
        form.addRow('Tipo documento',doc); root.addLayout(form)
        nature_widgets=[]
        if zero:
            lab=QLabel('Righe con IVA 0%: seleziona il codice Natura previsto per l’operazione.'); lab.setWordWrap(True); root.addWidget(lab)
            for row in zero:
                combo=QComboBox(); combo.addItem('— Seleziona Natura —','')
                for code in sorted(NATURE_CODES): combo.addItem(code,code)
                combo.setCurrentIndex(max(0,combo.findData(row['nature'] or '')))
                formrow=QHBoxLayout(); desc=QLabel(row['description']); desc.setWordWrap(True); formrow.addWidget(desc,1); formrow.addWidget(combo); root.addLayout(formrow); nature_widgets.append((row['id'],combo))
        else:
            ok=QLabel('Questa fattura non contiene righe IVA 0%: nessun codice Natura necessario.'); ok.setStyleSheet('color:#087A52;'); root.addWidget(ok)
        row=QHBoxLayout(); row.addStretch(); cancel=QPushButton('Annulla'); save=QPushButton('Salva'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); row.addWidget(cancel); row.addWidget(save); root.addLayout(row); cancel.clicked.connect(d.reject)
        def do_save():
            raw=doc.currentData() if doc.currentData() else doc.currentText().split(' - ')[0].strip().upper()
            if not raw.startswith('TD') or len(raw)!=4: return QMessageBox.warning(d,'FatturaPA','Tipo documento non valido (es. TD01).')
            self.db.ex('UPDATE invoices SET sdi_document_type=? WHERE id=?',(raw,iid))
            for item_id,combo in nature_widgets: self.db.ex('UPDATE invoice_items SET nature=? WHERE id=?',(combo.currentData() or '',item_id))
            d.accept(); self.show_invoices()
        save.clicked.connect(do_save); d.exec()

    def _fatturapa_context(self, iid):
        inv=self.db.one('''SELECT i.*,v.plate,v.brand,v.model,c.id client_id,c.name client,c.vat_number,c.tax_code,c.transmission_format,c.recipient_code,c.pec,c.fiscal_address,c.street_number,c.zip_code,c.city,c.province,c.country FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''',(iid,))
        if not inv: raise ValueError('Fattura non trovata.')
        rows=self.db.q('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(iid,))
        seller={
            'business_name':self.db.setting('sdi_business_name') or self.db.setting('name'),
            'vat_number':self.db.setting('sdi_vat_number'),'tax_code':self.db.setting('sdi_tax_code'),'tax_regime':self.db.setting('sdi_tax_regime') or 'RF01',
            'address':self.db.setting('sdi_address'),'street_number':self.db.setting('sdi_street_number'),'zip_code':self.db.setting('sdi_zip_code'),'city':self.db.setting('sdi_city'),
            'province':self.db.setting('sdi_province'),'country':self.db.setting('sdi_country') or 'IT','email':self.db.setting('sdi_email'),'phone':self.db.setting('sdi_phone')
        }
        customer={'name':inv['client'],'vat_number':inv['vat_number'],'tax_code':inv['tax_code'],'transmission_format':inv['transmission_format'] or 'FPR12','recipient_code':inv['recipient_code'],'pec':inv['pec'],'address':inv['fiscal_address'],'street_number':inv['street_number'],'zip_code':inv['zip_code'],'city':inv['city'],'province':inv['province'],'country':inv['country'] or 'IT'}
        invoice={'number':inv['number'],'date':inv['created'],'document_type':inv['sdi_document_type'] or 'TD01','notes':inv['notes'] or ''}
        items=[{'description':r['description'],'qty':r['qty'],'unit_net':r['unit_net'],'vat_rate':r['vat_rate'],'net_total':r['net_total'],'vat_amount':r['vat_amount'],'gross_total':r['gross_total'],'nature':r['nature'] or ''} for r in rows]
        progressivo=str(iid).zfill(5)[-10:]
        return seller,customer,invoice,items,progressivo

    def export_invoice_fatturapa(self, iid):
        if not iid: return QMessageBox.information(self,'FatturaPA','Seleziona prima una fattura.')
        try:
            seller,customer,invoice,items,progressivo=self._fatturapa_context(iid)
            errors=validate_context(seller,customer,invoice,items)
        except Exception as e:
            return QMessageBox.critical(self,'FatturaPA',str(e))
        if errors:
            return QMessageBox.warning(self,'FatturaPA - dati mancanti','Prima dell’esportazione completa questi dati:\n\n• '+'\n• '.join(errors))
        xml_dir=Path(core.DB_PATH).parent/'XML_FatturaPA'; xml_dir.mkdir(parents=True,exist_ok=True)
        sender=(seller.get('country') or 'IT').upper()+(digits(seller.get('vat_number')) or alnum(seller.get('tax_code')))
        default=xml_dir/f'{sender}_{progressivo}.xml'
        filename,_=QFileDialog.getSaveFileName(self,'Esporta XML FatturaPA / SDI',str(default),'FatturaPA XML (*.xml)')
        if not filename: return
        path=Path(filename)
        if path.suffix.lower()!='.xml': path=path.with_suffix('.xml')
        try: write_xml(path,seller,customer,invoice,items,progressivo)
        except Exception as e: return QMessageBox.critical(self,'FatturaPA',f'Impossibile creare il file XML:\n{e}')
        fmt=customer.get('transmission_format') or 'FPR12'
        extra='\n\nPer fatture verso PA (FPA12) è richiesta la firma digitale prima della trasmissione.' if fmt=='FPA12' else ''
        QMessageBox.information(self,'FatturaPA',f'XML FatturaPA creato:\n{path}\n\nFormato: {fmt}. Il programma genera il file ma non lo invia automaticamente allo SDI.{extra}')


if __name__=='__main__':
    ensure_fatturapa_schema(); ensure_users_schema()
    app=QApplication(sys.argv); app.setApplicationName(f'LA PRIMA Garage Manager {APP_VERSION}')
    login=UserLoginDialog()
    if login.exec()!=QDialog.Accepted: sys.exit(0)
    w=AppWindow(login.selected_user); w.show(); sys.exit(app.exec())
