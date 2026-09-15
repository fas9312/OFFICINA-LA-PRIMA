import re
import xml.etree.ElementTree as ET
from collections import defaultdict

FATTURAPA_NS = 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2'
ET.register_namespace('p', FATTURAPA_NS)
ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

NATURE_CODES = {
    'N1','N2.1','N2.2','N3.1','N3.2','N3.3','N3.4','N3.5','N3.6',
    'N4','N5','N6.1','N6.2','N6.3','N6.4','N6.5','N6.6','N6.7','N6.8','N6.9','N7'
}

PAYMENT_METHODS = {
    'MP01':'Contanti','MP02':'Assegno','MP03':'Assegno circolare','MP04':'Contanti presso Tesoreria',
    'MP05':'Bonifico','MP06':'Vaglia cambiario','MP07':'Bollettino bancario','MP08':'Carta di pagamento',
    'MP09':'RID','MP10':'RID utenze','MP11':'RID veloce','MP12':'RIBA','MP13':'MAV','MP14':'Quietanza erario',
    'MP15':'Giroconto su conti di contabilità speciale','MP16':'Domiciliazione bancaria','MP17':'Domiciliazione postale',
    'MP18':'Bollettino di c/c postale','MP19':'SEPA Direct Debit','MP20':'SEPA Direct Debit CORE',
    'MP21':'SEPA Direct Debit B2B','MP22':'Trattenuta su somme già riscosse','MP23':'PagoPA'
}
PAYMENT_TERMS = {'TP01':'Pagamento a rate','TP02':'Pagamento completo','TP03':'Anticipo'}


def clean_text(value, max_len=None):
    text = ' '.join(str(value or '').replace('\n',' ').replace('\r',' ').split())
    return text[:max_len] if max_len else text


def digits(value): return ''.join(ch for ch in str(value or '') if ch.isdigit())
def alnum(value): return ''.join(ch for ch in str(value or '').upper() if ch.isalnum())
def money(value): return f'{float(value or 0):.2f}'

def quantity(value):
    text=f'{float(value or 0):.6f}'.rstrip('0').rstrip('.')
    return text or '0'


def add(parent, tag, value, *, max_len=None, required=False):
    text=clean_text(value,max_len)
    if not text and not required: return None
    node=ET.SubElement(parent,tag); node.text=text; return node


