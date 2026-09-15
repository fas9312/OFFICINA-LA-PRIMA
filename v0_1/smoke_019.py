import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import xml.etree.ElementTree as ET
from pathlib import Path

import core
from main_013 import ensure_schema_013
from main_019 import ensure_customer_type_schema, ensure_company_schema
from main_016 import ensure_fatturapa_schema, ensure_users_schema
from fatturapa_017 import write_xml, validate_context

base = core.DB()
try:
    base.conn.close()
except Exception:
    pass
ensure_schema_013()
ensure_fatturapa_schema()
ensure_company_schema()
ensure_customer_type_schema()
ensure_users_schema()

# Persona fisica italiana: nessuna P.IVA, solo Codice Fiscale.
seller = {
    'business_name':'OFFICINA TEST SNC','vat_number':'12345678901','tax_code':'12345678901',
    'tax_regime':'RF01','address':'Via Test','street_number':'1','zip_code':'00100',
    'city':'Roma','province':'RM','country':'IT','email':'test@example.it','phone':'0612345678'
}
customer = {
    'subject_type':'PF','name':'MARIO ROSSI','vat_number':'','tax_code':'RSSMRA80A01H501U',
    'transmission_format':'FPR12','recipient_code':'0000000','pec':'',
    'address':'Via Cliente','street_number':'2','zip_code':'00100','city':'Roma','province':'RM','country':'IT'
}
invoice = {
    'number':'1/2026','date':'2026-09-15','document_type':'TD01','notes':'Test',
    'payment_terms':'TP02','payment_method':'MP05','payment_due_date':'2026-09-30',
    'payment_iban':'IT60X0542811101000000123456','virtual_stamp':False,'stamp_amount':0
}
items = [{
    'description':'Manodopera officina','qty':1,'unit_net':100,'vat_rate':22,
    'net_total':100,'vat_amount':22,'gross_total':122,'nature':''
}]

errors = validate_context(seller, customer, invoice, items)
for err in errors:
    if 'Cliente > Partita IVA' in err or 'almeno Partita IVA' in err:
        raise SystemExit('FAIL: persona fisica richiesta P.IVA: ' + err)
if errors:
    raise SystemExit('FAIL validation: ' + ' | '.join(errors))

out = Path('smoke_fatturapa_pf_019.xml')
write_xml(out, seller, customer, invoice, items, '00001')
root = ET.parse(out).getroot()
customer_node = None
for el in root.iter():
    if el.tag.endswith('CessionarioCommittente'):
        customer_node = el
        break
if customer_node is None:
    raise SystemExit('FAIL: CessionarioCommittente missing')
text = ET.tostring(customer_node, encoding='unicode')
if 'RSSMRA80A01H501U' not in text:
    raise SystemExit('FAIL: customer CodiceFiscale missing')
# The customer's subtree must not invent a VAT number.
if '<IdFiscaleIVA>' in text or ':IdFiscaleIVA>' in text:
    raise SystemExit('FAIL: VAT node generated for private individual without VAT')

print('OK 0.1.9: persona fisica exports FatturaPA without customer VAT number, using Codice Fiscale')
