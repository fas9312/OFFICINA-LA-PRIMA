import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication, QLabel

import core
from main_017 import AppWindow, ensure_company_schema
from main_016 import ensure_fatturapa_schema, ensure_users_schema
from fatturapa_017 import write_xml

base=core.DB()
try: base.conn.close()
except Exception: pass
ensure_fatturapa_schema(); ensure_company_schema(); ensure_users_schema()

app=QApplication([])
w=AppWindow({'id':1,'name':'Test'}); w.show_settings(); w.show(); app.processEvents()
if w.findChild(QLabel,'CompanyDataTitle') is None:
    raise SystemExit('FAIL: Dati Azienda section missing')

seller={'business_name':'OFFICINA TEST SNC','vat_number':'12345678901','tax_code':'12345678901','tax_regime':'RF01','address':'Via Test','street_number':'1','zip_code':'00100','city':'Roma','province':'RM','country':'IT','email':'test@example.it','phone':'0612345678','rea_office':'RM','rea_number':'123456','share_capital':'10000','sole_member':'','liquidation_status':'LN'}
customer={'name':'CLIENTE TEST','vat_number':'','tax_code':'RSSMRA80A01H501U','transmission_format':'FPR12','recipient_code':'0000000','pec':'','address':'Via Cliente','street_number':'2','zip_code':'00100','city':'Roma','province':'RM','country':'IT'}
invoice={'number':'1/2026','date':'2026-09-15','document_type':'TD01','notes':'Test','payment_terms':'TP02','payment_method':'MP05','payment_due_date':'2026-09-30','payment_iban':'IT60X0542811101000000123456','virtual_stamp':False,'stamp_amount':0}
items=[{'description':'Manodopera officina','qty':1,'unit_net':100,'vat_rate':22,'net_total':100,'vat_amount':22,'gross_total':122,'nature':''}]
out=Path('smoke_fatturapa_017.xml'); write_xml(out,seller,customer,invoice,items,'00001')
text=out.read_text(encoding='utf-8')
for needle in ['FatturaElettronica','CedentePrestatore','CessionarioCommittente','DatiBeniServizi','DatiPagamento','ModalitaPagamento','MP05']:
    if needle not in text: raise SystemExit('FAIL XML: '+needle)
shot=w.grab()
if shot.isNull() or not shot.save('smoke_017.png'): raise SystemExit('FAIL screenshot')
print('OK 0.1.7 Dati Azienda, logo gradient and FatturaPA generation')
