import sys, sqlite3, re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QComboBox, QLineEdit, QMessageBox, QFileDialog, QGroupBox
)

import core
from main_016 import AppWindow as AppWindow016, UserLoginDialog, ensure_users_schema, ensure_fatturapa_schema
from core import BaseDialog, GlassFrame, RED
from fatturapa_017 import (
    write_xml, validate_context, NATURE_CODES, PAYMENT_METHODS, PAYMENT_TERMS,
    digits, alnum
)

APP_VERSION='0.1.7'


def _columns(conn,table): return {r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}


def ensure_company_schema():
    conn=sqlite3.connect(core.DB_PATH)
    invoice_cols=_columns(conn,'invoices')
    additions={
        'payment_terms':"TEXT DEFAULT 'TP02'",
        'payment_method':"TEXT DEFAULT 'MP05'",
        'payment_due_date':"TEXT DEFAULT ''",
        'payment_iban':"TEXT DEFAULT ''",
        'virtual_stamp':"INTEGER DEFAULT 0",
        'stamp_amount':"REAL DEFAULT 2.00",
    }
    for name,ddl in additions.items():
        if name not in invoice_cols: conn.execute(f'ALTER TABLE invoices ADD COLUMN {name} {ddl}')
    defaults={
        'sdi_pec':'',
        'sdi_rea_office':'',
        'sdi_rea_number':'',
        'sdi_share_capital':'',
        'sdi_sole_member':'',
        'sdi_liquidation_status':'LN',
        'sdi_iban':'',
        'sdi_bank_name':'',
        'sdi_default_payment_terms':'TP02',
        'sdi_default_payment_method':'MP05',
    }
    for key,value in defaults.items(): conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(key,value))
    conn.commit(); conn.close()


