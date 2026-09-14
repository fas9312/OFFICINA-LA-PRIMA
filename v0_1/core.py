import os, sys, sqlite3, shutil, calendar
from pathlib import Path
from datetime import date, datetime

from PySide6.QtCore import Qt, Signal, QDate, QTime, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QCheckBox,
    QMessageBox, QFileDialog, QAbstractItemView, QGroupBox
)

from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm

from car_catalog import CAR_CATALOG

APP_NAME = 'LA PRIMA Garage Manager 0.1'
NAVY = '#12263A'; NAVY_2 = '#0D1C2B'; RED = '#C51928'; TEXT = '#10233B'; MUTED = '#5D6D7E'
BLUE = '#0D6FD8'; GREEN = '#119B67'; ORANGE = '#F08A19'; BORDER = 'rgba(170,185,200,150)'
STATUSES = ['Accettata','Da diagnosticare','Preventivo','Autorizzata','In lavorazione','Attesa ricambi','Pronta','Consegnata']
MONTHS = ['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre']

if getattr(sys, 'frozen', False):
    RES_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).resolve().parent))
else:
    RES_DIR = Path(__file__).resolve().parent
LOGO_PATH = RES_DIR / 'assets' / 'la_prima_logo.png'
DATA_DIR = Path.home() / 'Documents' / 'LA_PRIMA_Garage_Manager_01'
PDF_DIR = DATA_DIR / 'PDF'; BACKUP_DIR = DATA_DIR / 'Backup'
for p in (DATA_DIR, PDF_DIR, BACKUP_DIR): p.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'la_prima_01.db'

OFFICE_DEFAULTS = {
    'name': 'Officina LA PRIMA',
    'address': 'Lungomare Giovanni Caboto, 45 - 04024 Gaeta (LT)',
    'phone1': '347 6938367', 'phone2': '349 2635776',
    'tagline': 'LA TUA AUTO, LA NOSTRA PASSIONE'
}

