from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class JobsAppointmentsMixin:
    def show_jobs(self):
        self.set_nav('Commesse'); p=TablePage(self,'Commesse','Lavorazioni officina'); p.add_btn('Nuova',lambda:self.job_dialog(),True); p.add_btn('Modifica',lambda:self.job_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_job(p)); p.add_btn('Stampa situazione PDF',self.print_jobs)
        rows=self.db.q('''SELECT j.*,v.plate,c.name client FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY j.id DESC'''); p.populate(['ID','Numero','Apertura','Targa','Cliente','Stato','Problema','Totale €'],[[r['id'],r['number'],r['opened'],r['plate'],r['client'],r['status'],r['issue'],f"{(r['labor']+r['parts']):.2f}"] for r in rows]); p.table.doubleClicked.connect(lambda:self.job_dialog(p.selected_id())); self._set_page(p)

    def job_dialog(self,jid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Commesse','Crea prima un veicolo.')
        d=BaseDialog('Commessa',self); d.setMinimumWidth(650); f=QFormLayout(d); veh=self.vehicle_combo(d); num=QLineEdit(self.next_number('jobs','LP')); opened=QDateEdit(QDate.currentDate()); opened.setCalendarPopup(True); status=QComboBox(); status.addItems(STATUSES); issue=QTextEdit(); diagnosis=QTextEdit(); labor=QDoubleSpinBox(); parts=QDoubleSpinBox(); notes=QTextEdit();
        for x in (labor,parts): x.setMaximum(999999); x.setDecimals(2)
        issue.setFixedHeight(70); diagnosis.setFixedHeight(70); notes.setFixedHeight(70)
        for lab,w in [('Veicolo',veh),('Numero commessa',num),('Data apertura',opened),('Stato',status),('Problema segnalato',issue),('Diagnosi',diagnosis),('Manodopera €',labor),('Ricambi €',parts),('Note',notes)]: f.addRow(lab,w)
        if jid:
            r=self.db.one('SELECT * FROM jobs WHERE id=?',(jid,)); veh.setCurrentIndex(max(0,veh.findData(r['vehicle_id']))); num.setText(r['number']); opened.setDate(QDate.fromString(r['opened'],'yyyy-MM-dd')); status.setCurrentText(r['status']); issue.setPlainText(r['issue'] or ''); diagnosis.setPlainText(r['diagnosis'] or ''); labor.setValue(r['labor'] or 0); parts.setValue(r['parts'] or 0); notes.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            vals=(num.text().strip(),veh.currentData(),opened.date().toString('yyyy-MM-dd'),issue.toPlainText(),diagnosis.toPlainText(),status.currentText(),labor.value(),parts.value(),notes.toPlainText())
            self.db.ex('UPDATE jobs SET number=?,vehicle_id=?,opened=?,issue=?,diagnosis=?,status=?,labor=?,parts=?,notes=? WHERE id=?',vals+(jid,)) if jid else self.db.ex('INSERT INTO jobs(number,vehicle_id,opened,issue,diagnosis,status,labor,parts,notes) VALUES(?,?,?,?,?,?,?,?,?)',vals); d.accept(); self.show_jobs()
        b.clicked.connect(save); d.exec()

    def delete_job(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM jobs WHERE id=?',(x,)); self.show_jobs()

    def print_jobs(self):
        rows=self.db.q('''SELECT j.number,j.opened,v.plate,c.name client,j.status,j.issue,j.labor+j.parts total FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY j.id DESC'''); self.print_table_pdf('SITUAZIONE COMMESSE',['Numero','Data','Targa','Cliente','Stato','Problema','Totale'],[[r[k] for k in ['number','opened','plate','client','status','issue','total']] for r in rows],'Commesse')

    def show_appointments(self):
        self.set_nav('Appuntamenti'); p=TablePage(self,'Appuntamenti','Agenda officina'); p.add_btn('Nuovo',lambda:self.appointment_dialog(),True); p.add_btn('Modifica',lambda:self.appointment_dialog(aid=p.selected_id())); p.add_btn('Elimina',lambda:self.delete_appointment(p)); p.add_btn('Stampa situazione PDF',self.print_appointments)
        rows=self.db.q('''SELECT a.*,v.plate,c.name client FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id ORDER BY a.date,a.time'''); p.populate(['ID','Data','Ora','Targa','Cliente','Motivo','Note'],[[r['id'],r['date'],r['time'],r['plate'],r['client'],r['reason'],r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.appointment_dialog(aid=p.selected_id())); self._set_page(p)

    def appointment_dialog(self,aid=None,preset=None):
        d=BaseDialog('Appuntamento',self); f=QFormLayout(d); veh=self.vehicle_combo(d); de=QDateEdit(); de.setCalendarPopup(True); de.setDate(QDate.fromString(preset,'yyyy-MM-dd') if preset else QDate.currentDate()); ti=QTimeEdit(QTime(9,0)); reason=QLineEdit(); notes=QTextEdit(); notes.setFixedHeight(80)
        for lab,w in [('Veicolo',veh),('Data',de),('Ora',ti),('Motivo',reason),('Note',notes)]: f.addRow(lab,w)
        if aid:
            r=self.db.one('SELECT * FROM appointments WHERE id=?',(aid,)); veh.setCurrentIndex(max(0,veh.findData(r['vehicle_id']))); de.setDate(QDate.fromString(r['date'],'yyyy-MM-dd')); ti.setTime(QTime.fromString(r['time'] or '09:00','HH:mm')); reason.setText(r['reason'] or ''); notes.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            vals=(veh.currentData() if veh.count() else None,de.date().toString('yyyy-MM-dd'),ti.time().toString('HH:mm'),reason.text().strip(),notes.toPlainText().strip()); self.db.ex('UPDATE appointments SET vehicle_id=?,date=?,time=?,reason=?,notes=? WHERE id=?',vals+(aid,)) if aid else self.db.ex('INSERT INTO appointments(vehicle_id,date,time,reason,notes) VALUES(?,?,?,?,?)',vals); d.accept(); self.show_dashboard() if preset else self.show_appointments()
        b.clicked.connect(save); d.exec()

    def delete_appointment(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM appointments WHERE id=?',(x,)); self.show_appointments()

    def print_appointments(self):
        rows=self.db.q('''SELECT a.date,a.time,v.plate,c.name client,a.reason,a.notes FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id ORDER BY a.date,a.time'''); self.print_table_pdf('SITUAZIONE APPUNTAMENTI',['Data','Ora','Targa','Cliente','Motivo','Note'],[[r[k] for k in ['date','time','plate','client','reason','notes']] for r in rows],'Appuntamenti')
