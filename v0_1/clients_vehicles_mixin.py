from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class ClientsVehiclesMixin:
    def show_clients(self):
        self.set_nav('Clienti'); p=TablePage(self,'Clienti','Anagrafica clienti'); p.add_btn('Nuovo',lambda:self.client_dialog(),True); p.add_btn('Modifica',lambda:self.client_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_client(p)); p.add_btn('Stampa situazione PDF',self.print_clients)
        rows=self.db.q('SELECT * FROM clients ORDER BY name'); p.populate(['ID','Cliente','Telefono','Email','Note'],[[r['id'],r['name'],r['phone'],r['email'],r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.client_dialog(p.selected_id())); self._set_page(p)

    def client_dialog(self,cid=None):
        d=BaseDialog('Cliente',self); f=QFormLayout(d); name=QLineEdit(); phone=QLineEdit(); email=QLineEdit(); notes=QTextEdit(); notes.setFixedHeight(90); f.addRow('Nome / Ragione sociale',name); f.addRow('Telefono',phone); f.addRow('Email',email); f.addRow('Note',notes)
        if cid:
            r=self.db.one('SELECT * FROM clients WHERE id=?',(cid,)); name.setText(r['name']); phone.setText(r['phone'] or ''); email.setText(r['email'] or ''); notes.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            if not name.text().strip(): return
            vals=(name.text().strip(),phone.text().strip(),email.text().strip(),notes.toPlainText().strip())
            self.db.ex('UPDATE clients SET name=?,phone=?,email=?,notes=? WHERE id=?',vals+(cid,)) if cid else self.db.ex('INSERT INTO clients(name,phone,email,notes) VALUES(?,?,?,?)',vals); d.accept(); self.show_clients()
        b.clicked.connect(save); d.exec()

    def delete_client(self,p):
        x=p.selected_id();
        if x and self.confirm_delete('Eliminare cliente e dati collegati?'): self.db.ex('DELETE FROM clients WHERE id=?',(x,)); self.show_clients()

    def print_clients(self):
        rows=self.db.q('SELECT name,phone,email,notes FROM clients ORDER BY name'); self.print_table_pdf('SITUAZIONE CLIENTI',['Cliente','Telefono','Email','Note'],[[r[k] for k in ['name','phone','email','notes']] for r in rows],'Clienti')

    def show_vehicles(self):
        self.set_nav('Veicoli'); p=TablePage(self,'Veicoli','Archivio mezzi con marca e modello da database locale'); p.add_btn('Nuovo',lambda:self.vehicle_dialog(),True); p.add_btn('Modifica',lambda:self.vehicle_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_vehicle(p)); p.add_btn('Stampa situazione PDF',self.print_vehicles)
        rows=self.db.q('''SELECT v.*,c.name client FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate'''); p.populate(['ID','Targa','Marca','Modello','Anno','Cliente','Km','VIN'],[[r['id'],r['plate'],r['brand'],r['model'],r['year'],r['client'],r['km'],r['vin']] for r in rows]); p.table.doubleClicked.connect(lambda:self.vehicle_dialog(p.selected_id())); self._set_page(p)

    def vehicle_dialog(self,vid=None):
        clients=self.db.q('SELECT id,name FROM clients ORDER BY name')
        if not clients: return QMessageBox.information(self,'Veicoli','Crea prima un cliente.')
        d=BaseDialog('Veicolo',self); f=QFormLayout(d); client=QComboBox();
        for r in clients: client.addItem(r['name'],r['id'])
        plate=QLineEdit(); brand=QComboBox(); model=QComboBox(); brand.addItems([r['name'] for r in self.db.q('SELECT name FROM car_makes ORDER BY name')]); year=QLineEdit(); km=QSpinBox(); km.setMaximum(2_000_000); vin=QLineEdit()
        def models():
            model.clear(); rs=self.db.q('''SELECT cm.name FROM car_models cm JOIN car_makes mk ON mk.id=cm.make_id WHERE mk.name=? ORDER BY cm.name''',(brand.currentText(),)); model.addItems([r['name'] for r in rs])
        brand.currentTextChanged.connect(models); models()
        for lab,w in [('Cliente proprietario',client),('Targa',plate),('Marca',brand),('Modello',model),('Anno vettura',year),('Km',km),('VIN / Telaio',vin)]: f.addRow(lab,w)
        if vid:
            r=self.db.one('SELECT * FROM vehicles WHERE id=?',(vid,)); client.setCurrentIndex(max(0,client.findData(r['client_id']))); plate.setText(r['plate']); brand.setCurrentText(r['brand'] or ''); models(); model.setCurrentText(r['model'] or ''); year.setText(r['year'] or ''); km.setValue(r['km'] or 0); vin.setText(r['vin'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            if not plate.text().strip() or not brand.currentText() or not model.currentText(): return QMessageBox.warning(d,'Dati mancanti','Inserisci targa, marca e modello.')
            vals=(client.currentData(),plate.text().strip().upper(),brand.currentText(),model.currentText(),year.text().strip(),km.value(),vin.text().strip())
            try:self.db.ex('UPDATE vehicles SET client_id=?,plate=?,brand=?,model=?,year=?,km=?,vin=? WHERE id=?',vals+(vid,)) if vid else self.db.ex('INSERT INTO vehicles(client_id,plate,brand,model,year,km,vin) VALUES(?,?,?,?,?,?,?)',vals)
            except Exception as e:return QMessageBox.critical(d,'Errore',str(e))
            d.accept(); self.show_vehicles()
        b.clicked.connect(save); d.exec()

    def delete_vehicle(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM vehicles WHERE id=?',(x,)); self.show_vehicles()

    def print_vehicles(self):
        rows=self.db.q('''SELECT v.plate,v.brand,v.model,v.year,c.name client,v.km,v.vin FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate'''); self.print_table_pdf('SITUAZIONE VEICOLI',['Targa','Marca','Modello','Anno','Cliente','Km','VIN'],[[r[k] for k in ['plate','brand','model','year','client','km','vin']] for r in rows],'Veicoli')