def validate_context(seller, customer, invoice, items):
    errors=[]
    seller_vat=digits(seller.get('vat_number')); seller_cf=alnum(seller.get('tax_code'))
    if len(seller_vat)!=11: errors.append('Dati Azienda > Partita IVA: servono 11 cifre.')
    if seller_cf and not (11<=len(seller_cf)<=16): errors.append('Dati Azienda > Codice Fiscale non valido (11-16 caratteri).')
    if not clean_text(seller.get('business_name')): errors.append('Dati Azienda > Ragione sociale mancante.')
    if not re.fullmatch(r'RF\d{2}',clean_text(seller.get('tax_regime')).upper()): errors.append('Dati Azienda > Regime fiscale non valido (es. RF01).')
    if not clean_text(seller.get('address')): errors.append('Dati Azienda > Indirizzo mancante.')
    if not re.fullmatch(r'\d{5}',digits(seller.get('zip_code'))): errors.append('Dati Azienda > CAP: servono 5 cifre.')
    if not clean_text(seller.get('city')): errors.append('Dati Azienda > Comune mancante.')
    seller_country=clean_text(seller.get('country') or 'IT').upper()
    if len(seller_country)!=2: errors.append('Dati Azienda > Nazione: usare 2 lettere, es. IT.')
    if seller_country=='IT' and len(clean_text(seller.get('province')).upper())!=2: errors.append('Dati Azienda > Provincia: usare 2 lettere, es. LT.')

    fmt=clean_text(customer.get('transmission_format') or 'FPR12').upper()
    if fmt not in ('FPR12','FPA12'): errors.append('Cliente > Formato destinatario: usare FPR12 o FPA12.')
    customer_country=clean_text(customer.get('country') or 'IT').upper()
    code=clean_text(customer.get('recipient_code')).upper()
    if fmt=='FPA12':
        if len(code)!=6: errors.append('Cliente PA > Codice Ufficio: servono 6 caratteri.')
    else:
        if customer_country!='IT' and not code: code='XXXXXXX'
        if not code: code='0000000'
        if len(code)!=7: errors.append('Cliente > Codice Destinatario: servono 7 caratteri oppure 0000000.')
    if not clean_text(customer.get('name')): errors.append('Cliente > Nome / ragione sociale mancante.')
    customer_vat=digits(customer.get('vat_number')); customer_cf=alnum(customer.get('tax_code'))
    if customer_country=='IT' and not customer_vat and not customer_cf: errors.append('Cliente > inserire almeno Partita IVA o Codice Fiscale.')
    if customer_vat and customer_country=='IT' and len(customer_vat)!=11: errors.append('Cliente > Partita IVA: servono 11 cifre.')
    if customer_cf and customer_country=='IT' and not (11<=len(customer_cf)<=16): errors.append('Cliente > Codice Fiscale non valido.')
    if not clean_text(customer.get('address')): errors.append('Cliente > Indirizzo fiscale mancante.')
    if customer_country=='IT' and not re.fullmatch(r'\d{5}',digits(customer.get('zip_code'))): errors.append('Cliente > CAP: servono 5 cifre.')
    if not clean_text(customer.get('city')): errors.append('Cliente > Comune mancante.')
    if customer_country=='IT' and len(clean_text(customer.get('province')).upper())!=2: errors.append('Cliente > Provincia: usare 2 lettere.')

    if not clean_text(invoice.get('number')): errors.append('Fattura > Numero mancante.')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',clean_text(invoice.get('date'))): errors.append('Fattura > Data non valida: serve AAAA-MM-GG.')
    if not re.fullmatch(r'TD\d{2}',clean_text(invoice.get('document_type') or 'TD01').upper()): errors.append('Fattura > Tipo documento non valido (es. TD01).')
    pay_terms=clean_text(invoice.get('payment_terms') or 'TP02').upper()
    pay_method=clean_text(invoice.get('payment_method') or 'MP05').upper()
    if pay_terms not in PAYMENT_TERMS: errors.append('Fattura > Condizioni di pagamento non valide.')
    if pay_method not in PAYMENT_METHODS: errors.append('Fattura > Modalità di pagamento non valida.')
    if not items: errors.append('La fattura non contiene righe.')
    for idx,item in enumerate(items,1):
        rate=float(item.get('vat_rate') or 0); nature=clean_text(item.get('nature')).upper()
        if rate==0 and nature not in NATURE_CODES: errors.append(f'Riga {idx}: IVA 0% richiede un codice Natura valido.')
        if rate!=0 and nature: errors.append(f'Riga {idx}: Natura deve essere vuota con IVA diversa da 0%.')
        if not clean_text(item.get('description')): errors.append(f'Riga {idx}: descrizione mancante.')
    return errors