class AppWindow(AppWindow016):
    def __init__(self,current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")
        self._apply_logo_gradient_panel()

    def _apply_logo_gradient_panel(self):
        # Full official logo only. No separate OFFICINA / LA PRIMA text overlay.
        overlay=self.findChild(QLabel,'ReadableBrandText')
        if overlay: overlay.hide()
        for brand in self.findChildren(QLabel):
            if brand.toolTip()=='Logo ufficiale Officina LA PRIMA':
                brand.setFixedHeight(160)
                brand.setStyleSheet('''
                    QLabel{
                        background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                            stop:0 #FFFFFF, stop:0.48 #F4F5F6,
                            stop:0.78 #D9DDE1, stop:1 #BFC5CB);
                        border:1px solid rgba(90,105,120,120);
                        border-radius:12px;
                        padding:8px;
                    }
                ''')
                pm=QPixmap(str(core.LOGO_PATH))
                if not pm.isNull():
                    brand.setPixmap(pm.scaled(238,132,Qt.KeepAspectRatio,Qt.SmoothTransformation))
                    brand.setAlignment(Qt.AlignCenter)
                break

    # ---------- IMPOSTAZIONI > DATI AZIENDA ----------
    def show_settings(self):
        super().show_settings()
        page=self.stack.currentWidget()
        if not page or not page.layout(): return
        root=page.layout()

        # Hide the smaller fiscal card inherited from 0.1.6: this section replaces it completely.
        for lab in page.findChildren(QLabel):
            if lab.text().startswith('FatturaPA / Sistema di Interscambio'):
                if lab.parentWidget(): lab.parentWidget().hide()

        card=GlassFrame(225); box=QVBoxLayout(card)
        title=QLabel('Dati Azienda'); title.setObjectName('CompanyDataTitle'); title.setStyleSheet('font-size:22px;font-weight:900;color:#10233B;'); box.addWidget(title)
        intro=QLabel('Compila una sola volta i dati fiscali dell’officina. Verranno riutilizzati automaticamente nella generazione dell’XML FatturaPA destinato al Sistema di Interscambio (SDI).')
        intro.setWordWrap(True); intro.setStyleSheet('color:#405468;'); box.addWidget(intro)

        fiscal=QGroupBox('Anagrafica fiscale azienda'); f=QFormLayout(fiscal); widgets={}
        fields=[
            ('sdi_business_name','Ragione sociale / Denominazione'),
            ('sdi_vat_number','Partita IVA'),('sdi_tax_code','Codice Fiscale'),('sdi_tax_regime','Regime fiscale'),
            ('sdi_address','Indirizzo sede'),('sdi_street_number','Numero civico'),('sdi_zip_code','CAP'),
            ('sdi_city','Comune'),('sdi_province','Provincia'),('sdi_country','Nazione'),
            ('sdi_phone','Telefono'),('sdi_email','Email'),('sdi_pec','PEC aziendale'),
        ]
        for key,label in fields:
            w=QLineEdit(self.db.setting(key)); widgets[key]=w; f.addRow(label,w)
        widgets['sdi_vat_number'].setPlaceholderText('11 cifre')
        widgets['sdi_tax_regime'].setPlaceholderText('es. RF01')
        widgets['sdi_country'].setText(widgets['sdi_country'].text() or 'IT'); widgets['sdi_country'].setMaxLength(2)
        widgets['sdi_province'].setMaxLength(2); widgets['sdi_zip_code'].setMaxLength(5)
        box.addWidget(fiscal)

        rea=QGroupBox('Registro Imprese / REA (se applicabile)'); rf=QFormLayout(rea)
        for key,label in [
            ('sdi_rea_office','Ufficio REA / Provincia'),('sdi_rea_number','Numero REA'),('sdi_share_capital','Capitale sociale'),
        ]:
            w=QLineEdit(self.db.setting(key)); widgets[key]=w; rf.addRow(label,w)
        widgets['sdi_rea_office'].setMaxLength(2)
        sole=QComboBox(); sole.addItem('Non indicato',''); sole.addItem('Socio unico','SU'); sole.addItem('Più soci','SM'); sole.setCurrentIndex(max(0,sole.findData(self.db.setting('sdi_sole_member')))); widgets['sdi_sole_member']=sole; rf.addRow('Assetto societario',sole)
        liq=QComboBox(); liq.addItem('Non in liquidazione','LN'); liq.addItem('In liquidazione','LS'); liq.setCurrentIndex(max(0,liq.findData(self.db.setting('sdi_liquidation_status') or 'LN'))); widgets['sdi_liquidation_status']=liq; rf.addRow('Stato liquidazione',liq)
        box.addWidget(rea)

        pay=QGroupBox('Pagamenti predefiniti'); pf=QFormLayout(pay)
        iban=QLineEdit(self.db.setting('sdi_iban')); bank=QLineEdit(self.db.setting('sdi_bank_name')); widgets['sdi_iban']=iban; widgets['sdi_bank_name']=bank
        terms=QComboBox();
        for code,label in PAYMENT_TERMS.items(): terms.addItem(f'{code} - {label}',code)
        terms.setCurrentIndex(max(0,terms.findData(self.db.setting('sdi_default_payment_terms') or 'TP02'))); widgets['sdi_default_payment_terms']=terms
        method=QComboBox();
        for code,label in PAYMENT_METHODS.items(): method.addItem(f'{code} - {label}',code)
        method.setCurrentIndex(max(0,method.findData(self.db.setting('sdi_default_payment_method') or 'MP05'))); widgets['sdi_default_payment_method']=method
        pf.addRow('IBAN aziendale',iban); pf.addRow('Banca',bank); pf.addRow('Condizioni predefinite',terms); pf.addRow('Modalità predefinita',method); box.addWidget(pay)

        actions=QHBoxLayout(); save=QPushButton('Salva Dati Azienda'); verify=QPushButton('Verifica dati obbligatori')
        save.setStyleSheet(f'background:{RED};color:white;font-weight:800;padding:10px 16px;border-radius:7px;'); verify.setStyleSheet('background:#E7EDF2;color:#20364C;font-weight:700;padding:10px 16px;border-radius:7px;')
        actions.addWidget(save); actions.addWidget(verify); actions.addStretch(); box.addLayout(actions)
        note=QLabel('L’XML viene generato sul PC e può essere caricato manualmente nel portale “Fatture e Corrispettivi” dell’Agenzia delle Entrate oppure consegnato al commercialista. Il programma non effettua l’invio automatico allo SDI.')
        note.setWordWrap(True); note.setStyleSheet('color:#607487;font-size:11px;'); box.addWidget(note)

        def value_of(w): return w.currentData() if isinstance(w,QComboBox) else w.text().strip()
        def save_company(show_message=True):
            for key,w in widgets.items(): self.db.set_setting(key,value_of(w))
            if show_message: QMessageBox.information(self,'Dati Azienda','Dati aziendali salvati.')
        def verify_company():
            save_company(False); errors=[]
            vat=digits(self.db.setting('sdi_vat_number')); cf=alnum(self.db.setting('sdi_tax_code'))
            if len(vat)!=11: errors.append('Partita IVA: servono 11 cifre')
            if cf and not (11<=len(cf)<=16): errors.append('Codice Fiscale non valido')
            if not self.db.setting('sdi_business_name').strip(): errors.append('Ragione sociale mancante')
            if not re.fullmatch(r'RF\d{2}',(self.db.setting('sdi_tax_regime') or '').upper()): errors.append('Regime fiscale non valido (es. RF01)')
            if not self.db.setting('sdi_address').strip(): errors.append('Indirizzo mancante')
            if len(digits(self.db.setting('sdi_zip_code')))!=5: errors.append('CAP: servono 5 cifre')
            if not self.db.setting('sdi_city').strip(): errors.append('Comune mancante')
            if (self.db.setting('sdi_country') or 'IT').upper()=='IT' and len((self.db.setting('sdi_province') or '').strip())!=2: errors.append('Provincia: servono 2 lettere')
            if errors: QMessageBox.warning(self,'Dati Azienda incompleti','Completa questi campi prima di generare FatturaPA:\n\n• '+'\n• '.join(errors))
            else: QMessageBox.information(self,'Dati Azienda','I dati aziendali obbligatori di base risultano compilati correttamente.')
        save.clicked.connect(save_company); verify.clicked.connect(verify_company)
        root.insertWidget(max(0,root.count()-1),card)

    # ---------- OPZIONI FATTURAPA + PAGAMENTO ----------
    def fatturapa_options_dialog(self,iid):
        if not iid: return QMessageBox.information(self,'FatturaPA','Seleziona prima una fattura.')
        inv=self.db.one('SELECT * FROM invoices WHERE id=?',(iid,));
        if not inv: return
        zero=self.db.q('SELECT id,description,vat_rate,nature FROM invoice_items WHERE invoice_id=? AND ABS(vat_rate)<0.0001 ORDER BY id',(iid,))
        d=BaseDialog('Dati FatturaPA / SDI',self); d.setMinimumWidth(700); root=QVBoxLayout(d); form=QFormLayout()
        doc=QComboBox(); doc.setEditable(True)
        for code,label in [('TD01','Fattura'),('TD04','Nota di credito'),('TD05','Nota di debito'),('TD24','Fattura differita'),('TD25','Fattura differita triangolare')]: doc.addItem(f'{code} - {label}',code)
        current=inv['sdi_document_type'] or 'TD01'; idx=doc.findData(current); doc.setCurrentIndex(idx if idx>=0 else 0)
        terms=QComboBox();
        for code,label in PAYMENT_TERMS.items(): terms.addItem(f'{code} - {label}',code)
        terms.setCurrentIndex(max(0,terms.findData(inv['payment_terms'] or self.db.setting('sdi_default_payment_terms') or 'TP02')))
        method=QComboBox();
        for code,label in PAYMENT_METHODS.items(): method.addItem(f'{code} - {label}',code)
        method.setCurrentIndex(max(0,method.findData(inv['payment_method'] or self.db.setting('sdi_default_payment_method') or 'MP05')))
        due=QLineEdit(inv['payment_due_date'] or ''); due.setPlaceholderText('AAAA-MM-GG, opzionale')
        iban=QLineEdit(inv['payment_iban'] or self.db.setting('sdi_iban') or '')
        bollo=QComboBox(); bollo.addItem('No',0); bollo.addItem('Sì',1); bollo.setCurrentIndex(max(0,bollo.findData(int(inv['virtual_stamp'] or 0))))
        stamp=QLineEdit(f"{float(inv['stamp_amount'] or 2):.2f}")
        form.addRow('Tipo documento',doc); form.addRow('Condizioni pagamento',terms); form.addRow('Modalità pagamento',method); form.addRow('Scadenza pagamento',due); form.addRow('IBAN',iban); form.addRow('Bollo virtuale',bollo); form.addRow('Importo bollo €',stamp); root.addLayout(form)
        nature_widgets=[]
        if zero:
            lab=QLabel('Righe con IVA 0%: specifica il codice Natura previsto dal tracciato FatturaPA.'); lab.setWordWrap(True); root.addWidget(lab)
            for row in zero:
                combo=QComboBox(); combo.addItem('— Seleziona Natura —','')
                for code in sorted(NATURE_CODES): combo.addItem(code,code)
                combo.setCurrentIndex(max(0,combo.findData(row['nature'] or '')))
                rr=QHBoxLayout(); desc=QLabel(row['description']); desc.setWordWrap(True); rr.addWidget(desc,1); rr.addWidget(combo); root.addLayout(rr); nature_widgets.append((row['id'],combo))
        actions=QHBoxLayout(); actions.addStretch(); cancel=QPushButton('Annulla'); save=QPushButton('Salva'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); actions.addWidget(cancel); actions.addWidget(save); root.addLayout(actions); cancel.clicked.connect(d.reject)
        def do_save():
            raw=doc.currentData() if doc.currentData() else doc.currentText().split(' - ')[0].strip().upper()
            if not raw.startswith('TD') or len(raw)!=4: return QMessageBox.warning(d,'FatturaPA','Tipo documento non valido.')
            if due.text().strip() and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',due.text().strip()): return QMessageBox.warning(d,'FatturaPA','Scadenza: usare AAAA-MM-GG.')
            try: stamp_value=float(stamp.text().replace(',','.'))
            except ValueError: return QMessageBox.warning(d,'FatturaPA','Importo bollo non valido.')
            self.db.ex('UPDATE invoices SET sdi_document_type=?,payment_terms=?,payment_method=?,payment_due_date=?,payment_iban=?,virtual_stamp=?,stamp_amount=? WHERE id=?',(raw,terms.currentData(),method.currentData(),due.text().strip(),alnum(iban.text()),bollo.currentData(),stamp_value,iid))
            for item_id,combo in nature_widgets: self.db.ex('UPDATE invoice_items SET nature=? WHERE id=?',(combo.currentData() or '',item_id))
            d.accept(); self.show_invoices()
        save.clicked.connect(do_save); d.exec()

    def _fatturapa_context(self,iid):
        inv=self.db.one('''SELECT i.*,v.plate,v.brand,v.model,c.id client_id,c.name client,c.vat_number,c.tax_code,c.transmission_format,c.recipient_code,c.pec,c.fiscal_address,c.street_number,c.zip_code,c.city,c.province,c.country FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''',(iid,))
        if not inv: raise ValueError('Fattura non trovata.')
        rows=self.db.q('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(iid,))
        seller={
            'business_name':self.db.setting('sdi_business_name') or self.db.setting('name'),'vat_number':self.db.setting('sdi_vat_number'),'tax_code':self.db.setting('sdi_tax_code'),'tax_regime':self.db.setting('sdi_tax_regime') or 'RF01',
            'address':self.db.setting('sdi_address'),'street_number':self.db.setting('sdi_street_number'),'zip_code':self.db.setting('sdi_zip_code'),'city':self.db.setting('sdi_city'),'province':self.db.setting('sdi_province'),'country':self.db.setting('sdi_country') or 'IT',
            'email':self.db.setting('sdi_email'),'phone':self.db.setting('sdi_phone'),'pec':self.db.setting('sdi_pec'),'rea_office':self.db.setting('sdi_rea_office'),'rea_number':self.db.setting('sdi_rea_number'),'share_capital':self.db.setting('sdi_share_capital'),'sole_member':self.db.setting('sdi_sole_member'),'liquidation_status':self.db.setting('sdi_liquidation_status') or 'LN'
        }
        customer={'name':inv['client'],'vat_number':inv['vat_number'],'tax_code':inv['tax_code'],'transmission_format':inv['transmission_format'] or 'FPR12','recipient_code':inv['recipient_code'],'pec':inv['pec'],'address':inv['fiscal_address'],'street_number':inv['street_number'],'zip_code':inv['zip_code'],'city':inv['city'],'province':inv['province'],'country':inv['country'] or 'IT'}
        invoice={'number':inv['number'],'date':inv['created'],'document_type':inv['sdi_document_type'] or 'TD01','notes':inv['notes'] or '','payment_terms':inv['payment_terms'] or self.db.setting('sdi_default_payment_terms') or 'TP02','payment_method':inv['payment_method'] or self.db.setting('sdi_default_payment_method') or 'MP05','payment_due_date':inv['payment_due_date'] or '','payment_iban':inv['payment_iban'] or self.db.setting('sdi_iban') or '','virtual_stamp':bool(inv['virtual_stamp'] or 0),'stamp_amount':float(inv['stamp_amount'] or 0)}
        items=[{'description':r['description'],'qty':r['qty'],'unit_net':r['unit_net'],'vat_rate':r['vat_rate'],'net_total':r['net_total'],'vat_amount':r['vat_amount'],'gross_total':r['gross_total'],'nature':r['nature'] or ''} for r in rows]
        progressivo=str(iid).zfill(5)[-10:]
        return seller,customer,invoice,items,progressivo

    def export_invoice_fatturapa(self,iid):
        if not iid: return QMessageBox.information(self,'FatturaPA','Seleziona prima una fattura.')
        try:
            seller,customer,invoice,items,progressivo=self._fatturapa_context(iid); errors=validate_context(seller,customer,invoice,items)
        except Exception as e: return QMessageBox.critical(self,'FatturaPA',str(e))
        if errors: return QMessageBox.warning(self,'FatturaPA - dati mancanti','Prima dell’esportazione completa:\n\n• '+'\n• '.join(errors))
        xml_dir=Path(core.DB_PATH).parent/'XML_FatturaPA'; xml_dir.mkdir(parents=True,exist_ok=True)
        sender=(seller.get('country') or 'IT').upper()+(digits(seller.get('vat_number')) or alnum(seller.get('tax_code'))); default=xml_dir/f'{sender}_{progressivo}.xml'
        filename,_=QFileDialog.getSaveFileName(self,'Esporta XML FatturaPA / SDI',str(default),'FatturaPA XML (*.xml)')
        if not filename: return
        path=Path(filename); path=path if path.suffix.lower()=='.xml' else path.with_suffix('.xml')
        try: write_xml(path,seller,customer,invoice,items,progressivo)
        except Exception as e: return QMessageBox.critical(self,'FatturaPA',f'Impossibile creare XML:\n{e}')
        QMessageBox.information(self,'FatturaPA / SDI',f'XML FatturaPA creato:\n{path}\n\nIl file è predisposto per il caricamento manuale nei canali dell’Agenzia delle Entrate / SDI. Prima dell’uso fiscale reale è consigliato verificare i dati aziendali e il primo file con il commercialista.')


if __name__=='__main__':
    ensure_fatturapa_schema(); ensure_company_schema(); ensure_users_schema()
    app=QApplication(sys.argv); app.setApplicationName(f'LA PRIMA Garage Manager {APP_VERSION}')
    login=UserLoginDialog()
    if login.exec()!=QDialog.Accepted: sys.exit(0)
    w=AppWindow(login.selected_user); w.show(); sys.exit(app.exec())
