import shutil
from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class MiscMixin:
    def show_report(self):
        self.set_nav('Report'); p=QWidget(); p.setStyleSheet('background:transparent;'); v=QVBoxLayout(p); v.setContentsMargins(28,24,28,28); t=QLabel('Report'); t.setStyleSheet('font-size:30px;font-weight:850;color:white;'); v.addWidget(t); card=GlassFrame(215); cv=QVBoxLayout(card); vals=[('Clienti',self.db.one('SELECT COUNT(*) c FROM clients')['c']),('Veicoli',self.db.one('SELECT COUNT(*) c FROM vehicles')['c']),('Commesse aperte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c']),('Preventivi',self.db.one('SELECT COUNT(*) c FROM quotes')['c']),('Fatture',self.db.one('SELECT COUNT(*) c FROM invoices')['c']),('Ricambi sotto scorta',self.db.one('SELECT COUNT(*) c FROM inventory WHERE qty<=min_qty')['c'])]
        for k,n in vals:
            r=QHBoxLayout(); lab=QLabel(k); lab.setStyleSheet('font-size:15px;'); num=QLabel(str(n)); num.setStyleSheet('font-size:20px;font-weight:800;'); r.addWidget(lab); r.addStretch(); r.addWidget(num); cv.addLayout(r)
        b=QPushButton('Stampa report PDF'); b.setStyleSheet(f'background:{RED};color:white;border:0;border-radius:7px;padding:10px;font-weight:700;'); b.clicked.connect(lambda:self.print_table_pdf('REPORT OFFICINA',['Indicatore','Valore'],vals,'Report')); cv.addWidget(b,0,Qt.AlignRight); v.addWidget(card); v.addStretch(); self._set_page(p)

    def show_backup(self):
        self.set_nav('Backup'); p=QWidget(); p.setStyleSheet('background:transparent;'); v=QVBoxLayout(p); v.setContentsMargins(28,24,28,28); t=QLabel('Backup'); t.setStyleSheet('font-size:30px;font-weight:850;color:white;'); v.addWidget(t); c=GlassFrame(215); cv=QVBoxLayout(c); info=QLabel(f'Database: {DB_PATH}\nBackup: {BACKUP_DIR}'); info.setStyleSheet('font-size:13px;'); cv.addWidget(info); b=QPushButton('Crea backup adesso'); b.setStyleSheet(f'background:{RED};color:white;padding:10px;border:0;border-radius:7px;font-weight:700;'); b.clicked.connect(self.create_backup); cv.addWidget(b,0,Qt.AlignLeft); v.addWidget(c); v.addStretch(); self._set_page(p)

    def create_backup(self):
        p=BACKUP_DIR/f'la_prima_{datetime.now():%Y%m%d_%H%M%S}.db'; shutil.copy2(DB_PATH,p); QMessageBox.information(self,'Backup',f'Backup creato:\n{p}')

    def show_settings(self):
        self.set_nav('Impostazioni'); p=QWidget(); p.setStyleSheet('background:transparent;'); v=QVBoxLayout(p); v.setContentsMargins(28,24,28,28); t=QLabel('Impostazioni'); t.setStyleSheet('font-size:30px;font-weight:850;color:white;'); v.addWidget(t); c=GlassFrame(220); f=QFormLayout(c); fields={}
        for key,lab in [('name','Nome officina'),('address','Indirizzo'),('phone1','Telefono 1'),('phone2','Telefono 2'),('tagline','Slogan')]: fields[key]=QLineEdit(self.db.setting(key)); f.addRow(lab,fields[key])
        b=QPushButton('Salva impostazioni'); b.setStyleSheet(f'background:{RED};color:white;padding:9px;border:0;border-radius:7px;font-weight:700;'); f.addRow('',b); b.clicked.connect(lambda:[self.db.set_setting(k,w.text()) for k,w in fields.items()]); v.addWidget(c); v.addStretch(); self._set_page(p)
