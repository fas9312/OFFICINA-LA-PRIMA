import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from pathlib import Path
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import QApplication

from main_015 import ensure_users_schema
from main_013 import ensure_schema_013
ensure_users_schema(); ensure_schema_013()

from main_016 import ensure_fatturapa_schema, AppWindow
from fatturapa import write_xml, FATTURAPA_NS

ensure_fatturapa_schema()

seller = {
    'business_name': 'OFFICINA TEST SNC', 'vat_number': '12345678901', 'tax_code': '12345678901',
    'tax_regime': 'RF01', 'address': 'Via Test', 'street_number': '1', 'zip_code': '04024',
    'city': 'Gaeta', 'province': 'LT', 'country': 'IT', 'email': 'test@example.it', 'phone': '0771123456'
}
customer = {
    'name': 'CLIENTE TEST SRL', 'vat_number': '10987654321', 'tax_code': '',
    'transmission_format': 'FPR12', 'recipient_code': '0000000', 'pec': 'cliente@pec.it',
    'address': 'Via Cliente', 'street_number': '2', 'zip_code': '00100', 'city': 'Roma',
    'province': 'RM', 'country': 'IT'
}
invoice = {'number': '1/2026', 'date': '2026-09-15', 'document_type': 'TD01', 'notes': 'Test CI'}
items = [
    {'description':'Tagliando completo','qty':1,'unit_net':100,'vat_rate':22,'net_total':100,'vat_amount':22,'gross_total':122,'nature':''}
]
path = Path('smoke_fatturapa.xml')
write_xml(path, seller, customer, invoice, items, '00001')
root = ET.parse(path).getroot()
if root.tag != f'{{{FATTURAPA_NS}}}FatturaElettronica':
    raise SystemExit('FAIL: root FatturaElettronica namespace')
if root.attrib.get('versione') != 'FPR12':
    raise SystemExit('FAIL: versione FPR12')
text = path.read_text(encoding='utf-8')
for required in ('FatturaElettronicaHeader','DatiTrasmissione','CedentePrestatore','CessionarioCommittente','FatturaElettronicaBody','DatiBeniServizi','DatiRiepilogo'):
    if required not in text: raise SystemExit('FAIL: missing '+required)

app = QApplication([])
w = AppWindow({'id':1,'name':'Test'})
w.show_settings(); w.show(); app.processEvents()
if not any('FatturaPA / Sistema di Interscambio' in lab.text() for lab in w.findChildren(__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel)):
    raise SystemExit('FAIL: FatturaPA settings card missing')
shot = w.grab()
if shot.isNull() or not shot.save('smoke_016.png'):
    raise SystemExit('FAIL: screenshot')
print('OK 0.1.6 FatturaPA XML + fiscal settings UI')
