import sqlite3

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QGroupBox,
    QScrollArea
)
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

import core
from main_019 import AppWindow as AppWindow019
from main_019 import (
    ensure_customer_type_schema, ensure_company_schema, ensure_fatturapa_schema,
    ensure_users_schema,
)
from core import TablePage, BaseDialog, GlassFrame, RED
from fatturapa_017 import digits, alnum

APP_VERSION = '0.1.10'

PAYMENT_CHOICES = [
    ('MP01', 'Contanti'),
    ('MP08', 'Carta / POS'),
    ('MP05', 'Bonifico bancario'),
]

FISCAL_REGIMES = [
    ('RF01', 'Ordinario'),
    ('RF02', 'Contribuenti minimi'),
    ('RF04', 'Agricoltura e attività connesse e pesca'),
    ('RF05', 'Vendita sali e tabacchi'),
    ('RF06', 'Commercio dei fiammiferi'),
    ('RF07', 'Editoria'),
    ('RF08', 'Gestione servizi di telefonia pubblica'),
    ('RF09', 'Rivendita documenti trasporto pubblico e sosta'),
    ('RF10', 'Intrattenimenti, giochi e altre attività speciali'),
    ('RF11', 'Agenzie viaggi e turismo'),
    ('RF12', 'Agriturismo'),
    ('RF13', 'Vendite a domicilio'),
    ('RF14', 'Rivendita beni usati / arte / antiquariato / collezione'),
    ('RF15', 'Agenzie vendite all’asta di arte / antiquariato / collezione'),
    ('RF16', 'IVA per cassa P.A.'),
    ('RF17', 'IVA per cassa'),
    ('RF18', 'Altro'),
    ('RF19', 'Regime forfettario'),
]

LEGAL_TYPES = [
    ('SOCIETA', 'Società / ente con Partita IVA'),
    ('DITTA', 'Ditta individuale / persona fisica con Partita IVA'),
    ('PROFESSIONISTA', 'Professionista / lavoratore autonomo con Partita IVA'),
]


def _columns(conn, table):
    return {r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}


def ensure_final_schema():
    conn = sqlite3.connect(core.DB_PATH)
    quote_cols = _columns(conn, 'quote_items')
    additions = {
        'vat_rate': 'REAL NOT NULL DEFAULT 0',
        'net_total': 'REAL NOT NULL DEFAULT 0',
        'vat_amount': 'REAL NOT NULL DEFAULT 0',
        'gross_total': 'REAL NOT NULL DEFAULT 0',
    }
    changed = False
    for name, ddl in additions.items():
        if name not in quote_cols:
            conn.execute(f'ALTER TABLE quote_items ADD COLUMN {name} {ddl}')
            changed = True
    if changed:
        # Existing quotes keep exactly the same amount: old rows are migrated as IVA 0%.
        conn.execute('''UPDATE quote_items
                        SET vat_rate=0,
                            net_total=COALESCE(line_total, qty*unit_price, 0),
                            vat_amount=0,
                            gross_total=COALESCE(line_total, qty*unit_price, 0)''')

    defaults = {
        'sdi_legal_type': 'SOCIETA',
        'sdi_tax_regime': 'RF01',
    }
    for key, value in defaults.items():
        conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (key, value))
    conn.commit()
    conn.close()


def calc_line(qty, unit_net, vat_rate):
    net = round(float(qty) * float(unit_net), 2)
    vat = round(net * float(vat_rate) / 100.0, 2)
    gross = round(net + vat, 2)
    return net, vat, gross


