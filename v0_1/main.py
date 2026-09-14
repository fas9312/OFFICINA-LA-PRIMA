import os, sys, shutil
from datetime import date, datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *
from dashboard_mixin import DashboardMixin
from clients_vehicles_mixin import ClientsVehiclesMixin
from jobs_appointments_mixin import JobsAppointmentsMixin
from services_mixin import ServicesMixin
from quotes_mixin import QuotesMixin
from invoices_suppliers_mixin import InvoicesSuppliersMixin
from inventory_deadlines_mixin import InventoryDeadlinesMixin
from misc_mixin import MiscMixin

class AppWindow(DashboardMixin, ClientsVehiclesMixin, JobsAppointmentsMixin, ServicesMixin, QuotesMixin, InvoicesSuppliersMixin, InventoryDeadlinesMixin, MiscMixin, QMainWindow):
    def __init__(self):
        super().__init__(); self.db=DB(); self.setWindowTitle(APP_NAME); self.resize(1536,960); self.setMinimumSize(1180,760)
        self.logo=QPixmap(str(LOGO_PATH)); self.pages={}; self._build_ui(); self.show_dashboard()

    def _build_ui(self):
        root=QWidget(); self.setCentralWidget(root); hl=QHBoxLayout(root); hl.setContentsMargins(0,0,0,0); hl.setSpacing(0)
        side=QFrame(); side.setFixedWidth(285); side.setStyleSheet(f'QFrame{{background:{NAVY};border:0;}}'); sl=QVBoxLayout(side); sl.setContentsMargins(14,14,14,16); sl.setSpacing(3)
        brand=QLabel(); brand.setAlignment(Qt.AlignCenter); brand.setFixedHeight(150)
        if not self.logo.isNull(): brand.setPixmap(self.logo.scaled(250,135,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else: brand.setText('OFFICINA\nLA PRIMA'); brand.setStyleSheet('color:white;font-size:27px;font-weight:900;')
        sl.addWidget(brand)
        self.nav={}
        items=[('⌂','Dashboard',self.show_dashboard),('👥','Clienti',self.show_clients),('🚗','Veicoli',self.show_vehicles),('🔧','Commesse',self.show_jobs),('▣','Appuntamenti',self.show_appointments),('⚙','Tagliandi',self.show_services),('▤','Preventivi',self.show_quotes),('▤','Fatture',self.show_invoices),('▦','Magazzino',self.show_inventory),('▣','Fornitori',self.show_suppliers),('◷','Scadenze',self.show_deadlines),('▥','Report',self.show_report),('◉','Backup',self.show_backup),('⚙','Impostazioni',self.show_settings)]
        for icon,name,fn in items:
            b=QPushButton(f'{icon}   {name}'); b.setCheckable(True); b.setCursor(Qt.PointingHandCursor); b.setMinimumHeight(43); b.setStyleSheet(f'QPushButton{{text-align:left;padding-left:22px;color:white;background:transparent;border:0;border-radius:7px;font-size:14px;font-weight:650;}} QPushButton:hover{{background:#1C3C57;}} QPushButton:checked{{background:{RED};}}'); b.clicked.connect(fn); sl.addWidget(b); self.nav[name]=b
        sl.addStretch(); tag=QLabel('L A  T U A  A U T O ,\nL A  N O S T R A  P A S S I O N E'); tag.setAlignment(Qt.AlignCenter); tag.setStyleSheet('color:white;font-size:10px;letter-spacing:2px;'); sl.addWidget(tag)
        hl.addWidget(side)
        self.bg=BackgroundWidget(LOGO_PATH); bl=QVBoxLayout(self.bg); bl.setContentsMargins(0,0,0,0); self.stack=QStackedWidget(); self.stack.setStyleSheet('background:transparent;'); bl.addWidget(self.stack); hl.addWidget(self.bg,1)

    def set_nav(self,name):
        for n,b in self.nav.items(): b.setChecked(n==name)

    def next_number(self,table,prefix):
        y=date.today().year; r=self.db.one(f'SELECT COUNT(*) c FROM {table} WHERE number LIKE ?',(f'{prefix}-{y}-%',)); return f'{prefix}-{y}-{(r["c"]+1):05d}'

    def make_pdf_path(self,name):
        safe=''.join(c if c.isalnum() or c in '-_' else '_' for c in name); return PDF_DIR/f'{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf'

    def pdf_header(self,c,title):
        W,H=A4
        if LOGO_PATH.exists():
            try:c.drawImage(str(LOGO_PATH),14*mm,H-38*mm,width=70*mm,height=28*mm,preserveAspectRatio=True,mask='auto')
            except:pass
        c.setFillColor(colors.HexColor(RED)); c.setFont('Helvetica-Bold',17); c.drawRightString(W-15*mm,H-20*mm,title)
        c.setFillColor(colors.HexColor('#555')); c.setFont('Helvetica',8); c.drawRightString(W-15*mm,H-27*mm,datetime.now().strftime('%d/%m/%Y %H:%M')); c.setStrokeColor(colors.HexColor(RED)); c.line(14*mm,H-44*mm,W-14*mm,H-44*mm); return H-54*mm

    def open_pdf(self,p):
        try: os.startfile(str(p))
        except Exception: QMessageBox.information(self,'PDF',f'PDF salvato in:\n{p}')

    def print_table_pdf(self,title,headers,rows,name):
        p=self.make_pdf_path(name); c=pdfcanvas.Canvas(str(p),pagesize=landscape(A4)); W,H=landscape(A4); y=H-20*mm
        c.setFont('Helvetica-Bold',16); c.setFillColor(colors.HexColor(RED)); c.drawString(14*mm,y,title); c.setFont('Helvetica',8); c.setFillColor(colors.HexColor('#555')); c.drawRightString(W-14*mm,y,datetime.now().strftime('%d/%m/%Y %H:%M')); y-=10*mm
        usable=W-28*mm; cw=usable/max(1,len(headers)); c.setFont('Helvetica-Bold',7)
        for i,h in enumerate(headers): c.drawString(14*mm+i*cw,y,str(h)[:24])
        y-=5*mm; c.line(14*mm,y,W-14*mm,y); y-=5*mm; c.setFont('Helvetica',7)
        for row in rows:
            if y<15*mm: c.showPage(); y=H-18*mm; c.setFont('Helvetica',7)
            for i,v in enumerate(row): c.drawString(14*mm+i*cw,y,str(v or '')[:30])
            y-=5*mm
        c.save(); self.open_pdf(p)

    def confirm_delete(self,msg='Eliminare la voce selezionata?'): return QMessageBox.question(self,'Conferma',msg,QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes

    def vehicles_for_combo(self): return self.db.q('''SELECT v.id,v.plate,v.brand,v.model,c.name client FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY c.name,v.plate''')

    def vehicle_combo(self, dlg):
        cb=QComboBox(); rows=self.vehicles_for_combo();
        for r in rows: cb.addItem(f"{r['client']} — {r['plate']} — {r['brand'] or ''} {r['model'] or ''}",r['id'])
        return cb

    def _set_page(self,p):
        while self.stack.count():
            w=self.stack.widget(0); self.stack.removeWidget(w); w.deleteLater()
        self.stack.addWidget(p); self.stack.setCurrentWidget(p)

    def closeEvent(self,event):
        m=QMessageBox(self); m.setWindowTitle('Chiusura'); m.setText('Vuoi creare un backup prima di chiudere?'); y=m.addButton('Sì, backup e chiudi',QMessageBox.YesRole); n=m.addButton('No, chiudi',QMessageBox.NoRole); c=m.addButton('Annulla',QMessageBox.RejectRole); m.exec()
        if m.clickedButton()==c: event.ignore(); return
        if m.clickedButton()==y:
            try: shutil.copy2(DB_PATH,BACKUP_DIR/f'la_prima_{datetime.now():%Y%m%d_%H%M%S}.db')
            except: pass
        event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); w=AppWindow(); w.show(); sys.exit(app.exec())
