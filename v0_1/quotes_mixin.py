from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class QuotesMixin:
    def show_quotes(self):
        self.set_nav('Preventivi'); p=TablePage(self,'Preventivi','Preventivi a voci con totale automatico'); p.add_btn('Nuovo',lambda:self.quote_dialog(),True); p.add_btn('Modifica',lambda:self.quote_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_quote(p)); p.add_btn('Stampa selezionato',lambda:self.print_quote(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_quotes)
        rows=self.db.q('''SELECT q.*,v.plate,c.name client FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY q.id DESC'''); p.populate(['ID','Numero','Data','Targa','Cliente','Stato','Totale €','Note'],[[r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],f"{r['total']:.2f}",r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.quote_dialog(p.selected_id())); self._set_page(p)

    def quote_dialog(self,qid=None):
        if not self.vehicles_for_combo(): return QMessageBox.information(self,'Preventivi','Crea prima un veicolo.')
        d=BaseDialog('Preventivo',self); d.resize(950,720); root=QVBoxLayout(d); top=QFormLayout(); veh=self.vehicle_combo(d); num=QLineEdit(self.next_number('quotes','PREV')); de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); st=QComboBox(); st.addItems(['Bozza','Inviato','Accettato','Rifiutato']); top.addRow('Cliente / veicolo',veh); top.addRow('Numero',num); top.addRow('Data',de); top.addRow('Stato',st); root.addLayout(top)
        box=QGroupBox('Voci del preventivo'); g=QGridLayout(box); desc=QLineEdit(); qty=QDoubleSpinBox(); qty.setValue(1); qty.setMaximum(9999); price=QDoubleSpinBox(); price.setMaximum(999999); price.setDecimals(2); add=QPushButton('Aggiungi / aggiorna'); rem=QPushButton('Rimuovi'); g.addWidget(QLabel('Descrizione'),0,0); g.addWidget(QLabel('Q.tà'),0,1); g.addWidget(QLabel('Prezzo unit. €'),0,2); g.addWidget(desc,1,0); g.addWidget(qty,1,1); g.addWidget(price,1,2); g.addWidget(add,1,3); g.addWidget(rem,1,4)
        items=QTableWidget(); items.setColumnCount(4); items.setHorizontalHeaderLabels(['Voce','Q.tà','Prezzo unit. €','Totale €']); items.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); items.setSelectionBehavior(QAbstractItemView.SelectRows); items.setEditTriggers(QAbstractItemView.NoEditTriggers); g.addWidget(items,2,0,1,5); root.addWidget(box,1)
        total=QLabel('€ 0,00'); total.setStyleSheet(f'font-size:24px;font-weight:850;color:{RED};'); notes=QTextEdit(); notes.setPlaceholderText('Note generali del preventivo'); notes.setFixedHeight(90); root.addWidget(total); root.addWidget(notes)
        def refresh_total():
            t=sum(float(items.item(r,3).text().replace(',','.')) for r in range(items.rowCount())); total.setText(f"€ {t:,.2f}".replace(',','X').replace('.',',').replace('X','.')); return t
        def add_item():
            if not desc.text().strip(): return
            sel=items.currentRow(); r=sel if sel>=0 else items.rowCount();
            if sel<0: items.insertRow(r)
            vals=[desc.text().strip(),f'{qty.value():g}',f'{price.value():.2f}',f'{qty.value()*price.value():.2f}']
            for c1,v in enumerate(vals): items.setItem(r,c1,QTableWidgetItem(v))
            desc.clear(); qty.setValue(1); price.setValue(0); items.clearSelection(); refresh_total()
        def load_item():
            r=items.currentRow();
            if r>=0: desc.setText(items.item(r,0).text()); qty.setValue(float(items.item(r,1).text())); price.setValue(float(items.item(r,2).text()))
        add.clicked.connect(add_item); items.itemSelectionChanged.connect(load_item); rem.clicked.connect(lambda:(items.removeRow(items.currentRow()) if items.currentRow()>=0 else None, refresh_total()))
        if qid:
            q=self.db.one('SELECT * FROM quotes WHERE id=?',(qid,)); veh.setCurrentIndex(max(0,veh.findData(q['vehicle_id']))); num.setText(q['number']); de.setDate(QDate.fromString(q['created'],'yyyy-MM-dd')); st.setCurrentText(q['status']); notes.setPlainText(q['notes'] or '')
            for it in self.db.q('SELECT * FROM quote_items WHERE quote_id=? ORDER BY id',(qid,)):
                r=items.rowCount(); items.insertRow(r); vals=[it['description'],f"{it['qty']:g}",f"{it['unit_price']:.2f}",f"{it['line_total']:.2f}"]
                for c1,v in enumerate(vals): items.setItem(r,c1,QTableWidgetItem(v))
            refresh_total()
        save=QPushButton('Salva preventivo'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:10px;'); root.addWidget(save,0,Qt.AlignRight)
        def do_save():
            if items.rowCount()==0:return QMessageBox.warning(d,'Preventivo','Aggiungi almeno una voce.')
            t=refresh_total(); vals=(num.text().strip(),veh.currentData(),de.date().toString('yyyy-MM-dd'),st.currentText(),t,notes.toPlainText().strip())
            if qid: self.db.ex('UPDATE quotes SET number=?,vehicle_id=?,created=?,status=?,total=?,notes=? WHERE id=?',vals+(qid,)); qid2=qid; self.db.ex('DELETE FROM quote_items WHERE quote_id=?',(qid2,))
            else: qid2=self.db.ex('INSERT INTO quotes(number,vehicle_id,created,status,total,notes) VALUES(?,?,?,?,?,?)',vals).lastrowid
            for r in range(items.rowCount()): self.db.ex('INSERT INTO quote_items(quote_id,description,qty,unit_price,line_total) VALUES(?,?,?,?,?)',(qid2,items.item(r,0).text(),float(items.item(r,1).text()),float(items.item(r,2).text()),float(items.item(r,3).text())))
            d.accept(); self.show_quotes()
        save.clicked.connect(do_save); d.exec()

    def delete_quote(self,p):
        x=p.selected_id();
        if x and self.confirm_delete(): self.db.ex('DELETE FROM quotes WHERE id=?',(x,)); self.show_quotes()

    def print_quotes(self):
        rows=self.db.q('''SELECT q.number,q.created,v.plate,c.name client,q.status,q.total,q.notes FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY q.id DESC'''); self.print_table_pdf('SITUAZIONE PREVENTIVI',['Numero','Data','Targa','Cliente','Stato','Totale','Note'],[[r[k] for k in ['number','created','plate','client','status','total','notes']] for r in rows],'Preventivi')

    def print_quote(self,qid):
        if not qid:return
        r=self.db.one('''SELECT q.*,v.plate,v.brand,v.model,v.year,c.name client,c.phone,c.email FROM quotes q JOIN vehicles v ON v.id=q.vehicle_id JOIN clients c ON c.id=v.client_id WHERE q.id=?''',(qid,)); its=self.db.q('SELECT * FROM quote_items WHERE quote_id=? ORDER BY id',(qid,)); p=self.make_pdf_path(f"Preventivo_{r['number']}"); c=pdfcanvas.Canvas(str(p),pagesize=A4); W,H=A4; y=self.pdf_header(c,'PREVENTIVO')
        c.setFont('Helvetica-Bold',10); c.drawString(16*mm,y,f"N. {r['number']}   Data: {r['created']}   Stato: {r['status']}"); y-=9*mm; c.setFont('Helvetica',9); c.drawString(16*mm,y,f"Cliente: {r['client']}  Tel: {r['phone'] or '-'}  Email: {r['email'] or '-'}"); y-=6*mm; c.drawString(16*mm,y,f"Veicolo: {r['brand']} {r['model']}  Targa: {r['plate']}  Anno: {r['year'] or '-'}"); y-=12*mm
        c.setFont('Helvetica-Bold',8); c.drawString(16*mm,y,'Descrizione'); c.drawRightString(132*mm,y,'Q.tà'); c.drawRightString(166*mm,y,'Prezzo unit.'); c.drawRightString(195*mm,y,'Totale'); y-=5*mm; c.line(16*mm,y,195*mm,y); y-=6*mm; c.setFont('Helvetica',8)
        for it in its:
            if y<35*mm:c.showPage(); y=H-20*mm
            c.drawString(16*mm,y,str(it['description'])[:75]); c.drawRightString(132*mm,y,f"{it['qty']:g}"); c.drawRightString(166*mm,y,f"€ {it['unit_price']:.2f}"); c.drawRightString(195*mm,y,f"€ {it['line_total']:.2f}"); y-=6*mm
        y-=4*mm; c.setFont('Helvetica-Bold',13); c.setFillColor(colors.HexColor(RED)); c.drawRightString(195*mm,y,f"TOTALE: € {r['total']:.2f}"); y-=12*mm; c.setFillColor(colors.black); c.setFont('Helvetica',9); c.drawString(16*mm,y,'Note: '+str(r['notes'] or '')[:140]); c.save(); self.open_pdf(p)