class DB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.schema(); self.seed()
    def schema(self):
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT,email TEXT,notes TEXT);
        CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY AUTOINCREMENT,client_id INTEGER NOT NULL,plate TEXT NOT NULL UNIQUE,brand TEXT,model TEXT,year TEXT,km INTEGER DEFAULT 0,vin TEXT,FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,number TEXT UNIQUE NOT NULL,vehicle_id INTEGER NOT NULL,opened TEXT NOT NULL,issue TEXT,diagnosis TEXT,status TEXT NOT NULL,labor REAL DEFAULT 0,parts REAL DEFAULT 0,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY AUTOINCREMENT,vehicle_id INTEGER,date TEXT NOT NULL,time TEXT,reason TEXT,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY AUTOINCREMENT,vehicle_id INTEGER NOT NULL,service_date TEXT NOT NULL,km INTEGER DEFAULT 0,engine_oil TEXT,oil_filter INTEGER DEFAULT 0,air_filter INTEGER DEFAULT 0,fuel_filter INTEGER DEFAULT 0,cabin_filter INTEGER DEFAULT 0,other_filters TEXT,next_service_km INTEGER DEFAULT 0,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS quotes(id INTEGER PRIMARY KEY AUTOINCREMENT,number TEXT UNIQUE NOT NULL,vehicle_id INTEGER NOT NULL,created TEXT NOT NULL,status TEXT NOT NULL,total REAL DEFAULT 0,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS quote_items(id INTEGER PRIMARY KEY AUTOINCREMENT,quote_id INTEGER NOT NULL,description TEXT NOT NULL,qty REAL NOT NULL DEFAULT 1,unit_price REAL NOT NULL DEFAULT 0,line_total REAL NOT NULL DEFAULT 0,FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY AUTOINCREMENT,number TEXT UNIQUE NOT NULL,vehicle_id INTEGER NOT NULL,created TEXT NOT NULL,status TEXT NOT NULL,total REAL DEFAULT 0,notes TEXT,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT,email TEXT,notes TEXT);
        CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT,description TEXT NOT NULL,supplier_id INTEGER,qty REAL DEFAULT 0,min_qty REAL DEFAULT 0,cost REAL DEFAULT 0,sale REAL DEFAULT 0,FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS deadlines(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,due_date TEXT,vehicle_id INTEGER,client_id INTEGER,kind TEXT,notes TEXT,done INTEGER DEFAULT 0,FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS car_makes(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS car_models(id INTEGER PRIMARY KEY AUTOINCREMENT,make_id INTEGER NOT NULL,name TEXT NOT NULL,UNIQUE(make_id,name),FOREIGN KEY(make_id) REFERENCES car_makes(id) ON DELETE CASCADE);
        ''')
        self.conn.commit()
    def seed(self):
        for k,v in OFFICE_DEFAULTS.items(): self.conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
        for make, models in CAR_CATALOG.items():
            self.conn.execute('INSERT OR IGNORE INTO car_makes(name) VALUES(?)',(make,))
            mid=self.conn.execute('SELECT id FROM car_makes WHERE name=?',(make,)).fetchone()[0]
            self.conn.executemany('INSERT OR IGNORE INTO car_models(make_id,name) VALUES(?,?)',[(mid,m) for m in models])
        self.conn.commit()
    def q(self,sql,p=()): return self.conn.execute(sql,p).fetchall()
    def one(self,sql,p=()): return self.conn.execute(sql,p).fetchone()
    def ex(self,sql,p=()):
        cur=self.conn.cursor(); cur.execute(sql,p); self.conn.commit(); return cur
    def setting(self,key):
        r=self.one('SELECT value FROM settings WHERE key=?',(key,)); return r['value'] if r else ''
    def set_setting(self,key,val): self.ex('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,val))

class BackgroundWidget(QWidget):
    def __init__(self, logo_path, parent=None):
        super().__init__(parent); self.logo = QPixmap(str(logo_path)); self.setAttribute(Qt.WA_StyledBackground, True)
    def paintEvent(self, event):
        p=QPainter(self); p.fillRect(self.rect(), QColor('#CCD6DE'))
        if not self.logo.isNull():
            target=self.logo.scaled(int(self.width()*0.86), int(self.height()*0.70), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x=(self.width()-target.width())//2; y=max(70,(self.height()-target.height())//2)
            p.setOpacity(0.34); p.drawPixmap(x,y,target); p.setOpacity(1.0)
        p.fillRect(self.rect(), QColor(255,255,255,28))

class GlassFrame(QFrame):
    def __init__(self, alpha=205, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'QFrame{{background:rgba(255,255,255,{alpha});border:1px solid {BORDER};border-radius:15px;}} QLabel{{background:transparent;border:0;}}')

class KpiCard(GlassFrame):
    def __init__(self, icon, title, value, color, sub):
        super().__init__(205); l=QHBoxLayout(self); l.setContentsMargins(18,15,18,15)
        ic=QLabel(icon); ic.setStyleSheet(f'font-size:30px;color:{color};'); l.addWidget(ic)
        v=QVBoxLayout(); t=QLabel(title); t.setStyleSheet('font-size:16px;font-weight:700;color:#10233B;'); n=QLabel(str(value)); n.setStyleSheet(f'font-size:31px;font-weight:800;color:{color};'); s=QLabel(sub); s.setStyleSheet('font-size:11px;color:#617181;')
        v.addWidget(t); v.addWidget(n); v.addWidget(s); l.addLayout(v,1)

class DayCell(QFrame):
    clicked = Signal(str)
    def __init__(self, ds, day, today=False, events=None):
        super().__init__(); self.ds=ds
        self.setMinimumHeight(78); self.setStyleSheet('QFrame{background:rgba(255,255,255,80);border:1px solid rgba(150,170,190,130);border-radius:0;} QLabel{border:0;background:transparent;}')
        v=QVBoxLayout(self); v.setContentsMargins(5,4,5,4); v.setSpacing(2)
        d=QLabel(str(day)); d.setStyleSheet(('background:#0D6FD8;color:white;border-radius:4px;padding:2px 5px;font-weight:700;' if today else 'color:#10233B;font-weight:700;'))
        d.setFixedWidth(28); v.addWidget(d,0,Qt.AlignLeft)
        for i,e in enumerate((events or [])[:3]):
            tx=' '.join(x for x in [e['time'] or '',e['plate'] or '',e['reason'] or ''] if x)
            if len(tx)>25: tx=tx[:24]+'…'
            lab=QLabel(tx); bg=['#D8EAFF','#DDF5E9','#FFE8C9'][i%3]; fg=['#0756A1','#087A52','#A95A00'][i%3]
            lab.setStyleSheet(f'background:{bg};color:{fg};border-radius:5px;padding:2px 4px;font-size:10px;'); v.addWidget(lab)
        v.addStretch()
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self.clicked.emit(self.ds)
        super().mousePressEvent(e)

class DashboardCalendar(GlassFrame):
    dateClicked=Signal(str)
    def __init__(self, db):
        super().__init__(170); self.db=db; self.year=date.today().year; self.month=date.today().month
        self.root=QVBoxLayout(self); self.root.setContentsMargins(16,14,16,14)
        bar=QHBoxLayout(); self.title=QLabel(); self.title.setStyleSheet('font-size:23px;font-weight:800;color:#10233B;')
        self.prev=QPushButton('‹'); self.next=QPushButton('›'); self.today=QPushButton('Oggi')
        for b in (self.prev,self.next): b.setFixedSize(38,34); b.setStyleSheet('background:rgba(240,244,248,220);border:0;border-radius:6px;font-size:20px;font-weight:700;')
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
        rows=self.db.q('''SELECT a.date,a.time,a.reason,v.plate FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id WHERE a.date BETWEEN ? AND ? ORDER BY a.date,a.time''',(f'{self.year:04d}-{self.month:02d}-01',f'{self.year:04d}-{self.month:02d}-{last:02d}'))
        by={}
        for r in rows: by.setdefault(r['date'],[]).append(r)
        weeks=calendar.Calendar(firstweekday=0).monthdayscalendar(self.year,self.month)
        while len(weeks)<6: weeks.append([0]*7)
        td=date.today()
        for rr,wk in enumerate(weeks[:6],1):
            for cc,day in enumerate(wk):
                if day:
                    ds=f'{self.year:04d}-{self.month:02d}-{day:02d}'
                    cell=DayCell(ds,day,td==date(self.year,self.month,day),by.get(ds,[])); cell.clicked.connect(self.dateClicked); self.grid.addWidget(cell,rr,cc)
                else:
                    blank=QFrame(); blank.setStyleSheet('background:rgba(255,255,255,45);border:1px solid rgba(150,170,190,90);'); blank.setMinimumHeight(78); self.grid.addWidget(blank,rr,cc)
            self.grid.setRowStretch(rr,1)
        for c in range(7): self.grid.setColumnStretch(c,1)
    def shift(self,n):
        self.month+=n
        if self.month<1: self.month=12; self.year-=1
        if self.month>12: self.month=1; self.year+=1
        self.refresh()
    def go_today(self): self.year=date.today().year; self.month=date.today().month; self.refresh()

class BaseDialog(QDialog):
    def __init__(self,title,parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setMinimumWidth(520); self.setStyleSheet('QDialog{background:#EEF3F7;} QLabel{color:#10233B;} QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QDateEdit,QTimeEdit,QTextEdit{background:white;border:1px solid #C8D3DC;border-radius:6px;padding:6px;} QPushButton{padding:8px 14px;border-radius:6px;}')

class TablePage(QWidget):
    def __init__(self, app, title, subtitle):
        super().__init__(); self.app=app; self.setStyleSheet('background:transparent;')
        root=QVBoxLayout(self); root.setContentsMargins(22,18,22,22)
        hdr=QHBoxLayout(); tv=QVBoxLayout(); t=QLabel(title); t.setStyleSheet('font-size:28px;font-weight:800;color:white;'); s=QLabel(subtitle); s.setStyleSheet('font-size:12px;color:#EFF4F8;'); tv.addWidget(t); tv.addWidget(s); hdr.addLayout(tv); hdr.addStretch(); root.addLayout(hdr)
        self.card=GlassFrame(220); cl=QVBoxLayout(self.card); self.toolbar=QHBoxLayout(); cl.addLayout(self.toolbar)
        self.table=QTableWidget(); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.verticalHeader().setVisible(False); self.table.setStyleSheet('QTableWidget{background:rgba(255,255,255,225);border:0;color:#15283B;gridline-color:#D7E0E8;} QHeaderView::section{background:#E7EDF2;color:#20364C;padding:7px;border:0;font-weight:700;}')
        cl.addWidget(self.table); root.addWidget(self.card,1)
    def add_btn(self,text,slot,primary=False):
        b=QPushButton(text); b.clicked.connect(slot); b.setStyleSheet((f'background:{RED};color:white;' if primary else 'background:#E8EEF3;color:#20364C;')+'border:0;border-radius:7px;padding:8px 12px;font-weight:700;'); self.toolbar.addWidget(b); return b
    def selected_id(self):
        r=self.table.currentRow();
        if r<0:return None
        it=self.table.item(r,0); return int(it.data(Qt.UserRole) or it.text()) if it else None
    def populate(self, headers, rows, hidden_id=True):
        self.table.setColumnCount(len(headers)); self.table.setHorizontalHeaderLabels(headers); self.table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,val in enumerate(row): self.table.setItem(r,c,QTableWidgetItem('' if val is None else str(val)))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if hidden_id and headers and headers[0]=='ID': self.table.setColumnHidden(0,True)
