from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class InvoicesSuppliersMixin:
    def generic_page(self,nav,title,subtitle,headers,query,rowmap,add_fn,edit_fn,delete_fn,print_fn):
        self.set_nav(nav); p=TablePage(self,title,subtitle); p.add_btn('Nuovo',add_fn,True); p.add_btn('Modifica',lambda:edit_fn(p.selected_id())); p.add_btn('Elimina',lambda:delete_fn(p)); p.add_btn('Stampa situazione PDF',print_fn); rows=self.db.q(query); p.populate(headers,[rowmap(r) for r in rows]); p.table.doubleClicked.connect(lambda:edit_fn(p.selected_id())); self._set_page(p); return p

    def show_invoices(self):
        return self.generic_page('Fatture','Fatture','Archivio fatture e documenti fiscali',['ID','Numero','Data','Targa','Cliente','Stato','Totale €','Note'],'''SELECT i.*,v.plate,c.name client FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY i.id DESC''',lambda r:[r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],f"{r['total']:.2f}",r['notes']],lambda:self.invoice_dialog(),self.invoice_dialog,self.delete_invoice,self.print_invoices)

    def invoice_dialog(self,iid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Fatture','Crea prima un veicolo.')
        d=BaseDialog('Fattura',self); f=QFormLayout(d); veh=self.vehicle_combo(d); num=QLineEdit(self.next_number('invoices','FAT')); de=QDateEdit(QDate.currentDate()); st=QComboBox(); st.addItems(['Bozza','Emessa','Pagata','Annullata']); tot=QDoubleSpinBox(); tot.setMaximum(999999); tot.setDecimals(2); notes=QTextEdit(); notes.setFixedHeight(80)
        for lab,w in [('Cliente / veicolo',veh),('Numero',num),('Data',de),('Stato',st),('Totale €',tot),('Note',notes)]: f.addRow(lab,w)
        if iid:
            r=self.db.one('SELECT * FROM invoices WHERE id=?',(iid,)); veh.setCurrentIndex(max(0,veh.findData(r['vehicle_id']))); num.setText(r['number']); de.setDate(QDate.fromString(r['created'],'yyyy-MM-dd')); st.setCurrentText(r['status']); tot.setValue(r['total']); notes.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b); b.clicked.connect(lambda:self._save_invoice(d,iid,num,veh,de,st,tot,notes)); d.exec()

    def _save_invoice(self,d,iid,num,veh,de,st,tot,notes):
        vals=(num.text(),veh.currentData(),de.date().toString('yyyy-MM-dd'),st.currentText(),tot.value(),notes.toPlainText()); self.db.ex('UPDATE invoices SET number=?,vehicle_id=?,created=?,status=?,total=?,notes=? WHERE id=?',vals+(iid,)) if iid else self.db.ex('INSERT INTO invoices(number,vehicle_id,created,status,total,notes) VALUES(?,?,?,?,?,?)',vals); d.accept(); self.show_invoices()

    def delete_invoice(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM invoices WHERE id=?',(x,)); self.show_invoices()

    def print_invoices(self):
        rows=self.db.q('''SELECT i.number,i.created,v.plate,c.name client,i.status,i.total,i.notes FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY i.id DESC'''); self.print_table_pdf('SITUAZIONE FATTURE',['Numero','Data','Targa','Cliente','Stato','Totale','Note'],[[r[k] for k in ['number','created','plate','client','status','total','notes']] for r in rows],'Fatture')

    def show_suppliers(self):
        return self.generic_page('Fornitori','Fornitori','Anagrafica fornitori',['ID','Fornitore','Telefono','Email','Note'],'SELECT * FROM suppliers ORDER BY name',lambda r:[r['id'],r['name'],r['phone'],r['email'],r['notes']],lambda:self.supplier_dialog(),self.supplier_dialog,self.delete_supplier,self.print_suppliers)

    def supplier_dialog(self,sid=None):
        d=BaseDialog('Fornitore',self); f=QFormLayout(d); n=QLineEdit(); ph=QLineEdit(); em=QLineEdit(); no=QTextEdit(); no.setFixedHeight(80); [f.addRow(l,w) for l,w in [('Nome',n),('Telefono',ph),('Email',em),('Note',no)]]
        if sid:
            r=self.db.one('SELECT * FROM suppliers WHERE id=?',(sid,)); n.setText(r['name']); ph.setText(r['phone'] or ''); em.setText(r['email'] or ''); no.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b); b.clicked.connect(lambda:self._save_supplier(d,sid,n,ph,em,no)); d.exec()

    def _save_supplier(self,d,sid,n,ph,em,no):
        vals=(n.text(),ph.text(),em.text(),no.toPlainText()); self.db.ex('UPDATE suppliers SET name=?,phone=?,email=?,notes=? WHERE id=?',vals+(sid,)) if sid else self.db.ex('INSERT INTO suppliers(name,phone,email,notes) VALUES(?,?,?,?)',vals); d.accept(); self.show_suppliers()

    def delete_supplier(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM suppliers WHERE id=?',(x,)); self.show_suppliers()

    def print_suppliers(self):
        rows=self.db.q('SELECT name,phone,email,notes FROM suppliers ORDER BY name'); self.print_table_pdf('SITUAZIONE FORNITORI',['Fornitore','Telefono','Email','Note'],[[r[k] for k in ['name','phone','email','notes']] for r in rows],'Fornitori')
