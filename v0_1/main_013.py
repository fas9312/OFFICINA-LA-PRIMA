import os, sys, sqlite3, calendar
from datetime import date, datetime

from PySide6.QtCore import Qt, QDate, QTime, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

import dashboard_mixin
from core import *
from main_011 import AppWindow as AppWindow012, UI_LOGO


def ensure_schema_013():
    """Non-destructive migration from 0.1.2."""
    conn = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in conn.execute('PRAGMA table_info(services)').fetchall()}
    added_status = False
    if 'service_time' not in cols:
        conn.execute("ALTER TABLE services ADD COLUMN service_time TEXT DEFAULT '09:00'")
    if 'status' not in cols:
        conn.execute("ALTER TABLE services ADD COLUMN status TEXT DEFAULT 'Eseguito'")
        added_status = True
    if added_status:
        # Existing future tagliandi from 0.1.2 were necessarily intended as scheduled work.
        conn.execute("UPDATE services SET status='Programmato' WHERE service_date >= date('now')")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            qty REAL NOT NULL DEFAULT 1,
            unit_net REAL NOT NULL DEFAULT 0,
            vat_rate REAL NOT NULL DEFAULT 22,
            net_total REAL NOT NULL DEFAULT 0,
            vat_amount REAL NOT NULL DEFAULT 0,
            gross_total REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        )
    ''')
    conn.commit(); conn.close()


class UnifiedDayCell(QFrame):
    clicked = Signal(str)
    def __init__(self, ds, day, today=False, events=None):
        super().__init__(); self.ds = ds
        self.setMinimumHeight(82)
        self.setStyleSheet('QFrame{background:rgba(255,255,255,76);border:1px solid rgba(150,170,190,130);border-radius:0;} QLabel{border:0;background:transparent;}')
        v = QVBoxLayout(self); v.setContentsMargins(5,4,5,4); v.setSpacing(2)
        d = QLabel(str(day)); d.setFixedWidth(28)
        d.setStyleSheet('background:#0D6FD8;color:white;border-radius:4px;padding:2px 5px;font-weight:700;' if today else 'color:#10233B;font-weight:700;')
        v.addWidget(d,0,Qt.AlignLeft)
        for ev in (events or [])[:3]:
            typ = ev.get('event_type','Appuntamento')
            if typ == 'Tagliando':
                text = ' '.join(x for x in [ev.get('time',''), 'TAGLIANDO', ev.get('plate','')] if x)
                bg, fg = '#D8EAFF', '#0756A1'
            else:
                text = ' '.join(x for x in [ev.get('time',''), ev.get('plate',''), ev.get('title','')] if x)
                bg, fg = '#DDF5E9', '#087A52'
            if len(text) > 27: text = text[:26] + '…'
            lab = QLabel(text); lab.setToolTip(text)
            lab.setStyleSheet(f'background:{bg};color:{fg};border-radius:5px;padding:2px 4px;font-size:10px;')
            v.addWidget(lab)
        v.addStretch()
    def mousePressEvent(self,e):
        if e.button() == Qt.LeftButton: self.clicked.emit(self.ds)
        super().mousePressEvent(e)


class UnifiedDashboardCalendar(GlassFrame):
    dateClicked = Signal(str)
    def __init__(self, db):
        super().__init__(170); self.db=db; self.year=date.today().year; self.month=date.today().month
        self.root=QVBoxLayout(self); self.root.setContentsMargins(16,14,16,14)
        bar=QHBoxLayout(); self.title=QLabel(); self.title.setStyleSheet('font-size:23px;font-weight:800;color:#10233B;')
        self.prev=QPushButton('‹'); self.next=QPushButton('›'); self.today=QPushButton('Oggi')
        for b in (self.prev,self.next):
            b.setFixedSize(38,34); b.setStyleSheet('background:rgba(240,244,248,220);border:0;border-radius:6px;font-size:20px;font-weight:700;')
        self.today.setStyleSheet(f'background:{RED};color:white;border:0;border-radius:6px;padding:8px 14px;font-weight:700;')
        self.prev.clicked.connect(lambda:self.shift(-1)); self.next.clicked.connect(lambda:self.shift(1)); self.today.clicked.connect(self.go_today)
        bar.addWidget(self.title); bar.addStretch(); bar.addWidget(self.prev); bar.addWidget(self.next); bar.addWidget(self.today); self.root.addLayout(bar)
        self.gridw=QWidget(); self.gridw.setStyleSheet('background:transparent;'); self.grid=QGridLayout(self.gridw); self.grid.setContentsMargins(0,6,0,0); self.grid.setSpacing(1); self.root.addWidget(self.gridw)
        self.refresh()
    def clear_grid(self):
        while self.grid.count():
            it=self.grid.takeAt(0); w=it.widget()
            if w: w.deleteLater()
    def refresh(self):
        self.clear_grid(); self.title.setText(f'{MONTHS[self.month-1]} {self.year}')
        for i,n in enumerate(['Lun','Mar','Mer','Gio','Ven','Sab','Dom']):
            lab=QLabel(n); lab.setAlignment(Qt.AlignCenter); lab.setStyleSheet('font-weight:700;color:#20364C;background:rgba(235,241,246,170);padding:5px;border:0;'); self.grid.addWidget(lab,0,i)
        last=calendar.monthrange(self.year,self.month)[1]
        start=f'{self.year:04d}-{self.month:02d}-01'; end=f'{self.year:04d}-{self.month:02d}-{last:02d}'
        by={}
        appointments=self.db.q('''SELECT a.date,a.time,a.reason,v.plate FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id WHERE a.date BETWEEN ? AND ? ORDER BY a.date,a.time''',(start,end))
        for r in appointments:
            by.setdefault(r['date'],[]).append({'time':r['time'] or '', 'title':r['reason'] or 'Appuntamento', 'plate':r['plate'] or '', 'event_type':'Appuntamento'})
        services=self.db.q('''SELECT s.service_date,s.service_time,v.plate FROM services s JOIN vehicles v ON v.id=s.vehicle_id WHERE s.status='Programmato' AND s.service_date BETWEEN ? AND ? ORDER BY s.service_date,s.service_time''',(start,end))
        for r in services:
            by.setdefault(r['service_date'],[]).append({'time':r['service_time'] or '', 'title':'Tagliando programmato', 'plate':r['plate'] or '', 'event_type':'Tagliando'})
        for events in by.values(): events.sort(key=lambda x:(x.get('time',''),x.get('event_type','')))
        weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(self.year,self.month)
        while len(weeks)<6: weeks.append([0]*7)
        td=date.today()
        for rr,wk in enumerate(weeks[:6],1):
            for cc,day in enumerate(wk):
                if day:
                    ds=f'{self.year:04d}-{self.month:02d}-{day:02d}'
                    cell=UnifiedDayCell(ds,day,td==date(self.year,self.month,day),by.get(ds,[])); cell.clicked.connect(self.dateClicked); self.grid.addWidget(cell,rr,cc)
                else:
                    blank=QFrame(); blank.setStyleSheet('background:rgba(255,255,255,42);border:1px solid rgba(150,170,190,90);'); blank.setMinimumHeight(82); self.grid.addWidget(blank,rr,cc)
            self.grid.setRowStretch(rr,1)
        for c in range(7): self.grid.setColumnStretch(c,1)
    def shift(self,n):
        self.month += n
        if self.month < 1: self.month=12; self.year-=1
        if self.month > 12: self.month=1; self.year+=1
        self.refresh()
    def go_today(self):
        self.year=date.today().year; self.month=date.today().month; self.refresh()


class AppWindow(AppWindow012):
    def __init__(self):
        ensure_schema_013()
        dashboard_mixin.DashboardCalendar = UnifiedDashboardCalendar
        super().__init__()
        self.setWindowTitle('LA PRIMA Garage Manager 0.1.3')

    def _build_ui(self):
        super()._build_ui()
        # Keep the real logo, but make the workshop name readable independently of image details.
        for brand in self.findChildren(QLabel):
            if brand.toolTip() == 'Logo ufficiale Officina LA PRIMA':
                pm=QPixmap(UI_LOGO)
                if not pm.isNull():
                    brand.setPixmap(pm.scaled(235,100,Qt.KeepAspectRatio,Qt.SmoothTransformation))
                    brand.setAlignment(Qt.AlignHCenter|Qt.AlignTop)
                title=QLabel(brand); title.setObjectName('ReadableBrandText'); title.setTextFormat(Qt.RichText)
                title.setText('<div style="text-align:center;font-weight:900;font-size:18px;color:white;">OFFICINA<br><span style="color:#FF3647;font-size:21px;">“LA PRIMA”</span></div>')
                title.setAlignment(Qt.AlignCenter); title.setGeometry(4,92,247,62)
                title.setStyleSheet('background:rgba(18,38,58,225);border-radius:8px;padding:2px;')
                title.show(); title.raise_(); break

    # ---------- TAGLIANDI PROGRAMMATI = EVENTI CALENDARIO ----------
    def show_services(self):
        self.set_nav('Tagliandi'); p=TablePage(self,'Tagliandi','Tagliandi programmati e storico interventi')
        p.add_btn('Nuovo',lambda:self.service_dialog(),True); p.add_btn('Modifica',lambda:self.service_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_service(p)); p.add_btn('Stampa selezionato',lambda:self.print_service(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_services)
        rows=self.db.q('''SELECT s.*,v.plate,c.name client FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY s.service_date DESC,s.service_time DESC''')
        p.populate(['ID','Stato','Data','Ora','Targa','Cliente','Km','Olio','Prossimo km','Note'],[[r['id'],r['status'],r['service_date'],r['service_time'],r['plate'],r['client'],r['km'],r['engine_oil'],r['next_service_km'],r['notes']] for r in rows])
        p.table.doubleClicked.connect(lambda:self.service_dialog(p.selected_id())); self._set_page(p)

    def service_dialog(self,sid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Tagliandi','Crea prima un veicolo.')
        d=BaseDialog('Tagliando',self); d.setMinimumWidth(650); f=QFormLayout(d)
        veh=self.vehicle_combo(d); status=QComboBox(); status.addItems(['Programmato','Eseguito']); de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); ti=QTimeEdit(QTime(9,0))
        km=QSpinBox(); km.setMaximum(2_000_000); oil=QLineEdit(); fo=QCheckBox('Filtro olio'); fa=QCheckBox('Filtro aria'); ff=QCheckBox('Filtro carburante'); fc=QCheckBox('Filtro abitacolo')
        filters=QWidget(); fl=QHBoxLayout(filters); fl.setContentsMargins(0,0,0,0); [fl.addWidget(x) for x in (fo,fa,ff,fc)]
        other=QLineEdit(); nxt=QSpinBox(); nxt.setMaximum(2_000_000); notes=QTextEdit(); notes.setFixedHeight(80)
        for lab,w in [('Veicolo',veh),('Stato',status),('Data tagliando / appuntamento',de),('Ora',ti),('Km attuali',km),('Olio motore / gradazione',oil),('Filtri sostituiti',filters),('Altri filtri / materiali',other),('Prossimo tagliando a km',nxt),('Note',notes)]: f.addRow(lab,w)
        if sid:
            r=self.db.one('SELECT * FROM services WHERE id=?',(sid,)); veh.setCurrentIndex(max(0,veh.findData(r['vehicle_id']))); status.setCurrentText(r['status'] or 'Eseguito'); de.setDate(QDate.fromString(r['service_date'],'yyyy-MM-dd')); ti.setTime(QTime.fromString(r['service_time'] or '09:00','HH:mm')); km.setValue(r['km'] or 0); oil.setText(r['engine_oil'] or ''); fo.setChecked(bool(r['oil_filter'])); fa.setChecked(bool(r['air_filter'])); ff.setChecked(bool(r['fuel_filter'])); fc.setChecked(bool(r['cabin_filter'])); other.setText(r['other_filters'] or ''); nxt.setValue(r['next_service_km'] or 0); notes.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            vals=(veh.currentData(),status.currentText(),de.date().toString('yyyy-MM-dd'),ti.time().toString('HH:mm'),km.value(),oil.text(),int(fo.isChecked()),int(fa.isChecked()),int(ff.isChecked()),int(fc.isChecked()),other.text(),nxt.value(),notes.toPlainText())
            if sid: self.db.ex('UPDATE services SET vehicle_id=?,status=?,service_date=?,service_time=?,km=?,engine_oil=?,oil_filter=?,air_filter=?,fuel_filter=?,cabin_filter=?,other_filters=?,next_service_km=?,notes=? WHERE id=?',vals+(sid,))
            else: self.db.ex('INSERT INTO services(vehicle_id,status,service_date,service_time,km,engine_oil,oil_filter,air_filter,fuel_filter,cabin_filter,other_filters,next_service_km,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',vals)
            if status.currentText()=='Eseguito': self.db.ex('UPDATE vehicles SET km=MAX(km,?) WHERE id=?',(km.value(),veh.currentData()))
            d.accept(); self.show_services()
        b.clicked.connect(save); d.exec()

    def print_services(self):
        rows=self.db.q('''SELECT s.status,s.service_date,s.service_time,v.plate,c.name client,s.km,s.engine_oil,s.next_service_km,s.notes FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY s.service_date DESC''')
        self.print_table_pdf('SITUAZIONE TAGLIANDI',['Stato','Data','Ora','Targa','Cliente','Km','Olio','Prossimo km','Note'],[[r[k] for k in ['status','service_date','service_time','plate','client','km','engine_oil','next_service_km','notes']] for r in rows],'Tagliandi')

    def print_service(self,sid):
        if not sid:return
        r=self.db.one('''SELECT s.*,v.plate,v.brand,v.model,c.name client,c.phone,c.email FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id WHERE s.id=?''',(sid,)); p=self.make_pdf_path('Tagliando'); c=pdfcanvas.Canvas(str(p),pagesize=A4); y=self.pdf_header(c,'SCHEDA TAGLIANDO')
        pairs=[('Stato',r['status']),('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Targa',r['plate']),('Veicolo',f"{r['brand']} {r['model']}"),('Data',r['service_date']),('Ora',r['service_time']),('Km',r['km']),('Olio',r['engine_oil']),('Prossimo tagliando km',r['next_service_km']),('Note',r['notes'])]
        for k,v in pairs: c.setFont('Helvetica-Bold',9); c.drawString(16*mm,y,k); c.setFont('Helvetica',10); c.drawString(65*mm,y,str(v or '')); y-=8*mm
        c.save(); self.open_pdf(p)

    # ---------- FATTURE A RIGHE CON IVA ----------
    def show_invoices(self):
        self.set_nav('Fatture'); p=TablePage(self,'Fatture','Fatture a righe con imponibile, IVA e totale automatici')
        p.add_btn('Nuova',lambda:self.invoice_dialog(),True); p.add_btn('Modifica',lambda:self.invoice_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_invoice(p)); p.add_btn('Stampa fattura selezionata',lambda:self.print_invoice_selected(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_invoices)
        rows=self.db.q('''SELECT i.*,v.plate,c.name client FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY i.id DESC''')
        p.populate(['ID','Numero','Data','Targa','Cliente','Stato','Totale lordo €','Note'],[[r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],f"{r['total']:.2f}",r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.invoice_dialog(p.selected_id())); self._set_page(p)

    def invoice_dialog(self,iid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Fatture','Crea prima un veicolo.')
        d=BaseDialog('Fattura',self); d.resize(1080,760); root=QVBoxLayout(d)
        top=QFormLayout(); veh=self.vehicle_combo(d); num=QLineEdit(self.next_number('invoices','FAT')); de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); st=QComboBox(); st.addItems(['Bozza','Emessa','Pagata','Annullata'])
        top.addRow('Cliente / veicolo',veh); top.addRow('Numero fattura',num); top.addRow('Data',de); top.addRow('Stato',st); root.addLayout(top)
        box=QGroupBox('Righe fattura'); g=QGridLayout(box)
        desc=QLineEdit(); qty=QDoubleSpinBox(); qty.setRange(0.01,99999); qty.setValue(1); qty.setDecimals(2); unit=QDoubleSpinBox(); unit.setRange(0,9999999); unit.setDecimals(2); vat=QDoubleSpinBox(); vat.setRange(0,100); vat.setValue(22); vat.setSuffix(' %'); vat.setDecimals(2)
        add=QPushButton('Aggiungi / aggiorna riga'); rem=QPushButton('Rimuovi riga')
        for col,(lab,w) in enumerate([('Descrizione',desc),('Q.tà',qty),('Prezzo netto €',unit),('IVA %',vat)]): g.addWidget(QLabel(lab),0,col); g.addWidget(w,1,col)
        g.addWidget(add,1,4); g.addWidget(rem,1,5)
        items=QTableWidget(); items.setColumnCount(7); items.setHorizontalHeaderLabels(['Descrizione','Q.tà','Prezzo netto €','IVA %','Imponibile €','IVA €','Lordo €']); items.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); items.setSelectionBehavior(QAbstractItemView.SelectRows); items.setEditTriggers(QAbstractItemView.NoEditTriggers); g.addWidget(items,2,0,1,6); root.addWidget(box,1)
        sums=QHBoxLayout(); sums.addStretch(); net_lab=QLabel(); vat_lab=QLabel(); gross_lab=QLabel();
        for lab in (net_lab,vat_lab,gross_lab): lab.setStyleSheet('font-size:16px;font-weight:750;color:#10233B;padding:5px 10px;'); sums.addWidget(lab)
        gross_lab.setStyleSheet(f'font-size:19px;font-weight:850;color:{RED};padding:5px 10px;'); root.addLayout(sums)
        notes=QTextEdit(); notes.setPlaceholderText('Note fattura'); notes.setFixedHeight(80); root.addWidget(notes)
        def totals():
            n=sum(float(items.item(r,4).text()) for r in range(items.rowCount())); iv=sum(float(items.item(r,5).text()) for r in range(items.rowCount())); gr=sum(float(items.item(r,6).text()) for r in range(items.rowCount())); net_lab.setText(f'Imponibile: € {n:.2f}'); vat_lab.setText(f'IVA: € {iv:.2f}'); gross_lab.setText(f'Totale: € {gr:.2f}'); return n,iv,gr
        def add_item():
            if not desc.text().strip(): return QMessageBox.warning(d,'Fattura','Inserisci la descrizione della riga.')
            n=qty.value()*unit.value(); iv=n*vat.value()/100.0; gr=n+iv; row=items.currentRow()
            if row<0: row=items.rowCount(); items.insertRow(row)
            vals=[desc.text().strip(),f'{qty.value():.2f}',f'{unit.value():.2f}',f'{vat.value():.2f}',f'{n:.2f}',f'{iv:.2f}',f'{gr:.2f}']
            for c1,val in enumerate(vals): items.setItem(row,c1,QTableWidgetItem(val))
            desc.clear(); qty.setValue(1); unit.setValue(0); vat.setValue(22); items.clearSelection(); totals()
        def load_item():
            row=items.currentRow()
            if row>=0 and items.item(row,0): desc.setText(items.item(row,0).text()); qty.setValue(float(items.item(row,1).text())); unit.setValue(float(items.item(row,2).text())); vat.setValue(float(items.item(row,3).text()))
        def remove_item():
            row=items.currentRow()
            if row>=0: items.removeRow(row); totals()
        add.clicked.connect(add_item); rem.clicked.connect(remove_item); items.itemSelectionChanged.connect(load_item)
        if iid:
            inv=self.db.one('SELECT * FROM invoices WHERE id=?',(iid,)); veh.setCurrentIndex(max(0,veh.findData(inv['vehicle_id']))); num.setText(inv['number']); de.setDate(QDate.fromString(inv['created'],'yyyy-MM-dd')); st.setCurrentText(inv['status']); notes.setPlainText(inv['notes'] or '')
            old=self.db.q('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(iid,))
            if not old and (inv['total'] or 0)>0:
                old=[{'description':'Importo fattura precedente','qty':1.0,'unit_net':inv['total'],'vat_rate':0.0,'net_total':inv['total'],'vat_amount':0.0,'gross_total':inv['total']}]
            for it in old:
                row=items.rowCount(); items.insertRow(row); vals=[it['description'],f"{it['qty']:.2f}",f"{it['unit_net']:.2f}",f"{it['vat_rate']:.2f}",f"{it['net_total']:.2f}",f"{it['vat_amount']:.2f}",f"{it['gross_total']:.2f}"]
                for c1,val in enumerate(vals): items.setItem(row,c1,QTableWidgetItem(val))
        totals(); save=QPushButton('Salva fattura'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:10px 18px;border-radius:7px;'); root.addWidget(save,0,Qt.AlignRight)
        def do_save():
            if items.rowCount()==0: return QMessageBox.warning(d,'Fattura','Aggiungi almeno una riga.')
            _,_,gross=totals(); vals=(num.text().strip(),veh.currentData(),de.date().toString('yyyy-MM-dd'),st.currentText(),gross,notes.toPlainText().strip())
            if iid:
                self.db.ex('UPDATE invoices SET number=?,vehicle_id=?,created=?,status=?,total=?,notes=? WHERE id=?',vals+(iid,)); iid2=iid; self.db.ex('DELETE FROM invoice_items WHERE invoice_id=?',(iid2,))
            else: iid2=self.db.ex('INSERT INTO invoices(number,vehicle_id,created,status,total,notes) VALUES(?,?,?,?,?,?)',vals).lastrowid
            for r in range(items.rowCount()):
                self.db.ex('INSERT INTO invoice_items(invoice_id,description,qty,unit_net,vat_rate,net_total,vat_amount,gross_total) VALUES(?,?,?,?,?,?,?,?)',(iid2,items.item(r,0).text(),float(items.item(r,1).text()),float(items.item(r,2).text()),float(items.item(r,3).text()),float(items.item(r,4).text()),float(items.item(r,5).text()),float(items.item(r,6).text())))
            d.accept(); self.show_invoices()
        save.clicked.connect(do_save); d.exec()

    def print_invoice_selected(self,iid):
        if not iid:return QMessageBox.information(self,'PDF','Seleziona prima una fattura.')
        inv=self.db.one('''SELECT i.*,v.plate,v.brand,v.model,v.year,c.name client,c.phone,c.email FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''',(iid,)); its=self.db.q('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(iid,)); p=self.make_pdf_path(f"Fattura_{inv['number']}"); c=pdfcanvas.Canvas(str(p),pagesize=A4); W,H=A4; y=self.pdf_header(c,'FATTURA')
        c.setFont('Helvetica-Bold',10); c.drawString(16*mm,y,f"N. {inv['number']}   Data: {inv['created']}   Stato: {inv['status']}"); y-=8*mm; c.setFont('Helvetica',9); c.drawString(16*mm,y,f"Cliente: {inv['client']}   Tel: {inv['phone'] or '-'}   Email: {inv['email'] or '-'}"); y-=6*mm; c.drawString(16*mm,y,f"Veicolo: {inv['brand']} {inv['model']}   Targa: {inv['plate']}   Anno: {inv['year'] or '-'}"); y-=11*mm
        headers=[('Descrizione',16),('Q.tà',116),('Netto',137),('IVA %',158),('IVA €',176),('Lordo',198)]; c.setFont('Helvetica-Bold',7)
        for h,x in headers: c.drawRightString(x*mm,y,h) if x>20 else c.drawString(x*mm,y,h)
        y-=4*mm; c.line(16*mm,y,198*mm,y); y-=6*mm; c.setFont('Helvetica',7.5)
        net=iva=gross=0.0
        for it in its:
            if y<38*mm: c.showPage(); y=H-20*mm; c.setFont('Helvetica',7.5)
            c.drawString(16*mm,y,str(it['description'])[:62]); c.drawRightString(116*mm,y,f"{it['qty']:.2f}"); c.drawRightString(137*mm,y,f"€ {it['unit_net']:.2f}"); c.drawRightString(158*mm,y,f"{it['vat_rate']:.2f}%"); c.drawRightString(176*mm,y,f"€ {it['vat_amount']:.2f}"); c.drawRightString(198*mm,y,f"€ {it['gross_total']:.2f}"); y-=6*mm; net+=it['net_total']; iva+=it['vat_amount']; gross+=it['gross_total']
        if not its: gross=inv['total'] or 0; net=gross
        y-=5*mm; c.setFont('Helvetica-Bold',10); c.drawRightString(198*mm,y,f"Imponibile: € {net:.2f}"); y-=6*mm; c.drawRightString(198*mm,y,f"IVA: € {iva:.2f}"); y-=7*mm; c.setFillColor(colors.HexColor(RED)); c.setFont('Helvetica-Bold',13); c.drawRightString(198*mm,y,f"TOTALE: € {gross:.2f}"); c.setFillColor(colors.black); y-=12*mm; c.setFont('Helvetica',9); c.drawString(16*mm,y,'Note: '+str(inv['notes'] or '')[:140]); c.save(); self.open_pdf(p)


if __name__=='__main__':
    ensure_schema_013(); dashboard_mixin.DashboardCalendar=UnifiedDashboardCalendar
    app=QApplication(sys.argv); app.setApplicationName('LA PRIMA Garage Manager 0.1.3'); w=AppWindow(); w.show(); sys.exit(app.exec())
