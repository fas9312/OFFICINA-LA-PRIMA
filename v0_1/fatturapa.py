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


def clean_text(value, max_len=None):
    text = ' '.join(str(value or '').replace('\n', ' ').replace('\r', ' ').split())
    return text[:max_len] if max_len else text


def digits(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def alnum(value):
    return ''.join(ch for ch in str(value or '').upper() if ch.isalnum())


def money(value):
    return f'{float(value or 0):.2f}'


def quantity(value):
    v = float(value or 0)
    text = f'{v:.6f}'.rstrip('0').rstrip('.')
    return text or '0'


def add(parent, tag, value, *, max_len=None, required=False):
    text = clean_text(value, max_len)
    if not text and not required:
        return None
    node = ET.SubElement(parent, tag)
    node.text = text
    return node


def validate_context(seller, customer, invoice, items):
    errors = []
    seller_vat = digits(seller.get('vat_number'))
    seller_cf = alnum(seller.get('tax_code'))
    if len(seller_vat) != 11:
        errors.append('Partita IVA officina: servono 11 cifre.')
    if seller_cf and not (11 <= len(seller_cf) <= 16):
        errors.append('Codice fiscale officina non valido (11-16 caratteri).')
    if not clean_text(seller.get('business_name')):
        errors.append('Ragione sociale officina mancante.')
    if not re.fullmatch(r'RF\d{2}', clean_text(seller.get('tax_regime')).upper()):
        errors.append('Regime fiscale officina non valido (es. RF01).')
    if not clean_text(seller.get('address')):
        errors.append('Indirizzo officina mancante.')
    if not re.fullmatch(r'\d{5}', digits(seller.get('zip_code'))):
        errors.append('CAP officina: servono 5 cifre.')
    if not clean_text(seller.get('city')):
        errors.append('Comune officina mancante.')
    country = clean_text(seller.get('country') or 'IT').upper()
    if len(country) != 2:
        errors.append('Nazione officina: usare codice ISO a 2 lettere (es. IT).')
    if country == 'IT' and len(clean_text(seller.get('province')).upper()) != 2:
        errors.append('Provincia officina: usare 2 lettere (es. LT).')

    fmt = clean_text(customer.get('transmission_format') or 'FPR12').upper()
    if fmt not in ('FPR12','FPA12'):
        errors.append('Formato destinatario non valido: usare FPR12 o FPA12.')
    code = clean_text(customer.get('recipient_code')).upper()
    customer_country = clean_text(customer.get('country') or 'IT').upper()
    if fmt == 'FPA12':
        if len(code) != 6:
            errors.append('Cliente PA: il Codice Destinatario/Ufficio deve avere 6 caratteri.')
    else:
        if customer_country != 'IT' and not code:
            code = 'XXXXXXX'
        if not code:
            code = '0000000'
        if len(code) != 7:
            errors.append('Cliente privato/B2B: il Codice Destinatario deve avere 7 caratteri (oppure 0000000).')

    if not clean_text(customer.get('name')):
        errors.append('Ragione sociale/nome cliente mancante.')
    customer_vat = digits(customer.get('vat_number'))
    customer_cf = alnum(customer.get('tax_code'))
    if customer_country == 'IT' and not customer_vat and not customer_cf:
        errors.append('Cliente: inserire almeno Partita IVA o Codice Fiscale.')
    if customer_vat and customer_country == 'IT' and len(customer_vat) != 11:
        errors.append('Partita IVA cliente: servono 11 cifre.')
    if customer_cf and customer_country == 'IT' and not (11 <= len(customer_cf) <= 16):
        errors.append('Codice fiscale cliente non valido (11-16 caratteri).')
    if not clean_text(customer.get('address')):
        errors.append('Indirizzo cliente mancante.')
    if customer_country == 'IT' and not re.fullmatch(r'\d{5}', digits(customer.get('zip_code'))):
        errors.append('CAP cliente: servono 5 cifre.')
    if not clean_text(customer.get('city')):
        errors.append('Comune cliente mancante.')
    if customer_country == 'IT' and len(clean_text(customer.get('province')).upper()) != 2:
        errors.append('Provincia cliente: usare 2 lettere.')

    if not clean_text(invoice.get('number')):
        errors.append('Numero fattura mancante.')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', clean_text(invoice.get('date'))):
        errors.append('Data fattura non valida: serve AAAA-MM-GG.')
    doc_type = clean_text(invoice.get('document_type') or 'TD01').upper()
    if not re.fullmatch(r'TD\d{2}', doc_type):
        errors.append('Tipo documento non valido (es. TD01).')
    if not items:
        errors.append('La fattura non contiene righe.')
    for idx, item in enumerate(items, 1):
        rate = float(item.get('vat_rate') or 0)
        nature = clean_text(item.get('nature')).upper()
        if rate == 0 and nature not in NATURE_CODES:
            errors.append(f'Riga {idx}: IVA 0% richiede un codice Natura valido (es. N2.2, N4).')
        if rate != 0 and nature:
            errors.append(f'Riga {idx}: Natura deve essere vuota quando IVA è diversa da 0%.')
        if not clean_text(item.get('description')):
            errors.append(f'Riga {idx}: descrizione mancante.')
    return errors


def build_tree(seller, customer, invoice, items, progressivo):
    errors = validate_context(seller, customer, invoice, items)
    if errors:
        raise ValueError('\n'.join(errors))

    fmt = clean_text(customer.get('transmission_format') or 'FPR12').upper()
    recipient_code = clean_text(customer.get('recipient_code')).upper()
    customer_country = clean_text(customer.get('country') or 'IT').upper()
    if fmt == 'FPR12' and not recipient_code:
        recipient_code = 'XXXXXXX' if customer_country != 'IT' else '0000000'

    root = ET.Element(f'{{{FATTURAPA_NS}}}FatturaElettronica', {'versione': fmt})
    header = ET.SubElement(root, 'FatturaElettronicaHeader')

    transmission = ET.SubElement(header, 'DatiTrasmissione')
    sender_id = ET.SubElement(transmission, 'IdTrasmittente')
    add(sender_id, 'IdPaese', clean_text(seller.get('country') or 'IT').upper(), required=True)
    add(sender_id, 'IdCodice', digits(seller.get('vat_number')) or alnum(seller.get('tax_code')), max_len=28, required=True)
    add(transmission, 'ProgressivoInvio', clean_text(progressivo, 10), required=True)
    add(transmission, 'FormatoTrasmissione', fmt, required=True)
    add(transmission, 'CodiceDestinatario', recipient_code, required=True)
    if fmt == 'FPR12' and recipient_code == '0000000' and clean_text(customer.get('pec')):
        add(transmission, 'PECDestinatario', customer.get('pec'), max_len=256)

    seller_node = ET.SubElement(header, 'CedentePrestatore')
    seller_data = ET.SubElement(seller_node, 'DatiAnagrafici')
    seller_vat = ET.SubElement(seller_data, 'IdFiscaleIVA')
    add(seller_vat, 'IdPaese', clean_text(seller.get('country') or 'IT').upper(), required=True)
    add(seller_vat, 'IdCodice', digits(seller.get('vat_number')), max_len=28, required=True)
    if clean_text(seller.get('tax_code')):
        add(seller_data, 'CodiceFiscale', alnum(seller.get('tax_code')), max_len=16)
    seller_registry = ET.SubElement(seller_data, 'Anagrafica')
    add(seller_registry, 'Denominazione', seller.get('business_name'), max_len=80, required=True)
    add(seller_data, 'RegimeFiscale', clean_text(seller.get('tax_regime')).upper(), required=True)

    seller_address = ET.SubElement(seller_node, 'Sede')
    add(seller_address, 'Indirizzo', seller.get('address'), max_len=60, required=True)
    add(seller_address, 'NumeroCivico', seller.get('street_number'), max_len=8)
    add(seller_address, 'CAP', digits(seller.get('zip_code')), required=True)
    add(seller_address, 'Comune', seller.get('city'), max_len=60, required=True)
    if clean_text(seller.get('country') or 'IT').upper() == 'IT':
        add(seller_address, 'Provincia', clean_text(seller.get('province')).upper(), required=True)
    add(seller_address, 'Nazione', clean_text(seller.get('country') or 'IT').upper(), required=True)
    if clean_text(seller.get('phone')) or clean_text(seller.get('email')):
        contacts = ET.SubElement(seller_node, 'Contatti')
        add(contacts, 'Telefono', clean_text(seller.get('phone')).replace(' ', ''), max_len=12)
        add(contacts, 'Email', seller.get('email'), max_len=256)

    customer_node = ET.SubElement(header, 'CessionarioCommittente')
    customer_data = ET.SubElement(customer_node, 'DatiAnagrafici')
    customer_vat_value = digits(customer.get('vat_number')) if customer_country == 'IT' else clean_text(customer.get('vat_number'))
    if customer_vat_value:
        customer_vat = ET.SubElement(customer_data, 'IdFiscaleIVA')
        add(customer_vat, 'IdPaese', customer_country, required=True)
        add(customer_vat, 'IdCodice', customer_vat_value, max_len=28, required=True)
    if clean_text(customer.get('tax_code')):
        add(customer_data, 'CodiceFiscale', alnum(customer.get('tax_code')), max_len=16)
    customer_registry = ET.SubElement(customer_data, 'Anagrafica')
    add(customer_registry, 'Denominazione', customer.get('name'), max_len=80, required=True)
    customer_address = ET.SubElement(customer_node, 'Sede')
    add(customer_address, 'Indirizzo', customer.get('address'), max_len=60, required=True)
    add(customer_address, 'NumeroCivico', customer.get('street_number'), max_len=8)
    add(customer_address, 'CAP', digits(customer.get('zip_code')) if customer_country == 'IT' else clean_text(customer.get('zip_code')), required=True)
    add(customer_address, 'Comune', customer.get('city'), max_len=60, required=True)
    if customer_country == 'IT':
        add(customer_address, 'Provincia', clean_text(customer.get('province')).upper(), required=True)
    add(customer_address, 'Nazione', customer_country, required=True)

    body = ET.SubElement(root, 'FatturaElettronicaBody')
    general = ET.SubElement(body, 'DatiGenerali')
    document = ET.SubElement(general, 'DatiGeneraliDocumento')
    add(document, 'TipoDocumento', clean_text(invoice.get('document_type') or 'TD01').upper(), required=True)
    add(document, 'Divisa', 'EUR', required=True)
    add(document, 'Data', invoice.get('date'), required=True)
    add(document, 'Numero', invoice.get('number'), max_len=20, required=True)

    gross_total = sum(float(row.get('gross_total') or 0) for row in items)
    add(document, 'ImportoTotaleDocumento', money(gross_total), required=True)
    if clean_text(invoice.get('notes')):
        add(document, 'Causale', invoice.get('notes'), max_len=200)

    goods = ET.SubElement(body, 'DatiBeniServizi')
    vat_groups = defaultdict(lambda: [0.0, 0.0])
    for idx, row in enumerate(items, 1):
        detail = ET.SubElement(goods, 'DettaglioLinee')
        add(detail, 'NumeroLinea', str(idx), required=True)
        add(detail, 'Descrizione', row.get('description'), max_len=1000, required=True)
        add(detail, 'Quantita', quantity(row.get('qty')), required=True)
        add(detail, 'PrezzoUnitario', money(row.get('unit_net')), required=True)
        add(detail, 'PrezzoTotale', money(row.get('net_total')), required=True)
        rate = float(row.get('vat_rate') or 0)
        nature = clean_text(row.get('nature')).upper()
        add(detail, 'AliquotaIVA', money(rate), required=True)
        if rate == 0:
            add(detail, 'Natura', nature, required=True)
        key = (rate, nature if rate == 0 else '')
        vat_groups[key][0] += float(row.get('net_total') or 0)
        vat_groups[key][1] += float(row.get('vat_amount') or 0)

    for (rate, nature), (taxable, tax) in sorted(vat_groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        summary = ET.SubElement(goods, 'DatiRiepilogo')
        add(summary, 'AliquotaIVA', money(rate), required=True)
        if rate == 0:
            add(summary, 'Natura', nature, required=True)
        add(summary, 'ImponibileImporto', money(taxable), required=True)
        add(summary, 'Imposta', money(tax), required=True)
        if rate != 0:
            add(summary, 'EsigibilitaIVA', 'I')

    return ET.ElementTree(root)


def write_xml(path, seller, customer, invoice, items, progressivo):
    tree = build_tree(seller, customer, invoice, items, progressivo)
    ET.indent(tree, space='  ')
    tree.write(str(path), encoding='utf-8', xml_declaration=True)
    return path
