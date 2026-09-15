import os, time
os.environ['QT_QPA_PLATFORM']='offscreen'

from pathlib import Path
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import QApplication, QLabel

from main_015 import ensure_users_schema, UserStore, UserLoginDialog, AppWindow
import core

ensure_users_schema()
app=QApplication([])

# User management smoke test.
store=UserStore(); stamp=str(int(time.time()*1000)); uname='Test015_'+stamp
store.save(uname,'')
u=[x for x in store.all() if x['name']==uname][0]
store.save(uname+'_R','',u['id'])
u2=store.get(u['id'])
if u2['name']!=uname+'_R' or u2['password_hash']!='': raise SystemExit('FAIL: user add/edit/no-password')
store.delete(u['id'])

login=UserLoginDialog(); app.processEvents()
if login.combo.count()<1: raise SystemExit('FAIL: login user chooser empty')

w=AppWindow({'id':0,'name':'Smoke Test'}); w.resize(1536,960); w.show(); app.processEvents()
brand=w.findChild(QLabel,'ReadableBrandText')
if brand is None or 'OFFICINA' not in brand.text() or 'LA PRIMA' not in brand.text(): raise SystemExit('FAIL: readable logo text missing')
if brand.geometry().y()>40: raise SystemExit('FAIL: readable logo text not over top logo')

# Create a minimal invoice and verify generated XML structure.
client=w.db.ex('INSERT INTO clients(name,phone,email,notes) VALUES(?,?,?,?)',(uname,'123','test@example.it','')).lastrowid
vehicle=w.db.ex('INSERT INTO vehicles(client_id,plate,brand,model,year,km,vin) VALUES(?,?,?,?,?,?,?)',(client,'T'+stamp[-6:],'Fiat','Panda','2024',1000,'')).lastrowid
inv=w.db.ex('INSERT INTO invoices(number,vehicle_id,created,status,total,notes) VALUES(?,?,?,?,?,?)',('XML-'+stamp,vehicle,'2026-09-15','Emessa',122.0,'test')).lastrowid
w.db.ex('INSERT INTO invoice_items(invoice_id,description,qty,unit_net,vat_rate,net_total,vat_amount,gross_total) VALUES(?,?,?,?,?,?,?,?)',(inv,'Lavorazione',1,100,22,100,22,122))
out=Path('smoke_invoice_015.xml'); w._write_invoice_xml(inv,out)
root=ET.parse(out).getroot()
if root.tag!='FatturaLAPrima': raise SystemExit('FAIL: XML root')
if root.findtext('./Totali/Lordo')!='122.00': raise SystemExit('FAIL: XML total')
if root.findtext('./Operatore')!='Smoke Test': raise SystemExit('FAIL: XML operator')

shot=w.grab()
if shot.isNull() or not shot.save('smoke_015.png'): raise SystemExit('FAIL: screenshot')
print('OK 0.1.5 users, readable logo, invoice XML export')
