import sys, sqlite3, hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QComboBox, QLineEdit, QMessageBox, QFileDialog, QInputDialog
)

import core
# Importing main_014 activates the selected offline database before the app opens.
from main_014 import AppWindow as AppWindow014
from core import TablePage, RED


APP_VERSION = '0.1.5'


def _password_hash(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest() if password else ''


def ensure_users_schema():
    # Make sure the base database exists before the login screen needs it.
    base = core.DB()
    try:
        base.conn.close()
    except Exception:
        pass
    conn = sqlite3.connect(core.DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO users(name,password_hash) VALUES('Amministratore','')")
    conn.commit(); conn.close()


class UserStore:
    def _conn(self):
        c = sqlite3.connect(core.DB_PATH); c.row_factory = sqlite3.Row; return c
    def all(self):
        c=self._conn()
        try: return c.execute('SELECT id,name,password_hash FROM users ORDER BY name COLLATE NOCASE').fetchall()
        finally: c.close()
    def get(self, uid):
        c=self._conn()
        try: return c.execute('SELECT id,name,password_hash FROM users WHERE id=?',(uid,)).fetchone()
        finally: c.close()
    def save(self, name, password, uid=None):
        name=(name or '').strip()
        if not name: raise ValueError('Il nome utente è obbligatorio.')
        c=self._conn()
        try:
            if uid:
                c.execute('UPDATE users SET name=?,password_hash=? WHERE id=?',(name,_password_hash(password),uid))
            else:
                c.execute('INSERT INTO users(name,password_hash) VALUES(?,?)',(name,_password_hash(password)))
            c.commit()
        except sqlite3.IntegrityError:
            raise ValueError('Esiste già un utente con questo nome.')
        finally: c.close()
    def delete(self, uid):
        c=self._conn()
        try:
            if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] <= 1:
                raise ValueError('Deve rimanere almeno un utente.')
            c.execute('DELETE FROM users WHERE id=?',(uid,)); c.commit()
        finally: c.close()


class UserEditDialog(QDialog):
    def __init__(self, parent=None, name=''):
        super().__init__(parent); self.setWindowTitle('Utente'); self.setMinimumWidth(420)
        root=QVBoxLayout(self); form=QFormLayout(); self.name=QLineEdit(name); self.password=QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText('Lascia vuoto per nessuna password')
        form.addRow('Nome utente',self.name); form.addRow('Password opzionale',self.password); root.addLayout(form)
        note=QLabel('La password è facoltativa. Se lasci il campo vuoto, l’utente accederà senza password.'); note.setWordWrap(True); note.setStyleSheet('color:#5D6D7E;font-size:11px;'); root.addWidget(note)
        row=QHBoxLayout(); cancel=QPushButton('Annulla'); save=QPushButton('Salva'); save.setStyleSheet(f'background:{RED};color:white;font-weight:700;padding:8px 16px;border-radius:6px;'); row.addStretch(); row.addWidget(cancel); row.addWidget(save); root.addLayout(row)
        cancel.clicked.connect(self.reject); save.clicked.connect(self.accept)


class UserLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.store=UserStore(); self.selected_user=None
        self.setWindowTitle('LA PRIMA - Accesso utente'); self.setMinimumWidth(500); self.setModal(True)
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(14)
        title=QLabel('OFFICINA  LA PRIMA'); title.setAlignment(Qt.AlignCenter); title.setStyleSheet('font-size:25px;font-weight:900;color:#10233B;')
        sub=QLabel('Scegli l’utente con cui entrare nel gestionale'); sub.setAlignment(Qt.AlignCenter); sub.setStyleSheet('color:#5D6D7E;')
        root.addWidget(title); root.addWidget(sub)
        self.combo=QComboBox(); self.combo.setMinimumHeight(38); root.addWidget(self.combo)
        manage=QHBoxLayout(); add=QPushButton('Nuovo utente'); edit=QPushButton('Modifica'); delete=QPushButton('Elimina')
        for b in (add,edit,delete): b.setMinimumHeight(34)
        manage.addWidget(add); manage.addWidget(edit); manage.addWidget(delete); root.addLayout(manage)
        enter=QPushButton('Entra'); enter.setMinimumHeight(42); enter.setStyleSheet(f'background:{RED};color:white;font-size:15px;font-weight:800;border-radius:7px;'); root.addWidget(enter)
        info=QLabel(f'Database: {core.DB_PATH}'); info.setWordWrap(True); info.setStyleSheet('color:#7A8997;font-size:10px;'); root.addWidget(info)
        add.clicked.connect(self.add_user); edit.clicked.connect(self.edit_user); delete.clicked.connect(self.delete_user); enter.clicked.connect(self.login); self.combo.activated.connect(lambda *_: None)
        self.refresh()

    def refresh(self, select_id=None):
        self.combo.clear()
        for u in self.store.all(): self.combo.addItem(u['name'],u['id'])
        if select_id is not None:
            idx=self.combo.findData(select_id)
            if idx>=0: self.combo.setCurrentIndex(idx)

    def current(self):
        return self.store.get(self.combo.currentData()) if self.combo.count() else None

    def add_user(self):
        d=UserEditDialog(self)
        if d.exec()!=QDialog.Accepted: return
        try: self.store.save(d.name.text(),d.password.text())
        except ValueError as e: return QMessageBox.warning(self,'Utente',str(e))
        rows=self.store.all(); self.refresh(rows[-1]['id'] if rows else None)

    def edit_user(self):
        u=self.current()
        if not u: return
        d=UserEditDialog(self,u['name'])
        if d.exec()!=QDialog.Accepted: return
        try: self.store.save(d.name.text(),d.password.text(),u['id'])
        except ValueError as e: return QMessageBox.warning(self,'Utente',str(e))
        self.refresh(u['id'])

    def delete_user(self):
        u=self.current()
        if not u: return
        if QMessageBox.question(self,'Elimina utente',f"Eliminare l’utente “{u['name']}”?",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes: return
        try: self.store.delete(u['id'])
        except ValueError as e: return QMessageBox.warning(self,'Utente',str(e))
        self.refresh()

    def login(self):
        u=self.current()
        if not u: return
        if u['password_hash']:
            password,ok=QInputDialog.getText(self,'Password',f"Password per {u['name']}:",QLineEdit.Password)
            if not ok: return
            if _password_hash(password)!=u['password_hash']:
                return QMessageBox.warning(self,'Accesso','Password non corretta.')
        self.selected_user={'id':u['id'],'name':u['name']}; self.accept()


class AppWindow(AppWindow014):
    def __init__(self, current_user=None):
        self.current_user=current_user or {'id':None,'name':'Utente'}
        super().__init__()
        self.setWindowTitle(f"LA PRIMA Garage Manager {APP_VERSION} — Utente: {self.current_user['name']}")
        self._fix_sidebar_logo_readability()

    def _fix_sidebar_logo_readability(self):
        # 0.1.3 created this text layer. In 0.1.5 it is moved ONTO the logo itself,
        # so the dark original lettering can no longer disappear on the navy sidebar.
        title=self.findChild(QLabel,'ReadableBrandText')
        if title:
            title.setText('<div style="text-align:center;font-weight:950;line-height:92%;"><span style="color:white;font-size:18px;">OFFICINA</span><br><span style="color:#FF2C3D;font-size:26px;">LA PRIMA</span></div>')
            title.setGeometry(36,20,184,74)
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet('background:rgba(18,38,58,170);border:0;border-radius:7px;padding:2px;')
            title.show(); title.raise_()

    # ---------- FATTURE: aggiunta esportazione XML ----------
    def show_invoices(self):
        self.set_nav('Fatture'); p=TablePage(self,'Fatture','Fatture a righe con imponibile, IVA, PDF e XML')
        p.add_btn('Nuova',lambda:self.invoice_dialog(),True)
        p.add_btn('Modifica',lambda:self.invoice_dialog(p.selected_id()))
        p.add_btn('Elimina',lambda:self.delete_invoice(p))
        p.add_btn('Stampa fattura selezionata',lambda:self.print_invoice_selected(p.selected_id()))
        p.add_btn('Esporta XML',lambda:self.export_invoice_xml(p.selected_id()))
        p.add_btn('Stampa situazione PDF',self.print_invoices)
        rows=self.db.q('''SELECT i.*,v.plate,c.name client FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id ORDER BY i.id DESC''')
        p.populate(['ID','Numero','Data','Targa','Cliente','Stato','Totale lordo €','Note'],[[r['id'],r['number'],r['created'],r['plate'],r['client'],r['status'],f"{r['total']:.2f}",r['notes']] for r in rows])
        p.table.doubleClicked.connect(lambda:self.invoice_dialog(p.selected_id())); self._set_page(p)

    def _invoice_xml_tree(self, iid):
        inv=self.db.one('''SELECT i.*,v.plate,v.brand,v.model,v.year,c.name client,c.phone,c.email FROM invoices i JOIN vehicles v ON v.id=i.vehicle_id JOIN clients c ON c.id=v.client_id WHERE i.id=?''',(iid,))
        if not inv: raise ValueError('Fattura non trovata.')
        items=self.db.q('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(iid,))
        root=ET.Element('FatturaLAPrima',{'versione':'1.0','tipo':'XML gestionale per commercialista'})
        doc=ET.SubElement(root,'Documento')
        for tag,val in [('Numero',inv['number']),('Data',inv['created']),('Stato',inv['status']),('Note',inv['notes'] or '')]: ET.SubElement(doc,tag).text=str(val or '')
        office=ET.SubElement(root,'Officina')
        for tag,key in [('Nome','name'),('Indirizzo','address'),('Telefono1','phone1'),('Telefono2','phone2')]: ET.SubElement(office,tag).text=self.db.setting(key) or ''
        client=ET.SubElement(root,'Cliente')
        for tag,val in [('Nome',inv['client']),('Telefono',inv['phone'] or ''),('Email',inv['email'] or '')]: ET.SubElement(client,tag).text=str(val)
        vehicle=ET.SubElement(root,'Veicolo')
        for tag,val in [('Targa',inv['plate']),('Marca',inv['brand'] or ''),('Modello',inv['model'] or ''),('Anno',inv['year'] or '')]: ET.SubElement(vehicle,tag).text=str(val)
        lines=ET.SubElement(root,'Righe')
        net_total=vat_total=gross_total=0.0; vat_groups={}
        for n,r in enumerate(items,1):
            row=ET.SubElement(lines,'Riga',{'numero':str(n)})
            vals=[('Descrizione',r['description']),('Quantita',f"{r['qty']:.3f}"),('PrezzoUnitarioNetto',f"{r['unit_net']:.2f}"),('AliquotaIVA',f"{r['vat_rate']:.2f}"),('Imponibile',f"{r['net_total']:.2f}"),('IVA',f"{r['vat_amount']:.2f}"),('TotaleLordo',f"{r['gross_total']:.2f}")]
            for tag,val in vals: ET.SubElement(row,tag).text=str(val)
            net_total+=float(r['net_total'] or 0); vat_total+=float(r['vat_amount'] or 0); gross_total+=float(r['gross_total'] or 0)
            rate=float(r['vat_rate'] or 0); grp=vat_groups.setdefault(rate,[0.0,0.0]); grp[0]+=float(r['net_total'] or 0); grp[1]+=float(r['vat_amount'] or 0)
        summary=ET.SubElement(root,'RiepilogoIVA')
        for rate,(net,vat) in sorted(vat_groups.items()):
            g=ET.SubElement(summary,'Aliquota',{'percentuale':f'{rate:.2f}'}); ET.SubElement(g,'Imponibile').text=f'{net:.2f}'; ET.SubElement(g,'IVA').text=f'{vat:.2f}'
        totals=ET.SubElement(root,'Totali'); ET.SubElement(totals,'Imponibile').text=f'{net_total:.2f}'; ET.SubElement(totals,'IVA').text=f'{vat_total:.2f}'; ET.SubElement(totals,'Lordo').text=f'{gross_total:.2f}'
        ET.SubElement(root,'Operatore').text=self.current_user.get('name','')
        return ET.ElementTree(root), inv['number']

    def _write_invoice_xml(self, iid, path):
        tree,_=self._invoice_xml_tree(iid)
        ET.indent(tree,space='  ')
        tree.write(str(path),encoding='utf-8',xml_declaration=True)

    def export_invoice_xml(self, iid):
        if not iid: return QMessageBox.information(self,'XML','Seleziona prima una fattura.')
        try: _,number=self._invoice_xml_tree(iid)
        except ValueError as e: return QMessageBox.warning(self,'XML',str(e))
        xml_dir=Path(core.DB_PATH).parent/'XML'; xml_dir.mkdir(parents=True,exist_ok=True)
        default=xml_dir/f'Fattura_{number}.xml'
        filename,_=QFileDialog.getSaveFileName(self,'Esporta fattura XML',str(default),'File XML (*.xml)')
        if not filename: return
        path=Path(filename)
        if path.suffix.lower()!='.xml': path=path.with_suffix('.xml')
        try: self._write_invoice_xml(iid,path)
        except Exception as e: return QMessageBox.critical(self,'XML',f'Errore durante la creazione XML:\n{e}')
        QMessageBox.information(self,'XML',f'Fattura esportata in XML:\n{path}\n\nNota: è un XML gestionale strutturato da consegnare al commercialista; non è un file FatturaPA firmato/inviato allo SDI.')


if __name__=='__main__':
    ensure_users_schema()
    app=QApplication(sys.argv); app.setApplicationName(f'LA PRIMA Garage Manager {APP_VERSION}')
    login=UserLoginDialog()
    if login.exec()!=QDialog.Accepted: sys.exit(0)
    w=AppWindow(login.selected_user); w.show(); sys.exit(app.exec())
