import os, sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QMessageBox
)
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

import resources_rc
from core import *
from main import AppWindow as Clean01Window

UI_LOGO = ':/la_prima/logo.png'


class LogoBackgroundWidget(QWidget):
    """Background guaranteed by a Qt embedded resource, never by a filesystem path."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo = QPixmap(UI_LOGO)
        if self.logo.isNull():
            raise RuntimeError('Logo LA PRIMA Qt resource non disponibile')
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#BFCAD3'))
        target = self.logo.scaled(
            int(self.width() * 0.90), int(self.height() * 0.72),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        x = (self.width() - target.width()) // 2
        y = max(70, (self.height() - target.height()) // 2)
        p.setOpacity(0.64)
        p.drawPixmap(x, y, target)
        p.setOpacity(1.0)
        p.fillRect(self.rect(), QColor(255, 255, 255, 18))
        super().paintEvent(event)


class AppWindow(Clean01Window):
    """0.1.1: same clean 0.1 data model/functions, with guaranteed logo rendering and restored single PDFs."""

    def _build_ui(self):
        ui_logo = QPixmap(UI_LOGO)
        if ui_logo.isNull():
            raise RuntimeError('Impossibile caricare il logo ufficiale incorporato')

        root = QWidget()
        self.setCentralWidget(root)
        hl = QHBoxLayout(root)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        side = QFrame()
        side.setFixedWidth(285)
        side.setStyleSheet(f'QFrame{{background:{NAVY};border:0;}}')
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 12, 14, 16)
        sl.setSpacing(3)

        brand = QLabel()
        brand.setAlignment(Qt.AlignCenter)
        brand.setFixedHeight(155)
        brand.setPixmap(ui_logo.scaled(255, 138, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand.setToolTip('Logo ufficiale Officina LA PRIMA')
        sl.addWidget(brand)

        self.nav = {}
        items = [
            ('⌂','Dashboard',self.show_dashboard),('👥','Clienti',self.show_clients),
            ('🚗','Veicoli',self.show_vehicles),('🔧','Commesse',self.show_jobs),
            ('▣','Appuntamenti',self.show_appointments),('⚙','Tagliandi',self.show_services),
            ('▤','Preventivi',self.show_quotes),('▤','Fatture',self.show_invoices),
            ('▦','Magazzino',self.show_inventory),('▣','Fornitori',self.show_suppliers),
            ('◷','Scadenze',self.show_deadlines),('▥','Report',self.show_report),
            ('◉','Backup',self.show_backup),('⚙','Impostazioni',self.show_settings)
        ]
        for icon, name, fn in items:
            b = QPushButton(f'{icon}   {name}')
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(43)
            b.setStyleSheet(
                f'QPushButton{{text-align:left;padding-left:22px;color:white;background:transparent;'
                f'border:0;border-radius:7px;font-size:14px;font-weight:650;}} '
                f'QPushButton:hover{{background:#1C3C57;}} QPushButton:checked{{background:{RED};}}'
            )
            b.clicked.connect(fn)
            sl.addWidget(b)
            self.nav[name] = b
        sl.addStretch()
        tag = QLabel('L A  T U A  A U T O ,\nL A  N O S T R A  P A S S I O N E')
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet('color:white;font-size:10px;letter-spacing:2px;')
        sl.addWidget(tag)
        hl.addWidget(side)

        self.bg = LogoBackgroundWidget()
        bl = QVBoxLayout(self.bg)
        bl.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.stack.setAttribute(Qt.WA_TranslucentBackground, True)
        self.stack.setStyleSheet('QStackedWidget{background:transparent;border:0;}')
        bl.addWidget(self.stack)
        hl.addWidget(self.bg, 1)
        self._ui_logo_ok = True

    def show_dashboard(self):
        super().show_dashboard()
        page = self.stack.currentWidget()
        if page:
            page.setAttribute(Qt.WA_TranslucentBackground, True)
            page.setStyleSheet('background:transparent;')
            for scroll in page.findChildren(QScrollArea):
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setAttribute(Qt.WA_TranslucentBackground, True)
                scroll.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
                scroll.viewport().setAutoFillBackground(False)
                scroll.setStyleSheet(
                    'QScrollArea{background:transparent;border:0;}'
                    'QScrollArea > QWidget > QWidget{background:transparent;}'
                    'QScrollBar:vertical{background:rgba(255,255,255,75);width:14px;}'
                    'QScrollBar::handle:vertical{background:#647D91;border-radius:7px;min-height:45px;}'
                )
            for frame in page.findChildren(GlassFrame):
                frame.setStyleSheet(
                    'QFrame{background:rgba(255,255,255,172);border:1px solid rgba(170,185,200,150);border-radius:15px;}'
                    'QLabel{background:transparent;border:0;}'
                )

    # --------- CLIENTI: stampa singola ripristinata ---------
    def show_clients(self):
        self.set_nav('Clienti')
        p = TablePage(self, 'Clienti', 'Anagrafica clienti')
        p.add_btn('Nuovo', lambda: self.client_dialog(), True)
        p.add_btn('Modifica', lambda: self.client_dialog(p.selected_id()))
        p.add_btn('Elimina', lambda: self.delete_client(p))
        p.add_btn('Stampa cliente selezionato', lambda: self.print_client_selected(p.selected_id()))
        p.add_btn('Stampa situazione PDF', self.print_clients)
        rows = self.db.q('SELECT * FROM clients ORDER BY name')
        p.populate(['ID','Cliente','Telefono','Email','Note'], [[r['id'],r['name'],r['phone'],r['email'],r['notes']] for r in rows])
        p.table.doubleClicked.connect(lambda: self.client_dialog(p.selected_id()))
        self._set_page(p)

    def print_client_selected(self, cid):
        if not cid:
            return QMessageBox.information(self, 'PDF', 'Seleziona prima un cliente.')
        r = self.db.one('SELECT * FROM clients WHERE id=?', (cid,))
        vehicles = self.db.q('SELECT plate,brand,model,year,km,vin FROM vehicles WHERE client_id=? ORDER BY plate', (cid,))
        pth = self.make_pdf_path(f"Cliente_{r['name']}")
        c = pdfcanvas.Canvas(str(pth), pagesize=A4)
        y = self.pdf_header(c, 'SCHEDA CLIENTE')
        for k, v in [('Cliente',r['name']),('Telefono',r['phone']),('Email',r['email']),('Note',r['notes'])]:
            c.setFont('Helvetica-Bold', 9); c.drawString(16*mm, y, k)
            c.setFont('Helvetica', 10); c.drawString(58*mm, y, str(v or '-'))
            y -= 8*mm
        y -= 4*mm; c.setFont('Helvetica-Bold', 11); c.drawString(16*mm, y, 'VEICOLI DEL CLIENTE'); y -= 7*mm
        c.setFont('Helvetica', 9)
        if not vehicles:
            c.drawString(16*mm, y, 'Nessun veicolo registrato.')
        for v in vehicles:
            c.drawString(16*mm, y, f"{v['plate']}   {v['brand'] or ''} {v['model'] or ''}   Anno {v['year'] or '-'}   Km {v['km'] or 0}   VIN {v['vin'] or '-'}")
            y -= 7*mm
        c.save(); self.open_pdf(pth)

    # --------- VEICOLI: stampa singola ripristinata ---------
    def show_vehicles(self):
        self.set_nav('Veicoli')
        p = TablePage(self, 'Veicoli', 'Archivio mezzi con marca e modello da database locale')
        p.add_btn('Nuovo', lambda: self.vehicle_dialog(), True)
        p.add_btn('Modifica', lambda: self.vehicle_dialog(p.selected_id()))
        p.add_btn('Elimina', lambda: self.delete_vehicle(p))
        p.add_btn('Stampa veicolo selezionato', lambda: self.print_vehicle_selected(p.selected_id()))
        p.add_btn('Stampa situazione PDF', self.print_vehicles)
        rows = self.db.q('''SELECT v.*,c.name client FROM vehicles v JOIN clients c ON c.id=v.client_id ORDER BY v.plate''')
        p.populate(['ID','Targa','Marca','Modello','Anno','Cliente','Km','VIN'], [[r['id'],r['plate'],r['brand'],r['model'],r['year'],r['client'],r['km'],r['vin']] for r in rows])
        p.table.doubleClicked.connect(lambda: self.vehicle_dialog(p.selected_id()))
        self._set_page(p)

    def print_vehicle_selected(self, vid):
        if not vid:
            return QMessageBox.information(self, 'PDF', 'Seleziona prima un veicolo.')
        r = self.db.one('''SELECT v.*,c.name client,c.phone,c.email FROM vehicles v JOIN clients c ON c.id=v.client_id WHERE v.id=?''', (vid,))
        pth = self.make_pdf_path(f"Veicolo_{r['plate']}")
        c = pdfcanvas.Canvas(str(pth), pagesize=A4); y = self.pdf_header(c, 'SCHEDA VEICOLO')
        pairs = [('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Targa',r['plate']),('Marca',r['brand']),('Modello',r['model']),('Anno',r['year']),('Km',r['km']),('VIN / Telaio',r['vin'])]
        for k,v in pairs:
            c.setFont('Helvetica-Bold',9); c.drawString(16*mm,y,k); c.setFont('Helvetica',10); c.drawString(58*mm,y,str(v or '-')); y-=8*mm
        c.save(); self.open_pdf(pth)

    # --------- COMMESSE: stampa singola ripristinata ---------
    def show_jobs(self):
        self.set_nav('Commesse')
        p = TablePage(self,'Commesse','Lavorazioni officina')
        p.add_btn('Nuova',lambda:self.job_dialog(),True); p.add_btn('Modifica',lambda:self.job_dialog(p.selected_id())); p.add_btn('Elimina',lambda:self.delete_job(p))
        p.add_btn('Stampa commessa selezionata',lambda:self.print_job_selected(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_jobs)
        rows=self.db.q('''SELECT j.*,v.plate,c.name client FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY j.id DESC''')
        p.populate(['ID','Numero','Apertura','Targa','Cliente','Stato','Problema','Totale €'],[[r['id'],r['number'],r['opened'],r['plate'],r['client'],r['status'],r['issue'],f"{(r['labor']+r['parts']):.2f}"] for r in rows])
        p.table.doubleClicked.connect(lambda:self.job_dialog(p.selected_id())); self._set_page(p)

    def print_job_selected(self, jid):
        if not jid: return QMessageBox.information(self,'PDF','Seleziona prima una commessa.')
        r=self.db.one('''SELECT j.*,v.plate,v.brand,v.model,c.name client,c.phone,c.email FROM jobs j JOIN vehicles v ON v.id=j.vehicle_id JOIN clients c ON c.id=v.client_id WHERE j.id=?''',(jid,))
        pth=self.make_pdf_path(f"Commessa_{r['number']}"); c=pdfcanvas.Canvas(str(pth),pagesize=A4); y=self.pdf_header(c,'SCHEDA COMMESSA')
        pairs=[('Numero',r['number']),('Data apertura',r['opened']),('Cliente',r['client']),('Telefono',r['phone']),('Veicolo',f"{r['brand']} {r['model']}"),('Targa',r['plate']),('Stato',r['status']),('Problema',r['issue']),('Diagnosi',r['diagnosis']),('Manodopera €',f"{r['labor']:.2f}"),('Ricambi €',f"{r['parts']:.2f}"),('Totale €',f"{r['labor']+r['parts']:.2f}"),('Note',r['notes'])]
        for k,v in pairs:
            c.setFont('Helvetica-Bold',9); c.drawString(16*mm,y,k); c.setFont('Helvetica',9); c.drawString(58*mm,y,str(v or '-')[:105]); y-=7*mm
        c.save(); self.open_pdf(pth)

    # --------- APPUNTAMENTI: stampa singola ripristinata ---------
    def show_appointments(self):
        self.set_nav('Appuntamenti')
        p=TablePage(self,'Appuntamenti','Agenda officina'); p.add_btn('Nuovo',lambda:self.appointment_dialog(),True); p.add_btn('Modifica',lambda:self.appointment_dialog(aid=p.selected_id())); p.add_btn('Elimina',lambda:self.delete_appointment(p)); p.add_btn('Stampa appuntamento selezionato',lambda:self.print_appointment_selected(p.selected_id())); p.add_btn('Stampa situazione PDF',self.print_appointments)
        rows=self.db.q('''SELECT a.*,v.plate,c.name client FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id ORDER BY a.date,a.time'''); p.populate(['ID','Data','Ora','Targa','Cliente','Motivo','Note'],[[r['id'],r['date'],r['time'],r['plate'],r['client'],r['reason'],r['notes']] for r in rows]); p.table.doubleClicked.connect(lambda:self.appointment_dialog(aid=p.selected_id())); self._set_page(p)

    def print_appointment_selected(self, aid):
        if not aid: return QMessageBox.information(self,'PDF','Seleziona prima un appuntamento.')
        r=self.db.one('''SELECT a.*,v.plate,v.brand,v.model,c.name client,c.phone FROM appointments a LEFT JOIN vehicles v ON v.id=a.vehicle_id LEFT JOIN clients c ON c.id=v.client_id WHERE a.id=?''',(aid,))
        pth=self.make_pdf_path('Appuntamento'); c=pdfcanvas.Canvas(str(pth),pagesize=A4); y=self.pdf_header(c,'SCHEDA APPUNTAMENTO')
        pairs=[('Data',r['date']),('Ora',r['time']),('Cliente',r['client']),('Telefono',r['phone']),('Veicolo',f"{r['brand'] or ''} {r['model'] or ''}"),('Targa',r['plate']),('Motivo',r['reason']),('Note',r['notes'])]
        for k,v in pairs:
            c.setFont('Helvetica-Bold',9); c.drawString(16*mm,y,k); c.setFont('Helvetica',10); c.drawString(58*mm,y,str(v or '-')[:105]); y-=8*mm
        c.save(); self.open_pdf(pth)

    # Fatture e fornitori: aggiunta stampa singola senza perdere le funzioni 0.1.
    def show_invoices(self):
        super().show_invoices(); p=self.stack.currentWidget()
        if isinstance(p, TablePage): p.add_btn('Stampa fattura selezionata',lambda:self.print_invoice_selected(p.selected_id()))

    def print_invoice_selected(self, iid):
        if not iid: return QMessageBox.information(self,'PDF','Seleziona prima una fattura.')
        r=self.db.one('''SELECT i.*,v.plate,v.brand,v.model,c.name client,c.phone,c.email FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''',(iid,))
        pth=self.make_pdf_path(f"Fattura_{r['number']}"); c=pdfcanvas.Canvas(str(pth),pagesize=A4); y=self.pdf_header(c,'SCHEDA FATTURA')
        for k,v in [('Numero',r['number']),('Data',r['created']),('Cliente',r['client']),('Telefono',r['phone']),('Email',r['email']),('Veicolo',f"{r['brand']} {r['model']}"),('Targa',r['plate']),('Stato',r['status']),('Totale €',f"{r['total']:.2f}"),('Note',r['notes'])]:
            c.setFont('Helvetica-Bold',9); c.drawString(16*mm,y,k); c.setFont('Helvetica',10); c.drawString(58*mm,y,str(v or '-')[:105]); y-=8*mm
        c.save(); self.open_pdf(pth)

    def show_suppliers(self):
        super().show_suppliers(); p=self.stack.currentWidget()
        if isinstance(p, TablePage): p.add_btn('Stampa fornitore selezionato',lambda:self.print_supplier_selected(p.selected_id()))

    def print_supplier_selected(self, sid):
        if not sid: return QMessageBox.information(self,'PDF','Seleziona prima un fornitore.')
        r=self.db.one('SELECT * FROM suppliers WHERE id=?',(sid,)); pth=self.make_pdf_path(f"Fornitore_{r['name']}"); c=pdfcanvas.Canvas(str(pth),pagesize=A4); y=self.pdf_header(c,'SCHEDA FORNITORE')
        for k,v in [('Fornitore',r['name']),('Telefono',r['phone']),('Email',r['email']),('Note',r['notes'])]:
            c.setFont('Helvetica-Bold',9); c.drawString(16*mm,y,k); c.setFont('Helvetica',10); c.drawString(58*mm,y,str(v or '-')[:105]); y-=8*mm
        c.save(); self.open_pdf(pth)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('LA PRIMA Garage Manager 0.1.1')
    w = AppWindow(); w.show(); sys.exit(app.exec())