def build_tree(seller, customer, invoice, items, progressivo):
    errors=validate_context(seller,customer,invoice,items)
    if errors: raise ValueError('\n'.join(errors))

    fmt=clean_text(customer.get('transmission_format') or 'FPR12').upper()
    recipient=clean_text(customer.get('recipient_code')).upper(); customer_country=clean_text(customer.get('country') or 'IT').upper()
    if fmt=='FPR12' and not recipient: recipient='XXXXXXX' if customer_country!='IT' else '0000000'

    root=ET.Element(f'{{{FATTURAPA_NS}}}FatturaElettronica',{'versione':fmt})
    header=ET.SubElement(root,'FatturaElettronicaHeader')
    transmission=ET.SubElement(header,'DatiTrasmissione')
    sender=ET.SubElement(transmission,'IdTrasmittente')
    add(sender,'IdPaese',clean_text(seller.get('country') or 'IT').upper(),required=True)
    add(sender,'IdCodice',digits(seller.get('vat_number')) or alnum(seller.get('tax_code')),max_len=28,required=True)
    add(transmission,'ProgressivoInvio',clean_text(progressivo,10),required=True)
    add(transmission,'FormatoTrasmissione',fmt,required=True)
    add(transmission,'CodiceDestinatario',recipient,required=True)
    if fmt=='FPR12' and recipient=='0000000' and clean_text(customer.get('pec')):
        add(transmission,'PECDestinatario',customer.get('pec'),max_len=256)

    seller_node=ET.SubElement(header,'CedentePrestatore')
    seller_data=ET.SubElement(seller_node,'DatiAnagrafici')
    seller_vat=ET.SubElement(seller_data,'IdFiscaleIVA')
    add(seller_vat,'IdPaese',clean_text(seller.get('country') or 'IT').upper(),required=True)
    add(seller_vat,'IdCodice',digits(seller.get('vat_number')),max_len=28,required=True)
    if clean_text(seller.get('tax_code')): add(seller_data,'CodiceFiscale',alnum(seller.get('tax_code')),max_len=16)
    seller_registry=ET.SubElement(seller_data,'Anagrafica'); add(seller_registry,'Denominazione',seller.get('business_name'),max_len=80,required=True)
    add(seller_data,'RegimeFiscale',clean_text(seller.get('tax_regime')).upper(),required=True)
    seller_address=ET.SubElement(seller_node,'Sede')
    add(seller_address,'Indirizzo',seller.get('address'),max_len=60,required=True); add(seller_address,'NumeroCivico',seller.get('street_number'),max_len=8)
    add(seller_address,'CAP',digits(seller.get('zip_code')),required=True); add(seller_address,'Comune',seller.get('city'),max_len=60,required=True)
    if clean_text(seller.get('country') or 'IT').upper()=='IT': add(seller_address,'Provincia',clean_text(seller.get('province')).upper(),required=True)
    add(seller_address,'Nazione',clean_text(seller.get('country') or 'IT').upper(),required=True)
    if clean_text(seller.get('rea_office')) and clean_text(seller.get('rea_number')):
        rea=ET.SubElement(seller_node,'IscrizioneREA')
        add(rea,'Ufficio',clean_text(seller.get('rea_office')).upper(),max_len=2,required=True); add(rea,'NumeroREA',seller.get('rea_number'),max_len=20,required=True)
        if clean_text(seller.get('share_capital')): add(rea,'CapitaleSociale',money(seller.get('share_capital')))
        if clean_text(seller.get('sole_member')): add(rea,'SocioUnico',clean_text(seller.get('sole_member')).upper())
        if clean_text(seller.get('liquidation_status')): add(rea,'StatoLiquidazione',clean_text(seller.get('liquidation_status')).upper())
    if clean_text(seller.get('phone')) or clean_text(seller.get('email')):
        contacts=ET.SubElement(seller_node,'Contatti'); add(contacts,'Telefono',clean_text(seller.get('phone')).replace(' ',''),max_len=12); add(contacts,'Email',seller.get('email'),max_len=256)

    customer_node=ET.SubElement(header,'CessionarioCommittente'); customer_data=ET.SubElement(customer_node,'DatiAnagrafici')
    customer_vat_value=digits(customer.get('vat_number')) if customer_country=='IT' else clean_text(customer.get('vat_number'))
    if customer_vat_value:
        cv=ET.SubElement(customer_data,'IdFiscaleIVA'); add(cv,'IdPaese',customer_country,required=True); add(cv,'IdCodice',customer_vat_value,max_len=28,required=True)
    if clean_text(customer.get('tax_code')): add(customer_data,'CodiceFiscale',alnum(customer.get('tax_code')),max_len=16)
    cr=ET.SubElement(customer_data,'Anagrafica'); add(cr,'Denominazione',customer.get('name'),max_len=80,required=True)
    ca=ET.SubElement(customer_node,'Sede'); add(ca,'Indirizzo',customer.get('address'),max_len=60,required=True); add(ca,'NumeroCivico',customer.get('street_number'),max_len=8)
    add(ca,'CAP',digits(customer.get('zip_code')) if customer_country=='IT' else clean_text(customer.get('zip_code')),required=True); add(ca,'Comune',customer.get('city'),max_len=60,required=True)
    if customer_country=='IT': add(ca,'Provincia',clean_text(customer.get('province')).upper(),required=True)
    add(ca,'Nazione',customer_country,required=True)

    body=ET.SubElement(root,'FatturaElettronicaBody'); general=ET.SubElement(body,'DatiGenerali'); document=ET.SubElement(general,'DatiGeneraliDocumento')
    add(document,'TipoDocumento',clean_text(invoice.get('document_type') or 'TD01').upper(),required=True); add(document,'Divisa','EUR',required=True); add(document,'Data',invoice.get('date'),required=True); add(document,'Numero',invoice.get('number'),max_len=20,required=True)
    gross_total=sum(float(r.get('gross_total') or 0) for r in items)
    stamp_amount=float(invoice.get('stamp_amount') or 0) if invoice.get('virtual_stamp') else 0.0
    if stamp_amount>0:
        bollo=ET.SubElement(document,'DatiBollo'); add(bollo,'BolloVirtuale','SI',required=True); add(bollo,'ImportoBollo',money(stamp_amount))
    total_document=gross_total+stamp_amount
    add(document,'ImportoTotaleDocumento',money(total_document),required=True)
    if clean_text(invoice.get('notes')): add(document,'Causale',invoice.get('notes'),max_len=200)

    goods=ET.SubElement(body,'DatiBeniServizi'); groups=defaultdict(lambda:[0.0,0.0])
    for idx,row in enumerate(items,1):
        d=ET.SubElement(goods,'DettaglioLinee'); add(d,'NumeroLinea',str(idx),required=True); add(d,'Descrizione',row.get('description'),max_len=1000,required=True); add(d,'Quantita',quantity(row.get('qty')),required=True)
        add(d,'PrezzoUnitario',money(row.get('unit_net')),required=True); add(d,'PrezzoTotale',money(row.get('net_total')),required=True)
        rate=float(row.get('vat_rate') or 0); nature=clean_text(row.get('nature')).upper(); add(d,'AliquotaIVA',money(rate),required=True)
        if rate==0: add(d,'Natura',nature,required=True)
        key=(rate,nature if rate==0 else ''); groups[key][0]+=float(row.get('net_total') or 0); groups[key][1]+=float(row.get('vat_amount') or 0)
    for (rate,nature),(taxable,tax) in sorted(groups.items(),key=lambda kv:(kv[0][0],kv[0][1])):
        s=ET.SubElement(goods,'DatiRiepilogo'); add(s,'AliquotaIVA',money(rate),required=True)
        if rate==0: add(s,'Natura',nature,required=True)
        add(s,'ImponibileImporto',money(taxable),required=True); add(s,'Imposta',money(tax),required=True)
        if rate!=0: add(s,'EsigibilitaIVA','I')

    payment=ET.SubElement(body,'DatiPagamento'); add(payment,'CondizioniPagamento',clean_text(invoice.get('payment_terms') or 'TP02').upper(),required=True)
    detail=ET.SubElement(payment,'DettaglioPagamento'); add(detail,'ModalitaPagamento',clean_text(invoice.get('payment_method') or 'MP05').upper(),required=True)
    if clean_text(invoice.get('payment_due_date')): add(detail,'DataScadenzaPagamento',invoice.get('payment_due_date'),required=True)
    add(detail,'ImportoPagamento',money(total_document),required=True)
    if clean_text(invoice.get('payment_iban')): add(detail,'IBAN',alnum(invoice.get('payment_iban')),max_len=34)

    return ET.ElementTree(root)


def write_xml(path,seller,customer,invoice,items,progressivo):
    tree=build_tree(seller,customer,invoice,items,progressivo); ET.indent(tree,space='  '); tree.write(str(path),encoding='utf-8',xml_declaration=True); return path