class AppWindow(AppWindow019):
    def __init__(self, current_user=None):
        super().__init__(current_user)
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")

    # ---------- DATI AZIENDA: TIPO SOGGETTO + REGIME FISCALE SELEZIONABILI ----------
    def show_company_data(self):
        self.set_nav('Dati Azienda')
        page = QWidget(); page.setStyleSheet('background:transparent;')
        outer = QVBoxLayout(page); outer.setContentsMargins(22,18,22,22); outer.setSpacing(12)
        title = QLabel('Dati Azienda'); title.setStyleSheet('font-size:30px;font-weight:900;color:white;')
        subtitle = QLabel('Anagrafica fiscale dell’officina utilizzata per PDF e XML FatturaPA / SDI')
        subtitle.setStyleSheet('font-size:12px;color:#EFF4F8;')
        outer.addWidget(title); outer.addWidget(subtitle)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet('QScrollArea{background:transparent;border:0;}')
        content = QWidget(); content.setStyleSheet('background:transparent;')
        root = QVBoxLayout(content); root.setContentsMargins(0,0,10,10); root.setSpacing(14)
        scroll.setWidget(content); outer.addWidget(scroll,1)

        card = GlassFrame(228); box = QVBoxLayout(card); box.setContentsMargins(20,18,20,20); box.setSpacing(14)
        intro = QLabel('Seleziona prima il tipo di soggetto e il regime fiscale. Non viene presunto che l’officina sia una società o che applichi un determinato regime: questi dati vanno impostati in base alla situazione reale indicata dal commercialista.')
        intro.setWordWrap(True); intro.setStyleSheet('color:#405468;font-size:12px;'); box.addWidget(intro)
        self._company_widgets = {}

        fiscal = QGroupBox('Inquadramento fiscale')
        fiscal.setStyleSheet('QGroupBox{font-weight:800;color:#20364C;margin-top:10px;} QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}')
        ff = QFormLayout(fiscal); ff.setLabelAlignment(Qt.AlignRight)

        legal = QComboBox(); legal.setObjectName('CompanyLegalTypeCombo')
        for code, label in LEGAL_TYPES: legal.addItem(label, code)
        legal.setCurrentIndex(max(0, legal.findData(self.db.setting('sdi_legal_type') or 'SOCIETA')))
        self._company_widgets['sdi_legal_type'] = legal; ff.addRow('Tipo soggetto', legal)

        regime = QComboBox(); regime.setObjectName('CompanyTaxRegimeCombo')
        for code, label in FISCAL_REGIMES: regime.addItem(f'{code} - {label}', code)
        current_regime = (self.db.setting('sdi_tax_regime') or 'RF01').upper()
        regime.setCurrentIndex(max(0, regime.findData(current_regime)))
        self._company_widgets['sdi_tax_regime'] = regime; ff.addRow('Regime fiscale', regime)

        fields = [
            ('sdi_business_name','Ragione sociale / Denominazione'),
            ('sdi_vat_number','Partita IVA'),('sdi_tax_code','Codice Fiscale'),
            ('sdi_address','Indirizzo sede'),('sdi_street_number','Numero civico'),
            ('sdi_zip_code','CAP'),('sdi_city','Comune'),('sdi_province','Provincia'),
            ('sdi_country','Nazione'),('sdi_phone','Telefono'),('sdi_email','Email'),('sdi_pec','PEC aziendale'),
        ]
        for key, label in fields:
            w = QLineEdit(self.db.setting(key)); w.setObjectName('Company_' + key)
            self._company_widgets[key] = w; ff.addRow(label, w)
        self._company_widgets['sdi_vat_number'].setPlaceholderText('11 cifre')
        self._company_widgets['sdi_country'].setText(self._company_widgets['sdi_country'].text() or 'IT')
        self._company_widgets['sdi_country'].setMaxLength(2); self._company_widgets['sdi_province'].setMaxLength(2); self._company_widgets['sdi_zip_code'].setMaxLength(5)
        box.addWidget(fiscal)

        hint = QLabel(); hint.setObjectName('CompanyFiscalHint'); hint.setWordWrap(True); hint.setStyleSheet('color:#5D6D7E;font-size:11px;')
        box.addWidget(hint)
        def update_hint():
            lt = legal.currentData(); rf = regime.currentData()
            if lt == 'SOCIETA':
                text = 'Società / ente: usa la denominazione legale e la Partita IVA. Il regime fiscale va scelto in base all’inquadramento reale.'
                if rf == 'RF19': text += ' Attenzione: RF19 (forfettario) è normalmente riferito a persone fisiche, quindi verifica questo abbinamento con il commercialista.'
            elif lt == 'DITTA':
                text = 'Ditta individuale / persona fisica con P.IVA: inserisci la denominazione utilizzata fiscalmente, P.IVA e Codice Fiscale. Può essere RF01 o, se ne ricorrono i requisiti, RF19.'
            else:
                text = 'Professionista / autonomo con P.IVA: inserisci denominazione/nome fiscale, P.IVA e Codice Fiscale; scegli il regime reale (es. RF01 o RF19 se applicabile).'
            hint.setText(text)
        legal.currentIndexChanged.connect(update_hint); regime.currentIndexChanged.connect(update_hint); update_hint()

        rea = QGroupBox('Registro Imprese / REA (se applicabile)'); rea.setStyleSheet(fiscal.styleSheet()); rf = QFormLayout(rea)
        for key, label in [('sdi_rea_office','Ufficio REA / Provincia'),('sdi_rea_number','Numero REA'),('sdi_share_capital','Capitale sociale')]:
            w = QLineEdit(self.db.setting(key)); self._company_widgets[key] = w; rf.addRow(label,w)
        self._company_widgets['sdi_rea_office'].setMaxLength(2)
        sole=QComboBox(); sole.addItem('Non indicato',''); sole.addItem('Socio unico','SU'); sole.addItem('Più soci','SM'); sole.setCurrentIndex(max(0,sole.findData(self.db.setting('sdi_sole_member')))); self._company_widgets['sdi_sole_member']=sole; rf.addRow('Assetto societario',sole)
        liq=QComboBox(); liq.addItem('Non in liquidazione','LN'); liq.addItem('In liquidazione','LS'); liq.setCurrentIndex(max(0,liq.findData(self.db.setting('sdi_liquidation_status') or 'LN'))); self._company_widgets['sdi_liquidation_status']=liq; rf.addRow('Stato liquidazione',liq)
        box.addWidget(rea)

        pay = QGroupBox('Pagamenti predefiniti'); pay.setStyleSheet(fiscal.styleSheet()); pf=QFormLayout(pay)
        iban=QLineEdit(self.db.setting('sdi_iban')); bank=QLineEdit(self.db.setting('sdi_bank_name')); self._company_widgets['sdi_iban']=iban; self._company_widgets['sdi_bank_name']=bank
        default_pay=QComboBox(); default_pay.setObjectName('CompanyDefaultPaymentCombo')
        for code,label in PAYMENT_CHOICES: default_pay.addItem(f'{label} ({code})',code)
        default_pay.setCurrentIndex(max(0,default_pay.findData(self.db.setting('sdi_default_payment_method') or 'MP05')))
        self._company_widgets['sdi_default_payment_method']=default_pay
        pf.addRow('IBAN aziendale',iban); pf.addRow('Banca',bank); pf.addRow('Pagamento predefinito fatture',default_pay)
        box.addWidget(pay)

        actions=QHBoxLayout(); save=QPushButton('Salva Dati Azienda'); save.setObjectName('SaveCompanyDataButton'); verify=QPushButton('Verifica dati obbligatori')
        save.setStyleSheet(f'background:{RED};color:white;font-weight:800;padding:11px 18px;border-radius:7px;'); verify.setStyleSheet('background:#E7EDF2;color:#20364C;font-weight:700;padding:11px 18px;border-radius:7px;')
        actions.addWidget(save); actions.addWidget(verify); actions.addStretch(); box.addLayout(actions)
        status=QLabel('Le modifiche vengono salvate nel database quando premi “Salva Dati Azienda”.'); status.setWordWrap(True); status.setStyleSheet('color:#607487;font-size:11px;'); box.addWidget(status)
        root.addWidget(card); root.addStretch()

        def value_of(w): return w.currentData() if isinstance(w,QComboBox) else w.text().strip()
        def save_company(show_message=True):
            for key,w in self._company_widgets.items(): self.db.set_setting(key,value_of(w))
            status.setText('Dati Azienda salvati correttamente.'); status.setStyleSheet('color:#087A52;font-size:11px;font-weight:700;')
            if show_message: QMessageBox.information(self,'Dati Azienda','Dati aziendali salvati correttamente.')
        def verify_company():
            errors=[]; vat=digits(self._company_widgets['sdi_vat_number'].text()); cf=alnum(self._company_widgets['sdi_tax_code'].text())
            if len(vat)!=11: errors.append('Partita IVA: servono 11 cifre')
            if cf and not (11<=len(cf)<=16): errors.append('Codice Fiscale non valido')
            if not self._company_widgets['sdi_business_name'].text().strip(): errors.append('Ragione sociale / denominazione mancante')
            if regime.currentData() not in {c for c,_ in FISCAL_REGIMES}: errors.append('Regime fiscale non valido')
            if not self._company_widgets['sdi_address'].text().strip(): errors.append('Indirizzo mancante')
            if len(digits(self._company_widgets['sdi_zip_code'].text()))!=5: errors.append('CAP: servono 5 cifre')
            if not self._company_widgets['sdi_city'].text().strip(): errors.append('Comune mancante')
            if (self._company_widgets['sdi_country'].text().strip() or 'IT').upper()=='IT' and len(self._company_widgets['sdi_province'].text().strip())!=2: errors.append('Provincia: servono 2 lettere')
            if legal.currentData()=='SOCIETA' and regime.currentData()=='RF19': errors.append('Controlla con il commercialista: RF19 forfettario è normalmente previsto per persone fisiche, non per società')
            if errors: QMessageBox.warning(self,'Dati Azienda da verificare','Controlla questi dati:\n\n• '+'\n• '.join(errors))
            else: QMessageBox.information(self,'Dati Azienda','I dati aziendali obbligatori di base risultano compilati correttamente.')
        save.clicked.connect(save_company); verify.clicked.connect(verify_company)
        self._set_page(page)

    # ---------- FATTURE: PAGAMENTO DIRETTAMENTE NELLA FATTURA ----------
    def show_invoices(self):
        self.set_nav('Fatture')
        p=TablePage(self,'Fatture','Fatture a righe con IVA, modalità di pagamento, PDF e FatturaPA / SDI')
        p.add_btn('Nuova',lambda:self.invoice_dialog(),True); p.add_btn('Modifica',lambda:self.invoice_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_invoice(p)); p.add_btn('Stampa PDF',lambda:self.print_invoice_selected(p.selected_id())); p.add_btn('Dati FatturaPA',lambda:self.fatturapa_options_dialog(p.selected_id())); p.add_btn('Esporta FatturaPA/SDI',lambda:self.export_invoice_fatturapa(p.selected_id())); p.add_btn('XML gestionale',lambda:self.export_invoice_xml(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_invoices)
        labels=dict(PAYMENT_CHOICES)
        rows=self.db.q('''SELECT i.*,v.plate,c.name client FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY i.id DESC''')
        p.populate(['ID','Numero','Data','Targa','Cliente','Stato','Pagamento','Tipo SDI','Totale lordo €','Note'],[[r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],labels.get(r['payment_method'] or 'MP05',r['payment_method'] or 'Bonifico bancario'),r['sdi_document_type'] or 'TD01',f"{r['total']:.2f}",r['notes']] for r in rows])
        p.table.doubleClicked.connect(lambda:self.invoice_dialog(p.selected_id())); self._set_page(p)

    def invoice_dialog(self,iid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Fatture','Crea prima un veicolo.')
        d=BaseDialog('Fattura',self); d.resize(1100,790); root=QVBoxLayout(d)
        top=QFormLayout(); veh=self.vehicle_combo(d); num=QLineEdit(self.next_number('invoices','FAT')); de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); st=QComboBox(); st.addItems(['Bozza','Emessa','Pagata','Annullata'])
        payment=QComboBox(); payment.setObjectName('InvoicePaymentMethodCombo')
        for code,label in PAYMENT_CHOICES: payment.addItem(label,code)
        payment.setCurrentIndex(max(0,payment.findData(self.db.setting('sdi_default_payment_method') or 'MP05')))
        top.addRow('Cliente / veicolo',veh); top.addRow('Numero fattura',num); top.addRow('Data',de); top.addRow('Stato',st); top.addRow('Modalità di pagamento',payment); root.addLayout(top)

        box=QGroupBox('Righe fattura'); g=QGridLayout(box)
        desc=QLineEdit(); qty=QDoubleSpinBox(); qty.setRange(0.01,99999); qty.setValue(1); qty.setDecimals(2); unit=QDoubleSpinBox(); unit.setRange(0,9999999); unit.setDecimals(2); vat=QDoubleSpinBox(); vat.setRange(0,100); vat.setValue(22); vat.setSuffix(' %'); vat.setDecimals(2)
        add=QPushButton('Aggiungi / aggiorna riga'); rem=QPushButton('Rimuovi riga')
        for col,(lab,w) in enumerate([('Descrizione',desc),('Q.tà',qty),('Prezzo netto €',unit),('IVA %',vat)]): g.addWidget(QLabel(lab),0,col); g.addWidget(w,1,col)
        g.addWidget(add,1,4); g.addWidget(rem,1,5)
        items=QTableWidget(); items.setColumnCount(7); items.setHorizontalHeaderLabels(['Descrizione','Q.tà','Prezzo netto €','IVA %','Imponibile €','IVA €','Lordo €']); items.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); items.setSelectionBehavior(QAbstractItemView.SelectRows); items.setEditTriggers(QAbstractItemView.NoEditTriggers); g.addWidget(items,2,0,1,6); root.addWidget(box,1)
        sums=QHBoxLayout(); sums.addStretch(); net_lab=QLabel(); vat_lab=QLabel(); gross_lab=QLabel()
        for lab in (net_lab,vat_lab,gross_lab): lab.setStyleSheet('font-size:16px;font-weight:750;color:#10233B;padding:5px 10px;'); sums.addWidget(lab)
        gross_lab.setStyleSheet(f'font-size:19px;font-weight:850;color:{RED};padding:5px 10px;'); root.addLayout(sums)
        notes=QTextEdit(); notes.setPlaceholderText('Note fattura'); notes.setFixedHeight(80); root.addWidget(notes)
        def totals():
            n=sum(float(items.item(r,4).text()) for r in range(items.rowCount())); iv=sum(float(items.item(r,5).text()) for r in range(items.rowCount())); gr=sum(float(items.item(r,6).text()) for r in range(items.rowCount())); net_lab.setText(f'Imponibile: € {n:.2f}'); vat_lab.setText(f'IVA: € {iv:.2f}'); gross_lab.setText(f'Totale: € {gr:.2f}'); return n,iv,gr
        def add_item():
            if not desc.text().strip(): return QMessageBox.warning(d,'Fattura','Inserisci la descrizione della riga.')
            n,iv,gr=calc_line(qty.value(),unit.value(),vat.value()); row=items.currentRow()
            if row<0: row=items.rowCount(); items.insertRow(row)
            vals=[desc.text().strip(),f'{qty.value():.2f}',f'{unit.value():.2f}',f'{vat.value():.2f}',f'{n:.2f}',f'{iv:.2f}',f'{gr:.2f}']
            for c,val in enumerate(vals): items.setItem(row,c,QTableWidgetItem(val))
            desc.clear(); qty.setValue(1); unit.setValue(0); vat.setValue(22); items.clearSelection(); totals()
        def load_item():
            row=items.currentRow()
            if row>=0 and items.item(row,0): desc.setText(items.item(row,0).text()); qty.setValue(float(items.item(row,1).text())); unit.setValue(float(items.item(row,2).text())); vat.setValue(float(items.item(row,3).text()))
        def remove_item():
            row=items.currentRow()
            if row>=0: items.removeRow(row); totals()
        add.clicked.connect(add_item); rem.clicked.connect(remove_item); items.itemSelectionChanged.connect(load_item)
        if iid:
            inv=self.db.one('SELECT * FROM invoices WHERE id=?',(iid,)); veh.setCurrentIndex(max(0,veh.findData(inv['vehicle_id']))); num.setText(inv['number']); de.setDate(QDate.fromString(inv['created'],'yyyy-MM-dd')); st.setCurrentText(inv['status']); payment.setCurrentIndex(max(0,payment.findData(inv['payment_method'] or 'MP05'))); notes.setPlainText(inv['notes'] or '')
            old=self.db.q('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(iid,))
            if not old and (inv['total'] or 0)>0: old=[{'description':'Importo fattura precedente','qty':1.0,'unit_net':inv['total'],'vat_rate':0.0,'net_total':inv['total'],'vat_amount':0.0,'gross_total':inv['total']}]
            for it in old:
                row=items.rowCount(); items.insertRow(row); vals=[it['description'],f"{it['qty']:.2f}",f"{it['unit_net']:.2f}",f"{it['vat_rate']:.2f}",f"{it['net_total']:.2f}",f"{it['vat_amount']:.2f}",f"{it['gross_total']:.2f}"]
                for c,val in enumerate(vals): items.setItem(row,c,QTableWidgetItem(val))
        totals(); save=QPushButton('Salva fattura'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:10px 18px;border-radius:7px;'); root.addWidget(save,0,Qt.AlignRight)
        def do_save():
            if items.rowCount()==0: return QMessageBox.warning(d,'Fattura','Aggiungi almeno una riga.')
            _,_,gross=totals(); vals=(num.text().strip(),veh.currentData(),de.date().toString('yyyy-MM-dd'),st.currentText(),gross,notes.toPlainText().strip(),payment.currentData())
            if iid:
                self.db.ex('UPDATE invoices SET number=?,vehicle_id=?,created=?,status=?,total=?,notes=?,payment_method=? WHERE id=?',vals+(iid,)); iid2=iid; self.db.ex('DELETE FROM invoice_items WHERE invoice_id=?',(iid2,))
            else:
                iid2=self.db.ex('INSERT INTO invoices(number,vehicle_id,created,status,total,notes,payment_method) VALUES(?,?,?,?,?,?,?)',vals).lastrowid
            for r in range(items.rowCount()):
                self.db.ex('INSERT INTO invoice_items(invoice_id,description,qty,unit_net,vat_rate,net_total,vat_amount,gross_total) VALUES(?,?,?,?,?,?,?,?)',(iid2,items.item(r,0).text(),float(items.item(r,1).text()),float(items.item(r,2).text()),float(items.item(r,3).text()),float(items.item(r,4).text()),float(items.item(r,5).text()),float(items.item(r,6).text())))
            d.accept(); self.show_invoices()
        save.clicked.connect(do_save); d.exec()

    def print_invoice_selected(self,iid):
        if not iid:return QMessageBox.information(self,'PDF','Seleziona prima una fattura.')
        inv=self.db.one('''SELECT i.*,v.plate,v.brand,v.model,v.year,c.name client,c.phone,c.email FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''',(iid,)); its=self.db.q('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(iid,)); p=self.make_pdf_path(f"Fattura_{inv['number']}"); c=pdfcanvas.Canvas(str(p),pagesize=A4); W,H=A4; y=self.pdf_header(c,'FATTURA')
        pay_label=dict(PAYMENT_CHOICES).get(inv['payment_method'] or 'MP05',inv['payment_method'] or 'Bonifico bancario')
        c.setFont('Helvetica-Bold',10); c.drawString(16*mm,y,f"N. {inv['number']}   Data: {inv['created']}   Stato: {inv['status']}"); y-=7*mm; c.drawString(16*mm,y,f"Pagamento: {pay_label}"); y-=8*mm; c.setFont('Helvetica',9); c.drawString(16*mm,y,f"Cliente: {inv['client']}   Tel: {inv['phone'] or '-'}   Email: {inv['email'] or '-'}"); y-=6*mm; c.drawString(16*mm,y,f"Veicolo: {inv['brand']} {inv['model']}   Targa: {inv['plate']}   Anno: {inv['year'] or '-'}"); y-=11*mm
        headers=[('Descrizione',16),('Q.tà',116),('Netto',137),('IVA %',158),('IVA €',176),('Lordo',198)]; c.setFont('Helvetica-Bold',7)
        for h,x in headers: c.drawRightString(x*mm,y,h) if x>20 else c.drawString(x*mm,y,h)
        y-=4*mm; c.line(16*mm,y,198*mm,y); y-=6*mm; c.setFont('Helvetica',7.5); net=iva=gross=0.0
        for it in its:
            if y<38*mm: c.showPage(); y=H-20*mm; c.setFont('Helvetica',7.5)
            c.drawString(16*mm,y,str(it['description'])[:62]); c.drawRightString(116*mm,y,f"{it['qty']:.2f}"); c.drawRightString(137*mm,y,f"€ {it['unit_net']:.2f}"); c.drawRightString(158*mm,y,f"{it['vat_rate']:.2f}%"); c.drawRightString(176*mm,y,f"€ {it['vat_amount']:.2f}"); c.drawRightString(198*mm,y,f"€ {it['gross_total']:.2f}"); y-=6*mm; net+=it['net_total']; iva+=it['vat_amount']; gross+=it['gross_total']
        if not its: gross=inv['total'] or 0; net=gross
        y-=5*mm; c.setFont('Helvetica-Bold',10); c.drawRightString(198*mm,y,f"Imponibile: € {net:.2f}"); y-=6*mm; c.drawRightString(198*mm,y,f"IVA: € {iva:.2f}"); y-=7*mm; c.setFillColor(colors.HexColor(RED)); c.setFont('Helvetica-Bold',13); c.drawRightString(198*mm,y,f"TOTALE: € {gross:.2f}"); c.setFillColor(colors.black); y-=12*mm; c.setFont('Helvetica',9); c.drawString(16*mm,y,'Note: '+str(inv['notes'] or '')[:140]); c.save(); self.open_pdf(p)

    # ---------- PREVENTIVI: IVA PER RIGA ----------
    def show_quotes(self):
        self.set_nav('Preventivi'); p=TablePage(self,'Preventivi','Preventivi con imponibile, IVA per riga e totale lordo automatico')
        p.add_btn('Nuovo',lambda:self.quote_dialog(),True); p.add_btn('Modifica',lambda:self.quote_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_quote(p)); p.add_btn('Stampa selezionato',lambda:self.print_quote(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_quotes)
        rows=self.db.q('''SELECT q.*,v.plate,c.name client FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY q.id DESC'''); p.populate(['ID','Numero','Data','Targa','Cliente','Stato','Totale lordo €','Note'],[[r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],f"{r['total']:.2f}",r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.quote_dialog(p.selected_id())); self._set_page(p)

    def quote_dialog(self,qid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Preventivi','Crea prima un veicolo.')
        d=BaseDialog('Preventivo',self); d.resize(1080,760); root=QVBoxLayout(d); top=QFormLayout(); veh=self.vehicle_combo(d); num=QLineEdit(self.next_number('quotes','PREV')); de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); st=QComboBox(); st.addItems(['Bozza','Inviato','Accettato','Rifiutato']); top.addRow('Cliente / veicolo',veh); top.addRow('Numero',num); top.addRow('Data',de); top.addRow('Stato',st); root.addLayout(top)
        box=QGroupBox('Voci del preventivo'); g=QGridLayout(box); desc=QLineEdit(); qty=QDoubleSpinBox(); qty.setRange(0.01,99999); qty.setValue(1); qty.setDecimals(2); price=QDoubleSpinBox(); price.setMaximum(9999999); price.setDecimals(2); vat=QDoubleSpinBox(); vat.setRange(0,100); vat.setValue(22); vat.setSuffix(' %'); vat.setDecimals(2); add=QPushButton('Aggiungi / aggiorna'); rem=QPushButton('Rimuovi')
        for col,(lab,w) in enumerate([('Descrizione',desc),('Q.tà',qty),('Prezzo netto €',price),('IVA %',vat)]): g.addWidget(QLabel(lab),0,col); g.addWidget(w,1,col)
        g.addWidget(add,1,4); g.addWidget(rem,1,5)
        items=QTableWidget(); items.setColumnCount(7); items.setHorizontalHeaderLabels(['Voce','Q.tà','Prezzo netto €','IVA %','Imponibile €','IVA €','Lordo €']); items.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); items.setSelectionBehavior(QAbstractItemView.SelectRows); items.setEditTriggers(QAbstractItemView.NoEditTriggers); g.addWidget(items,2,0,1,6); root.addWidget(box,1)
        sums=QHBoxLayout(); sums.addStretch(); net_lab=QLabel(); iva_lab=QLabel(); total_lab=QLabel()
        for lab in (net_lab,iva_lab,total_lab): lab.setStyleSheet('font-size:16px;font-weight:750;color:#10233B;padding:5px 10px;'); sums.addWidget(lab)
        total_lab.setStyleSheet(f'font-size:19px;font-weight:850;color:{RED};padding:5px 10px;'); root.addLayout(sums)
        notes=QTextEdit(); notes.setPlaceholderText('Note generali del preventivo'); notes.setFixedHeight(85); root.addWidget(notes)
        def refresh_total():
            net=sum(float(items.item(r,4).text()) for r in range(items.rowCount())); iva=sum(float(items.item(r,5).text()) for r in range(items.rowCount())); gross=sum(float(items.item(r,6).text()) for r in range(items.rowCount())); net_lab.setText(f'Imponibile: € {net:.2f}'); iva_lab.setText(f'IVA: € {iva:.2f}'); total_lab.setText(f'Totale: € {gross:.2f}'); return net,iva,gross
        def add_item():
            if not desc.text().strip(): return
            net,iva,gross=calc_line(qty.value(),price.value(),vat.value()); row=items.currentRow()
            if row<0: row=items.rowCount(); items.insertRow(row)
            vals=[desc.text().strip(),f'{qty.value():.2f}',f'{price.value():.2f}',f'{vat.value():.2f}',f'{net:.2f}',f'{iva:.2f}',f'{gross:.2f}']
            for c,val in enumerate(vals): items.setItem(row,c,QTableWidgetItem(val))
            desc.clear(); qty.setValue(1); price.setValue(0); vat.setValue(22); items.clearSelection(); refresh_total()
        def load_item():
            r=items.currentRow()
            if r>=0: desc.setText(items.item(r,0).text()); qty.setValue(float(items.item(r,1).text())); price.setValue(float(items.item(r,2).text())); vat.setValue(float(items.item(r,3).text()))
        def remove_item():
            r=items.currentRow()
            if r>=0: items.removeRow(r); refresh_total()
        add.clicked.connect(add_item); items.itemSelectionChanged.connect(load_item); rem.clicked.connect(remove_item)
        if qid:
            q=self.db.one('SELECT * FROM quotes WHERE id=?',(qid,)); veh.setCurrentIndex(max(0,veh.findData(q['vehicle_id']))); num.setText(q['number']); de.setDate(QDate.fromString(q['created'],'yyyy-MM-dd')); st.setCurrentText(q['status']); notes.setPlainText(q['notes'] or '')
            for it in self.db.q('SELECT * FROM quote_items WHERE quote_id=? ORDER BY id',(qid,)):
                net=float(it['net_total'] or 0); iva=float(it['vat_amount'] or 0); gross=float(it['gross_total'] or 0)
                if gross==0 and float(it['line_total'] or 0)!=0: net=float(it['line_total']); gross=net
                r=items.rowCount(); items.insertRow(r); vals=[it['description'],f"{it['qty']:.2f}",f"{it['unit_price']:.2f}",f"{float(it['vat_rate'] or 0):.2f}",f"{net:.2f}",f"{iva:.2f}",f"{gross:.2f}"]
                for c,val in enumerate(vals): items.setItem(r,c,QTableWidgetItem(val))
            refresh_total()
        save=QPushButton('Salva preventivo'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:10px 18px;border-radius:7px;'); root.addWidget(save,0,Qt.AlignRight)
        def do_save():
            if items.rowCount()==0:return QMessageBox.warning(d,'Preventivo','Aggiungi almeno una voce.')
            _,_,gross=refresh_total(); vals=(num.text().strip(),veh.currentData(),de.date().toString('yyyy-MM-dd'),st.currentText(),gross,notes.toPlainText().strip())
            if qid: self.db.ex('UPDATE quotes SET number=?,vehicle_id=?,created=?,status=?,total=?,notes=? WHERE id=?',vals+(qid,)); qid2=qid; self.db.ex('DELETE FROM quote_items WHERE quote_id=?',(qid2,))
            else: qid2=self.db.ex('INSERT INTO quotes(number,vehicle_id,created,status,total,notes) VALUES(?,?,?,?,?,?)',vals).lastrowid
            for r in range(items.rowCount()):
                self.db.ex('''INSERT INTO quote_items(quote_id,description,qty,unit_price,line_total,vat_rate,net_total,vat_amount,gross_total) VALUES(?,?,?,?,?,?,?,?,?)''',(qid2,items.item(r,0).text(),float(items.item(r,1).text()),float(items.item(r,2).text()),float(items.item(r,6).text()),float(items.item(r,3).text()),float(items.item(r,4).text()),float(items.item(r,5).text()),float(items.item(r,6).text())))
            d.accept(); self.show_quotes()
        save.clicked.connect(do_save); d.exec()

    def print_quote(self,qid):
        if not qid:return
        r=self.db.one('''SELECT q.*,v.plate,v.brand,v.model,v.year,c.name client,c.phone,c.email FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id JOIN clients c ON c.id=v.client_id WHERE q.id=?''',(qid,)); its=self.db.q('SELECT * FROM quote_items WHERE quote_id=? ORDER BY id',(qid,)); p=self.make_pdf_path(f"Preventivo_{r['number']}"); c=pdfcanvas.Canvas(str(p),pagesize=A4); W,H=A4; y=self.pdf_header(c,'PREVENTIVO')
        c.setFont('Helvetica-Bold',10); c.drawString(16*mm,y,f"N. {r['number']}   Data: {r['created']}   Stato: {r['status']}"); y-=9*mm; c.setFont('Helvetica',9); c.drawString(16*mm,y,f"Cliente: {r['client']}  Tel: {r['phone'] or '-'}  Email: {r['email'] or '-'}"); y-=6*mm; c.drawString(16*mm,y,f"Veicolo: {r['brand']} {r['model']}  Targa: {r['plate']}  Anno: {r['year'] or '-'}"); y-=12*mm
        headers=[('Descrizione',16),('Q.tà',112),('Netto',135),('IVA %',156),('IVA €',176),('Lordo',198)]; c.setFont('Helvetica-Bold',7)
        for h,x in headers: c.drawRightString(x*mm,y,h) if x>20 else c.drawString(x*mm,y,h)
        y-=4*mm; c.line(16*mm,y,198*mm,y); y-=6*mm; c.setFont('Helvetica',7.5); net=iva=gross=0.0
        for it in its:
            if y<38*mm: c.showPage(); y=H-20*mm; c.setFont('Helvetica',7.5)
            line_net=float(it['net_total'] or it['line_total'] or 0); line_iva=float(it['vat_amount'] or 0); line_gross=float(it['gross_total'] or it['line_total'] or 0)
            c.drawString(16*mm,y,str(it['description'])[:60]); c.drawRightString(112*mm,y,f"{it['qty']:.2f}"); c.drawRightString(135*mm,y,f"€ {it['unit_price']:.2f}"); c.drawRightString(156*mm,y,f"{float(it['vat_rate'] or 0):.2f}%"); c.drawRightString(176*mm,y,f"€ {line_iva:.2f}"); c.drawRightString(198*mm,y,f"€ {line_gross:.2f}"); y-=6*mm; net+=line_net; iva+=line_iva; gross+=line_gross
        y-=5*mm; c.setFont('Helvetica-Bold',10); c.drawRightString(198*mm,y,f"Imponibile: € {net:.2f}"); y-=6*mm; c.drawRightString(198*mm,y,f"IVA: € {iva:.2f}"); y-=7*mm; c.setFillColor(colors.HexColor(RED)); c.setFont('Helvetica-Bold',13); c.drawRightString(198*mm,y,f"TOTALE: € {gross:.2f}"); c.setFillColor(colors.black); y-=12*mm; c.setFont('Helvetica',9); c.drawString(16*mm,y,'Note: '+str(r['notes'] or '')[:140]); c.save(); self.open_pdf(p)


__all__ = [
    'AppWindow','APP_VERSION','ensure_final_schema','ensure_customer_type_schema',
    'ensure_company_schema','ensure_fatturapa_schema','ensure_users_schema',
    'PAYMENT_CHOICES','FISCAL_REGIMES','LEGAL_TYPES','calc_line'
]
