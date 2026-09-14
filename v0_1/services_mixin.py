from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class ServicesMixin:
    def show_services(self):
        self.set_nav('Tagliandi'); p=TablePage(self,'Tagliandi','Storico olio, filtri e chilometraggio'); p.add_btn('Nuovo',lambda:self.service_dialog(),True); p.add_btn('Modifica',lambda:self.service_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_service(p)); p.add_btn('Stampa selezionato',lambda:self.print_service(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_services)
        rows=self.db.q('''SELECT s.*,v.plate,c.name client FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY s.service_date DESC'''); p.populate(['ID','Data','Targa','Cliente','Km','Olio','Prossimo km','Note'],[[r['id'],r['service_date'],r['plate'],r['client'],r['km'],r['engine_oil'],r['next_service_km'],r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.service_dialog(p.selected_id())); self._set_page(p)

    def service_dialog(self,sid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Tagliandi','Crea prima un veicolo.')
        d=BaseDialog('Tagliando',self); f=QFormLayout(d); veh=self.vehicle_combo(d); de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); km=QSpinBox(); km.setMaximum(2_000_000); oil=QLineEdit(); fo=QCheckBox('Filtro olio'); fa=QCheckBox('Filtro aria'); ff=QCheckBox('Filtro carburante'); fc=QCheckBox('Filtro abitacolo'); filters=QWidget(); fl=QHBoxLayout(filters); fl.setContentsMargins(0,0,0,0); [fl.addWidget(x) for x in (fo,fa,ff,fc)]; other=QLineEdit(); nxt=QSpinBox(); nxt.setMaximum(2_000_000); notes=QTextEdit(); notes.setFixedHeight(80)
        for lab,w in [('Veicolo',veh),('Data tagliando',de),('Km attuali',km),('Olio motore / gradazione',oil),('Filtri sostituiti',filters),('Altri filtri / materiali',other),('Prossimo tagliando a km',nxt),('Note',notes)]: f.addRow(lab,w)
        if sid:
            r=self.db.one('SELECT * FROM services WHERE id=?',(sid,)); veh.setCurrentIndex(max(0,veh.findData(r['vehicle_id']))); de.setDate(QDate.fromString(r['service_date'],'yyyy-MM-dd')); km.setValue(r['km'] or 0); oil.setText(r['engine_oil'] or ''); fo.setChecked(bool(r['oil_filter'])); fa.setChecked(bool(r['air_filter'])); ff.setChecked(bool(r['fuel_filter'])); fc.setChecked(bool(r['cabin_filter'])); other.setText(r['other_filters'] or ''); nxt.setValue(r['next_service_km'] or 0); notes.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            vals=(veh.currentData(),de.date().toString('yyyy-MM-dd'),km.value(),oil.text(),int(fo.isChecked()),int(fa.isChecked()),int(ff.isChecked()),int(fc.isChecked()),other.text(),nxt.value(),notes.toPlainText()); self.db.ex('UPDATE services SET vehicle_id=?,service_date=?,km=?,engine_oil=?,oil_filter=?,air_filter=?,fuel_filter=?,cabin_filter=?,other_filters=?,next_service_km=?,notes=? WHERE id=?',vals+(sid,)) if sid else self.db.ex('INSERT INTO services(vehicle_id,service_date,km,engine_oil,oil_filter,air_filter,fuel_filter,cabin_filter,other_filters,next_service_km,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?)',vals); self.db.ex('UPDATE vehicles SET km=MAX(km,?) WHERE id=?',(km.value(),veh.currentData())); d.accept(); self.show_services()
        b.clicked.connect(save); d.exec()

    def delete_service(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM services WHERE id=?',(x,)); self.show_services()

    def print_services(self):
        rows=self.db.q('''SELECT s.service_date,v.plate,c.name client,s.km,s.engine_oil,s.next_service_km,s.notes FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY s.service_date DESC'''); self.print_table_pdf('SITUAZIONE TAGLIANDI',['Data','Targa','Cliente','Km','Olio','Prossimo km','Note'],[[r[k] for k in ['service_date','plate','client','km','engine_oil','next_service_km','notes']] for r in rows],'Tagliandi')

    def print_service(self,sid):
        if not sid:return
        r=self.db.one('''SELECT s.*,v.plate,v.brand,v.model,c.name client,c.phone,c.email FROM services s JOIN vehicles v ON v.id=s.vehicle_id JOIN clients c ON c.id=v.client_id WHERE s.id=?''',(sid,)); p=self.make_pdf_path('Tagliando'); c=pdfcanvas.Canvas(str(p),pagesize=A4); y=self.pdf_header(c,'SCHEDA TAGLIANDO');
        pairs=[('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Targa',r['plate']),('Veicolo',f"{r['brand']} {r['model']}"),('Data',r['service_date']),('Km',r['km']),('Olio',r['engine_oil']),('Prossimo tagliando km',r['next_service_km']),('Note',r['notes'])]
        for k,v in pairs: c.setFont('Helvetica-Bold',9); c.drawString(16*mm,y,k); c.setFont('Helvetica',10); c.drawString(65*mm,y,str(v or '')); y-=8*mm
        c.save(); self.open_pdf(p)
