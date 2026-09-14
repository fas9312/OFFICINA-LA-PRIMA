from datetime import date, datetime
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import *
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from core import *

class DashboardMixin:
    def show_dashboard(self):
        self.set_nav('Dashboard'); page=QWidget(); page.setStyleSheet('background:transparent;'); root=QVBoxLayout(page); root.setContentsMargins(0,0,0,0)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet('QScrollArea{background:transparent;border:0;} QScrollBar:vertical{background:rgba(255,255,255,70);width:14px;} QScrollBar::handle:vertical{background:#71879A;border-radius:7px;min-height:45px;}'); cont=QWidget(); cont.setStyleSheet('background:transparent;'); v=QVBoxLayout(cont); v.setContentsMargins(28,22,28,28); v.setSpacing(14)
        header=QHBoxLayout(); ht=QVBoxLayout(); t=QLabel('Dashboard'); t.setStyleSheet('font-size:34px;font-weight:850;color:#10233B;'); s=QLabel('Benvenuto in Officina LA PRIMA\nGestisci il tuo lavoro, un cliente alla volta.'); s.setStyleSheet('font-size:14px;color:#20364C;'); ht.addWidget(t); ht.addWidget(s); header.addLayout(ht); header.addStretch(); self.clock=QLabel(); self.clock.setAlignment(Qt.AlignRight|Qt.AlignTop); self.clock.setStyleSheet('font-size:13px;color:#10233B;background:rgba(255,255,255,120);padding:10px;border-radius:10px;'); header.addWidget(self.clock); v.addLayout(header)
        self.update_clock(); timer=QTimer(page); timer.timeout.connect(self.update_clock); timer.start(30000)
        row=QHBoxLayout(); vals=[('👥','Clienti',self.db.one('SELECT COUNT(*) c FROM clients')['c'],RED,'Totali nel database'),('🚗','Veicoli',self.db.one('SELECT COUNT(*) c FROM vehicles')['c'],BLUE,'Totali nel database'),('🔧','Commesse Aperte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status!='Consegnata'")['c'],ORANGE,'In lavorazione'),('✓','Auto pronte',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN,'Da consegnare')]
        for x in vals:
            row.addWidget(KpiCard(*x))
        v.addLayout(row)
        mid=QHBoxLayout(); self.cal=DashboardCalendar(self.db); self.cal.dateClicked.connect(self.add_appointment_for_date); mid.addWidget(self.cal,2)
        right=QVBoxLayout(); prom=GlassFrame(200); pv=QVBoxLayout(prom); h=QLabel('🔔  Promemoria e scadenze'); h.setStyleSheet('font-size:18px;font-weight:800;color:#10233B;'); pv.addWidget(h); future=self.db.one('SELECT COUNT(*) c FROM appointments WHERE date>=?',(date.today().isoformat(),))['c']; tq=self.db.one("SELECT COUNT(*) c FROM quotes WHERE status NOT IN ('Accettato','Rifiutato')")['c']; ts=self.db.one('SELECT COUNT(*) c FROM services WHERE next_service_km>0')['c']; pv.addWidget(QLabel(f'🔧  {ts} tagliandi programmati')); pv.addWidget(QLabel(f'📄  {tq} preventivi da seguire')); pv.addWidget(QLabel(f'📅  {future} appuntamenti futuri')); pv.addStretch(); right.addWidget(prom)
        state=GlassFrame(200); sv=QVBoxLayout(state); sh=QLabel('▥  Stato Officina'); sh.setStyleSheet('font-size:18px;font-weight:800;color:#10233B;'); sv.addWidget(sh); entries=[('Tagliandi programmati',ts,BLUE),('Preventivi da inviare',tq,ORANGE),('Appuntamenti futuri',future,GREEN),('Commesse in lavorazione',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='In lavorazione'")['c'],RED),('Auto pronte alla consegna',self.db.one("SELECT COUNT(*) c FROM jobs WHERE status='Pronta'")['c'],GREEN)]
        for label,n,col in entries:
            rr=QHBoxLayout(); dot=QLabel('●'); dot.setStyleSheet(f'color:{col};'); rr.addWidget(dot); rr.addWidget(QLabel(label)); rr.addStretch(); rr.addWidget(QLabel(str(n))); sv.addLayout(rr)
        right.addWidget(state); mid.addLayout(right,1); v.addLayout(mid)
        low=QHBoxLayout(); jobs=GlassFrame(205); jv=QVBoxLayout(jobs); jt=QLabel('🔧  Commesse in evidenza'); jt.setStyleSheet('font-size:18px;font-weight:800;color:#10233B;'); jv.addWidget(jt); tbl=QTableWidget(); tbl.setColumnCount(4); tbl.setHorizontalHeaderLabels(['#','Cliente','Veicolo','Stato']); tbl.verticalHeader().setVisible(False); tbl.setEditTriggers(QAbstractItemView.NoEditTriggers); tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); rows=self.db.q('''SELECT j.number,c.name,v.plate,j.status FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id WHERE j.status!='Consegnata' ORDER BY j.id DESC LIMIT 7'''); tbl.setRowCount(len(rows));
        for r,x in enumerate(rows):
            for c1,k in enumerate(['number','name','plate','status']): tbl.setItem(r,c1,QTableWidgetItem(str(x[k] or '')))
        jv.addWidget(tbl); low.addWidget(jobs,2)
        ap=GlassFrame(205); av=QVBoxLayout(ap); at=QLabel('▣  Ultimi appuntamenti'); at.setStyleSheet('font-size:18px;font-weight:800;color:#10233B;'); av.addWidget(at); for_rows=self.db.q('''SELECT a.date,a.time,v.plate,a.reason FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id ORDER BY a.date DESC,a.time DESC LIMIT 7''')
        for r in for_rows: av.addWidget(QLabel(f"{r['date']}  {r['time'] or ''}  {r['plate'] or ''} — {r['reason'] or ''}"))
        av.addStretch(); low.addWidget(ap,1); v.addLayout(low)
        scroll.setWidget(cont); root.addWidget(scroll); self._set_page(page)

    def update_clock(self):
        if hasattr(self,'clock'): self.clock.setText(datetime.now().strftime('%d/%m/%Y   %H:%M'))

    def add_appointment_for_date(self,ds): self.appointment_dialog(preset=ds)
