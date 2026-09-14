from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class InventoryDeadlinesMixin:
    def show_inventory(self):
        self.set_nav('Magazzino'); p=TablePage(self,'Magazzino','Ricambi, costi e giacenze'); p.add_btn('Nuovo',lambda:self.part_dialog(),True); p.add_btn('Modifica',lambda:self.part_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_part(p)); p.add_btn('Stampa situazione PDF',self.print_inventory); rows=self.db.q('''SELECT i.*,s.name supplier FROM inventory i LEFT JOIN suppliers s ON s.id=i.supplier_id ORDER BY i.description'''); p.populate(['ID','Codice','Descrizione','Fornitore','Q.tà','Min','Costo','Vendita'],[[r['id'],r['code'],r['description'],r['supplier'],r['qty'],r['min_qty'],r['cost'],r['sale']] for r in rows]); p.table.doubleClicked.connect(lambda:self.part_dialog(p.selected_id())); self._set_page(p)

    def part_dialog(self,pid=None):
        d=BaseDialog('Ricambio',self); f=QFormLayout(d); code=QLineEdit(); desc=QLineEdit(); sup=QComboBox(); sup.addItem('— Nessuno —',None); [sup.addItem(r['name'],r['id']) for r in self.db.q('SELECT id,name FROM suppliers ORDER BY name')]; qty=QDoubleSpinBox(); mi=QDoubleSpinBox(); cost=QDoubleSpinBox(); sale=QDoubleSpinBox();
        for x in (qty,mi,cost,sale): x.setMaximum(999999); x.setDecimals(2)
        for lab,w in [('Codice',code),('Descrizione',desc),('Fornitore',sup),('Quantità',qty),('Scorta minima',mi),('Costo €',cost),('Prezzo vendita €',sale)]: f.addRow(lab,w)
        if pid:
            r=self.db.one('SELECT * FROM inventory WHERE id=?',(pid,)); code.setText(r['code'] or ''); desc.setText(r['description']); sup.setCurrentIndex(max(0,sup.findData(r['supplier_id']))); qty.setValue(r['qty']); mi.setValue(r['min_qty']); cost.setValue(r['cost']); sale.setValue(r['sale'])
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            vals=(code.text(),desc.text(),sup.currentData(),qty.value(),mi.value(),cost.value(),sale.value()); self.db.ex('UPDATE inventory SET code=?,description=?,supplier_id=?,qty=?,min_qty=?,cost=?,sale=? WHERE id=?',vals+(pid,)) if pid else self.db.ex('INSERT INTO inventory(code,description,supplier_id,qty,min_qty,cost,sale) VALUES(?,?,?,?,?,?,?)',vals); d.accept(); self.show_inventory()
        b.clicked.connect(save); d.exec()

    def delete_part(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM inventory WHERE id=?',(x,)); self.show_inventory()

    def print_inventory(self):
        rows=self.db.q('''SELECT i.code,i.description,s.name supplier,i.qty,i.min_qty,i.cost,i.sale FROM inventory i LEFT JOIN suppliers s ON s.id=i.supplier_id ORDER BY i.description'''); self.print_table_pdf('SITUAZIONE MAGAZZINO',['Codice','Descrizione','Fornitore','Q.tà','Min','Costo','Vendita'],[[r[k] for k in ['code','description','supplier','qty','min_qty','cost','sale']] for r in rows],'Magazzino')

    def show_deadlines(self):
        self.set_nav('Scadenze'); p=TablePage(self,'Scadenze','Promemoria amministrativi e tecnici'); p.add_btn('Nuova',lambda:self.deadline_dialog(),True); p.add_btn('Modifica',lambda:self.deadline_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_deadline(p)); p.add_btn('Stampa situazione PDF',self.print_deadlines); rows=self.db.q('''SELECT d.*,v.plate,c.name client FROM deadlines d LEFT JOIN vehicles v ON v.id=d.vehicle_id LEFT JOIN clients c ON c.id=d.client_id ORDER BY d.done,d.due_date'''); p.populate(['ID','Scadenza','Data','Tipo','Targa','Cliente','Completata','Note'],[[r['id'],r['title'],r['due_date'],r['kind'],r['plate'],r['client'],'Sì' if r['done'] else 'No',r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.deadline_dialog(p.selected_id())); self._set_page(p)

    def deadline_dialog(self,did=None):
        d=BaseDialog('Scadenza',self); f=QFormLayout(d); title=QLineEdit(); de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); kind=QComboBox(); kind.addItems(['Generica','Revisione','Bollo','Assicurazione','Tagliando','Preventivo','Ricambio']); veh=self.vehicle_combo(d); cl=QComboBox(); cl.addItem('—',None); [cl.addItem(r['name'],r['id']) for r in self.db.q('SELECT id,name FROM clients ORDER BY name')]; done=QCheckBox('Completata'); notes=QTextEdit(); notes.setFixedHeight(80); [f.addRow(l,w) for l,w in [('Titolo',title),('Data',de),('Tipo',kind),('Veicolo',veh),('Cliente',cl),('',done),('Note',notes)]]
        if did:
            r=self.db.one('SELECT * FROM deadlines WHERE id=?',(did,)); title.setText(r['title']); de.setDate(QDate.fromString(r['due_date'],'yyyy-MM-dd')); kind.setCurrentText(r['kind'] or 'Generica'); veh.setCurrentIndex(max(0,veh.findData(r['vehicle_id']))); cl.setCurrentIndex(max(0,cl.findData(r['client_id']))); done.setChecked(bool(r['done'])); notes.setPlainText(r['notes'] or '')
        b=QPushButton('Salva'); b.setStyleSheet(f'background:{RED};color:white;font-weight:700;'); f.addRow('',b)
        def save():
            vals=(title.text(),de.date().toString('yyyy-MM-dd'),veh.currentData() if veh.count() else None,cl.currentData(),kind.currentText(),notes.toPlainText(),int(done.isChecked())); self.db.ex('UPDATE deadlines SET title=?,due_date=?,vehicle_id=?,client_id=?,kind=?,notes=?,done=? WHERE id=?',vals+(did,)) if did else self.db.ex('INSERT INTO deadlines(title,due_date,vehicle_id,client_id,kind,notes,done) VALUES(?,?,?,?,?,?,?)',vals); d.accept(); self.show_deadlines()
        b.clicked.connect(save); d.exec()

    def delete_deadline(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM deadlines WHERE id=?',(x,)); self.show_deadlines()

    def print_deadlines(self):
        rows=self.db.q('''SELECT d.title,d.due_date,d.kind,v.plate,c.name client,d.done,d.notes FROM deadlines d LEFT JOIN vehicles v ON v.id=d.vehicle_id LEFT JOIN clients c ON c.id=d.client_id ORDER BY d.done,d.due_date'''); self.print_table_pdf('SITUAZIONE SCADENZE',['Scadenza','Data','Tipo','Targa','Cliente','Fatta','Note'],[[r['title'],r['due_date'],r['kind'],r['plate'],r['client'],'Si' if r['done'] else 'No',r['notes']] for r in rows],'Scadenze')
